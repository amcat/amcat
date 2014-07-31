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
Plugin for uploading csv files
"""

from __future__ import unicode_literals, absolute_import

import csv
import datetime

from django import forms
from django.db.models.fields import FieldDoesNotExist
from amcat.models import ArticleSet

from amcat.scripts.article_upload.upload import UploadScript
from amcat.scripts.article_upload import fileupload
from amcat.models.article import Article
from amcat.models.medium import Medium
from amcat.tools.amcates import ES
from amcat.tools.toolkit import readDate

FIELDS = ("text", "date", "medium", "pagenr", "section", "headline", "byline", "url", "externalid",
          "author", "addressee", "parent_url", "parent_externalid")
REQUIRED = [True] * 2 + [False] * (len(FIELDS) - 2)

PARSERS = {
    "date": readDate,
    "pagenr": int,
    "externalid": int,
    "parent_externalid": int,
    "medium": Medium.get_or_create
}

HELP_TEXTS = {
    "parent_url": "Column name for the URL of the parent article, which should be in the same CSV file",
    "parent_externalid": "Column name for the External ID of the parent article, which should be in the same CSV file",
}


def is_nullable(field_name):
    try:
        return Article._meta.get_field(field_name).null
    except FieldDoesNotExist:
        return True


class CSVForm(UploadScript.options_form, fileupload.CSVUploadForm):
    medium_name = forms.CharField(
        max_length=Article._meta.get_field_by_name('medium')[0].max_length,
        required=False)
    medium_existing = forms.ModelChoiceField(
        queryset=Medium.objects.all(), required=False,
        help_text="Use this option if you want to choose one medium for all uploaded articles."
    )

    addressee_from_parent = forms.BooleanField(required=False, initial=False, label="Addressee from parent",
                                               help_text="If set, will set the addressee field to the author of the parent article")

    def clean_medium_name(self):
        cd = self.cleaned_data
        name = self.cleaned_data['medium_name']

        if not (name or ("medium" in self.data and self.data["medium"]) or "medium_existing" in cd):
            raise forms.ValidationError("Please specify either medium, medium_existing or medium_name")

        return name

    def __init__(self, *args, **kargs):
        super(CSVForm, self).__init__(*args, **kargs)
        for fieldname, required in reversed(zip(FIELDS, REQUIRED)):
            label = fieldname + " field"
            if fieldname in HELP_TEXTS:
                help_text = HELP_TEXTS[fieldname]
            else:
                help_text = "Column name for the article {}".format(fieldname)
                if not required:
                    help_text += ", or leave blank to leave unspecified"

            initial = fieldname if required else None

            field = forms.CharField(help_text=help_text, required=required,
                                    initial=initial, label=label)
            self.fields.insert(7, fieldname, field)


    def clean_parent_url(self):
        idfield = self.cleaned_data['parent_url']
        if idfield and self.cleaned_data['parent_externalid']:
            raise forms.ValidationError("Cannot specify both external id and URL for parents")
        return idfield


class CSV(UploadScript):
    """
    Upload CSV files to AmCAT.

    To tell AmCAT which columns from the csv file to use, you need to specify the name in the file
    for the AmCAT-fields that you want to import. So, if you have a 'title' column in the csv file
    that you want to import as the headline, specify 'title' in the "headline field" input box.

    Text and date and required, all other fields are optional.

    If you are encountering difficulties, please make sure that you know how the csv is exported, and
    manually set encoding and dialect in the options above.

    Since Excel has quite some difficulties with exporting proper csv, it is often better to use
    an alternative such as OpenOffice or Google Spreadsheet (but see below for experimental xlsx support).
    If you must use excel, there is a 'tools' button on the save dialog which allows you to specify the
    encoding and delimiter used.

    We have added experimental support for .xlsx files (note: only use .xlsx, not the older .xls file type).
    This will hopefully alleviate some of the problems with reading Excel-generated csv file. Only the
    first sheet will be used, and please make sure that the data in that sheet has a header row. Please let
    us know if you encounter any difficulties at github.com/amcat/amcat/issues. Since you can only attach
    pictures there, the best way to share the file that you are having difficulty with (if it is not private)
    is to upload it to dropbox or a file sharing website and paste the link into the issue.
    """

    options_form = CSVForm

    def explain_error(self, error):
        if isinstance(error.error, KeyError):
            return "Field {error.error} not found in row {error.i}. Check field name and/or csv dialect".format(
                **locals())
        return super(CSV, self).explain_error(error)

    def run(self, *args, **kargs):

        if self.options['parent_url']:
            self.id_field, self.parent_field = 'url', 'parent_url'
        elif self.options['parent_externalid']:
            self.id_field, self.parent_field = 'externalid', 'parent_externalid'
        else:
            self.id_field, self.parent_field = None, None

        if self.parent_field:
            self.parents = {}  # id/url : id/url
            self.articles = {}  # id/url : article

        return super(CSV, self).run(*args, **kargs)

    @property
    def _medium(self):
        if self.options["medium"]:
            return

        if self.options['medium_existing']:
            return self.options['medium_existing']

        if self.options['medium_name']:
            med = Medium.get_or_create(self.options['medium_name'])
            self.options['medium_existing'] = med
            return med

        raise ValueError("No medium specified!")

    def parse_document(self, row):
        kargs = dict(medium=self._medium, metastring={})
        csvfields = [(fieldname, self.options[fieldname]) for fieldname in FIELDS if self.options[fieldname]]
        for fieldname, csvfield in csvfields:
            val = row[csvfield]
            if fieldname == 'date' and isinstance(val, datetime.datetime):
                pass  # no need to parse
            elif val.strip():
                if fieldname in PARSERS:
                    val = PARSERS[fieldname](val)
            elif is_nullable(fieldname):
                val = None
            else:
                val = val.strip()

            kargs[fieldname] = val

        # Metadata to metastring
        csvfields = [tup[1] for tup in csvfields]
        for key, value in row.items():
            if key not in csvfields:
                kargs["metastring"][key] = value

        # In case medium wasn't defined in csv
        medium = self._medium
        if medium is not None:
            kargs["medium"] = medium

        if self.parent_field:
            doc_id = kargs.get(self.id_field)
            parent_id = kargs.pop(self.parent_field)
            if parent_id:
                self.parents[doc_id] = parent_id

        article = Article(**kargs)
        if self.parent_field:
            self.articles[doc_id] = article

        return article

    def postprocess(self, articles):
        if self.parent_field:
            for doc_id, parent_id in self.parents.iteritems():
                doc = self.articles[doc_id]
                doc.parent = self.articles[parent_id]
                if not doc.addressee and self.options['addressee_from_parent']:
                    doc.addressee = doc.parent.author

                doc.save()
        super(CSV, self).postprocess(articles)


if __name__ == '__main__':
    from amcat.scripts.tools import cli

    cli.run_cli(CSV)

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
import unittest


def _run_test_csv(header, rows, **options):
    project = amcattest.create_test_project()
    articleset = amcattest.create_test_set(project=project)

    from tempfile import NamedTemporaryFile
    from django.core.files import File

    with NamedTemporaryFile(suffix=".txt") as f:
        w = csv.writer(f)
        for row in [header] + list(rows):
            w.writerow([field and field.encode('utf-8') for field in row])
        f.flush()

        set = CSV(dict(file=File(open(f.name)), encoding=0, project=project.id,
                       medium_name=options.pop("medium_name", 'testmedium'),
                       articlesets=[articleset.id], **options)).run()

    return ArticleSet.objects.get(id=set[0]).articles.all()


class TestCSV(amcattest.AmCATTestCase):
    @amcattest.use_elastic
    def test_csv(self):
        header = ('kop', 'datum', 'tekst', 'pagina')
        data = [('kop1', '2001-01-01', 'text1', '12'), ('kop2', '10 maart 1980', 'text2', None)]
        articles = _run_test_csv(header, data, text="tekst", headline="kop", date="datum", pagenr='pagina')
        self.assertEqual(len(articles), 2)

        # Scraper is not guarenteed to return articles in order.
        self.assertEqual({articles[0].headline, articles[1].headline}, {'kop1', 'kop2'})
        self.assertEqual({articles[0].pagenr, articles[1].pagenr}, {12, None})

        date1 = articles[0].date.isoformat()[:10]
        date2 = articles[1].date.isoformat()[:10]
        self.assertTrue('1980-03-10' in {date1, date2})

    @amcattest.use_elastic
    def test_text(self):
        header = ('kop', 'datum', 'tekst')
        data = [('kop1', '2001-01-01', '')]
        articles = _run_test_csv(header, data, text="tekst", headline="kop", date="datum")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].text, "")

    @amcattest.use_elastic
    def test_medium(self):
        import functools

        header = ('kop', 'datum', 'tekst', 'med')
        data = [('kop1', '2001-01-01', '', 'Bla')]

        test = functools.partial(_run_test_csv, header, data, text="tekst", headline="kop", date="datum")
        articles = test(medium_name=None, medium="med")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].medium.name, "Bla")

        articles = test(medium_existing=Medium.get_or_create("1").id)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].medium.name, "1")

        articles = test(medium_existing=Medium.get_or_create("1").id, medium="med")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].medium.name, "Bla")

        articles = test(medium_name="bla2", medium="med")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].medium.name, "Bla")

        articles = test(medium_name="bla2", medium_existing=Medium.get_or_create("2").id)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].medium.name, "2")

    @unittest.skip("Controller is a mess")
    def test_parents(self):
        header = ('kop', 'datum', 'tekst', 'id', 'parent', 'van')
        data = [
            ('kop1', '2001-01-01', 'text1', "7", "12", 'piet'),
            ('kop2', '2001-01-01', 'text2', "12", None, 'jan')
        ]
        articles = _run_test_csv(header, data, text="tekst", headline="kop", date="datum",
                                 externalid='id', parent_externalid='parent', author='van')


        # for strange reasons, it seems that the order is sometimes messed up
        # since this is not something we care about, we order the results
        articles = sorted(articles, key=lambda a: a.externalid)

        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0].parent, articles[1])
        self.assertEqual(articles[0].externalid, 7)
        self.assertEqual(articles[0].author, 'piet')
        self.assertEqual(articles[0].addressee, None)

        self.assertEqual(articles[1].parent, None)
        self.assertEqual(articles[1].externalid, 12)
        self.assertEqual(articles[1].author, 'jan')
        self.assertEqual(articles[1].addressee, None)

        articles = _run_test_csv(header, data, text="tekst", headline="kop", date="datum",
                                 externalid='id', parent_externalid='parent', author='van',
                                 addressee_from_parent=True)

        # see above
        articles = sorted(articles, key=lambda a: a.externalid)

        self.assertEqual(articles[0].author, 'piet')
        self.assertEqual(articles[0].addressee, 'jan')
        self.assertEqual(articles[1].author, 'jan')
        self.assertEqual(articles[1].addressee, None)


    @amcattest.use_elastic
    def test_date_format(self):
        # Stump class to test future 'date format' option, if needed. Currently just checks that
        # a variety of formats load correctly.
        header = "date", "text"

        for datestr, dateformat, expected in [
            ("2001-01-01", None, "2001-01-01"),
            ("10/03/80", None, "1980-03-10"),
            ("15/08/2008", None, "2008-08-15"),
        ]:
            data = [(datestr, "text")]
            a, = _run_test_csv(header, data, date="date", text="text")
            self.assertEqual(a.date.isoformat()[:10], expected)
