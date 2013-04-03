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
Abstract analysis scripts for preprocessing.

We assume that all actual preprocessing will be done by an external
service that runs in parallel, e.g. the vunlp web service. Thus, the
analysis script has to be able to (1) submit articles to the service,
and (2) check, retrieve, interpret and store the results of the
external service.
"""

import traceback, logging
log = logging.getLogger(__name__)

from amcat.nlp.vunlpclient import Client
from amcat.nlp import sbd
from amcat.models import AnalysedArticle
from django.db import transaction

from amcat.scripts.script import Script

class AnalysisScript(Script):

    def submit_article(self, article):
        """
        Submit this article to the preprocessing service. 
        @param article: an amcat.Article or AnalysedArticle model instance. If it is an Article,
                        this method will create (and return) an AnalysedArticle object.
        @return: an AnalysedArticle model instance used or created, with .error=False, .done=False,
                 and optionally .info set to something useful for retrieving the article (e.g. the handle)
        """
        raise NotImplementedError()

    def retrieve_article(self, analysed_article):
        """
        Check, retrieve, interpret and store the preprocessing results. If successful, the
        various tokens/triples should be created as needed, and analysed_article.done should be
        set to True. If unsuccesful, the method should set .error=True and put an informative error
        message in the .info field.
        Note, the method will not raise an exception if one occurred. Check .done and .error if you
        want to check whether retrieving was succesfull.
        Note also that this method does transaction handling itself, committing or rolling back the
        transaction as needed. 
        @param analysed_article: an amcat.AnalysedArticle model instance as created by submit_article
        """
        try:
            with transaction.commit_on_success():
                success = self._do_retrieve_article(analysed_article)
                if success:
                    analysed_article.done = True
                    analysed_article.save()
        except Exception, e:
            log.exception("Error on retrieving/storing parse for ananalysed_article {analysed_article.id}".format(**locals()))
            self._set_error(analysed_article, traceback.format_exc())

    def _set_error(self, analysed_article, error_msg):
        with transaction.commit_on_success():
            analysed_article.error = True
            analysed_article.info = error_msg
            analysed_article.save()
                
    def check_article(self, analysed_article):
        """
        Checks whether this article is ready to be retrieved. The method may raise an exception if the article
        is in an unexpected state, ie not either ready or in the queue.
        @return: boolean
        """
        try:
            return self._do_check_article(analysed_article)
        except Exception, e:
            log.exception("Error on checking ananalysed_article {analysed_article.id}".format(**locals()))
            self._set_error(analysed_article, traceback.format_exc())
            raise

class VUNLPParser(AnalysisScript):
    """Analysisscript subclass for parsers bound to a specific ('home') folder"""

    def __init__(self):
        self.client = Client()
    
    def submit_article(self, article):
        plugin = self.get_plugin()
        handle = self.client.upload(self.parse_command, self._get_text_to_submit(article))
        log.info("Submitted article {article.id}, handle {handle}".format(**locals()))
        if isinstance(article, AnalysedArticle):
            # (re)set done, error, info
            article.done = False
            article.error = False
            article.info = handle
            article.save()
        else:
            # Create AnalysedArticle object
            article = AnalysedArticle.objects.create(article=article, plugin=plugin,
                                                     done=False, error=False, info=handle)
        return article


    def _get_sentences(self, article):
        """
        Return the sentences in the article, creating them if needed.
        @param article: an amcat.Article or AnalysedArticle model instance.
        @return: a sequence of Sentence model instances
        """
        if isinstance(article, AnalysedArticle):
            article = article.article
        return sbd.get_or_create_sentences(article)
    
    def _get_text_to_submit(self, article):
        """
        Return the text to be submitted to the VUNLP web service
        @param article: an amcat.Article or AnalysedArticle model instance. 
        """
        return "\n".join(s.sentence for s in self._get_sentences(article))
        

    def _do_retrieve_article(self, analysed_article):
        if self.check_article(analysed_article):
            parse = Client().download(analysed_article.info)
            open("/tmp/aa_%i.xml" % analysed_article.id, "w").write(parse)
            self.store_parse(analysed_article, parse)
            log.info("Stored article  {analysed_article.id}".format(**locals()))
            return True
            
    def _do_check_article(self, analysed_article):
        status = Client().check(analysed_article.info)
        log.info("Article  {analysed_article.id} has parse status {status}".format(**locals()))

        if status == "unknown":
            raise Exception("Article {analysed_article.id} has status 'unknown'"
                            .format(**locals()))
        
        return (status == "ready")

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAnalysisScript(amcattest.PolicyTestCase):
    pass
