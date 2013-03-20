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

from vunlpclient.client import Client
from amcat.nlp import sbd
from amcat.models import AnalysedArticle

from amcat.scripts.script import Script

class AnalysisScript(Script):

    def submit_article(self, article):
        """
        Submit this article to the preprocessing service. If the article cannot be
        submitted, an exception should be raised.
        If this method returns without an exception, a analysed_article will be
        created with the return value as 'info' attribute.  
        @param article: an amcat.Article model instance.
        @return: an optional string to be placed in the info attribute
        """
        raise NotImplementedError()

    def retrieve_article(self, analysed_article):
        """
        Check, retrieve, interpret and store the preprocessing results. If successful, the
        various tokens/triples should be created as needed, and analysed_article.done should be
        set to True. If unsuccesful, the method should set .error=True and put an informative error
        message in the .info field. 
        @param analysed_article: an amcat.AnalysedArticle model instance. If the submit_article
                                 returned a string, this will be available as analysed_article.info
        """
        raise NotImplementedError()

class VUNLPParser(AnalysisScript):
    """Analysisscript subclass for parsers bound to a specific ('home') folder"""

    def __init__(self):
        self.client = Client()
    
    def submit_article(self, article):
        plugin = self.get_plugin()
        # Upload text to vunlp server
        sentences = sbd.get_or_create_sentences(article)
        text = "\n".join(s.sentence for s in sentences)
        handle = self.client.upload(self.parse_command, text)
        log.info("Submitted article {article.id}, handle {handle}".format(**locals()))
        # Create AnalysedArticle object
        return AnalysedArticle.objects.create(article=article, plugin=plugin,
                                              done=False, error=False, info=handle)

    def retrieve_article(self, analysed_article):
        status = Client().check(analysed_article.info)
        return status
        if status == "ready":
            try:
                #parse = Client().download(analysed_article.info)
                parse = u'This is the headline\n\nthis/DT be/VBZ the/DT headline/NN\n\nnsubj(headline-4, this-1)\ncop(headline-4, be-2)\ndet(headline-4, the-3)\nroot(ROOT-0, headline-4)\n\nThis is the first sentence of the body\n\nthis/DT be/VBZ the/DT first/JJ sentence/NN of/IN the/DT body/NN\n\nnsubj(sentence-5, this-1)\ncop(sentence-5, be-2)\ndet(sentence-5, the-3)\namod(sentence-5, first-4)\nroot(ROOT-0, sentence-5)\nprep(sentence-5, of-6)\ndet(body-8, the-7)\npobj(of-6, body-8)\n\n'
                self.store_parse(parse)
            except Exception, e:
                log.exception("Error on retrieving/storing parse for ananalysed_article {analysed_article.id}".format(**locals()))
                analysed_article.error = True
                analysed_article.info = traceback.format_exc()
                analysed_article.save()
            else:
                analysed_article.done = True
                analysed_article.save()
        else:
            log.info("Article  {analysed_article.id} has parse status {status}".format(**locals()))
            

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAnalysisScript(amcattest.PolicyTestCase):
    pass
