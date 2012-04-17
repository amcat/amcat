###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################


"""
A Scraper is an object that knows how to scrape a certain resource. A scraper
is called by the controller,
"""

from django import forms
from django.forms.widgets import HiddenInput
from django.core.exceptions import ObjectDoesNotExist


from amcat.scripts.script import Script
from amcat.models.articleset import ArticleSet
from amcat.models.article import Article
from amcat.models.project import Project
from amcat.models.medium import get_or_create_medium
from amcat.models.articleset import ArticleSet, get_or_create_articleset

from amcat.scraping.htmltools import HTTPOpener
from amcat.scraping.document import Document

from amcat.tools.toolkit import retry

import logging; log = logging.getLogger(__name__)

class ScraperForm(forms.Form):
    """Form for scrapers"""
    project = forms.ModelChoiceField(queryset=Project.objects.all())

    articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all(), required=False)
    articleset_name = forms.CharField(
        max_length=ArticleSet._meta.get_field_by_name('name')[0].max_length,
        required = False)

    def clean_articleset_name(self):
        name = self.cleaned_data['articleset_name']
        if not name: return
        if self.cleaned_data['articleset']:
            raise forms.ValidationError("Cannot specify both articleset and articleset_name")

        project = self.cleaned_data['project']
        s = ArticleSet.objects.create(project=project, name=name)
        self.cleaned_data['articleset'] = s


    @classmethod
    def get_empty(cls, project=None, **_options):
        f = cls()
        if project:
            f.fields['project'].initial = project.id
            f.fields['project'].widget = HiddenInput()

            f.fields['articleset'].queryset = ArticleSet.objects.filter(project=project)
        return f

class Scraper(Script):
    output_type = Article
    options_form = ScraperForm

    # if non-None, Medium on articles will be automatically set to a
    # medium with this name (which will be created if necessary)
    medium_name = None

    def __init__(self, *args, **kargs):
        super(Scraper, self).__init__(*args, **kargs)
        self.medium = get_or_create_medium(self.medium_name)
        self.project = self.options['project']
        self.articleset = self.options['articleset']

    def run(self, input):
        log.info("Scraping {self.__class__.__name__} into {self.project}, medium {self.medium}"
                 .format(**locals()))
        from amcat.scraping.controller import SimpleController
        SimpleController(self.articleset).scrape(self)

    def get_units(self):
        """
        Split the scraping job into a number of 'units' that can be processed independently
        of each other.

        @return: a sequence of arbitrary objects to be passed to scrape_unit
        """
        self._initialize()
        return self._get_units()

    def _get_units(self):
        """
        'Protected' method to do the actual work of getting units. Will be called by get_units
        after running any needed initialization. By default, returns a single 'None' unit.
        Subclasses that override this method are encouraged to yield rather than return
        units to facilitate multithreaded

        @return: a sequence of arbitrary objects to be passed to scrape_unit
        """
        return [None]

    def scrape_unit(self, unit):
        """
        Scrape a single unit of work. Subclasses can override _scrape_unit to have project
        and medium filled in automatically.
        @return: a sequence of Article objects ready to .save()
        """
        log.debug("Scraping unit %s" % unit)
        for article in self._scrape_unit(unit):
            article = self._postprocess_article(article)
            log.debug(".. yields article %s" % article)
            yield article


    def _scrape_unit(self, unit):
        """
        'Protected' method to parse the articles from one unit. Subclasses should override
        this method (or the base scrape_unit). This method may be called from different threads
        so ensure thread-safe access to any globals or instance members.

        @return: an Article object or a Document object that
                 can be converted to an article. Either object can have the project
                 and medium properties unset as they will be set automatically if provided
        """
        raise NotImplementedError

    def _initialize(self):
        """
        Perform any intialization needed before starting the processing.
        """
        pass

    def _postprocess_article(self, article):
        """
        Finalize an article. This should convert the output of _scrape_unit to the required
        output for scrape_unit, e.g. convert to Article, add project and/or medium
        """
        if isinstance(article, Document):
            article = article.create_article()
        _set_default(article, "project", self.project)
        _set_default(article, "medium", self.medium)
        return article




class DateForm(ScraperForm):
    """
    Form for scrapers that operate on a date
    """
    date = forms.DateField()

class DatedScraper(Scraper):
    """Base class for scrapers that work for a certain date"""
    options_form = DateForm
    def _postprocess_article(self, article):
        article = super(DatedScraper, self)._postprocess_article(article)
        _set_default(article, "date", self.options['date'])
        return article
    def __unicode__(self):
        return "[%s for %s]" % (self.__class__.__name__, self.options['date'])

class DBScraperForm(DateForm):
    """
    Form for dated scrapers that need credentials
    """
    username = forms.CharField()
    password = forms.CharField()

class DBScraper(DatedScraper):
    """Base class for (dated) scrapers that require a login"""
    options_form = DBScraperForm

    def _login(self, username, password):
        """Login to the resource to scrape, if needed. Will be called
        at the start of get_units()"""
        pass

    def _initialize(self):
        self._login(self.options['username'], self.options['password'])

class HTTPScraper(Scraper):
    """Base class for scrapers that require an http opener"""
    def __init__(self, *args, **kargs):
        super(HTTPScraper, self).__init__(*args, **kargs)
        # TODO: this should be moved to _initialize, but then _initialize should
        # be moved to some sort of listener-structure as HTTPScraper is expected to
        # be inherited from besides eg DBScraper in a "diamon-shaped" multi-inheritance
        self.opener = HTTPOpener()
    def getdoc(self, url, encoding=None):
        """Legacy/convenience function"""
        return self.opener.getdoc(url, encoding)





def _set_default(obj, attr, val):
    try:
        if getattr(obj, attr, None) is not None: return
    except ObjectDoesNotExist:
        pass # django throws DNE on x.y if y is not set and not nullable
    setattr(obj, attr, val)


class MultiScraper(object):
    """
    Class that encapsulated multiple scrapers behind a single scraper interface
    Does not formally inherit from Scraper because it is not a runnable script
    """

    def __init__(self, scrapers):
        """@param scrapers: instantiated Scraper objects ('Ready to start scraping') """
        self.scrapers = scrapers

    def get_units(self):
        for scraper in self.scrapers:
            log.info("Starting scraping for {scraper}".format(**locals()))
            try:
                units = retry(scraper.get_units)
                for u in units:
                    yield (scraper, u)
            except:
                log.error("%s.get_units failed after retrying, giving up"
                          % scraper.__class__.__name__)

    def scrape_unit(self, unit):
        """Call the craper for the given unit. Will yield article objects
        with a .scraper custom attribute indicating the 'concrete' scraper"""

        (scraper, unit) = unit
        for a in scraper.scrape_unit(unit):
            a.scraper = scraper
            yield a

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli(Scraper)
