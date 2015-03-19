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
from amcat.models import Sentence
from amcat.models.article import Article

from amcat.tools import amcattest


class TestSentence(amcattest.AmCATTestCase):

    def test_get_sentences(self):
        """Test retrieving all (unicode) sentences for an article"""
        a = amcattest.create_test_article()
        sentences = []
        for i, offset in enumerate(range(22, 20000, 1000)):
            sentnr = i % 7
            parnr = i // 7
            sent = "".join(unichr(offset + c) for c in range(47, 1000, 100))
            sentences += [(parnr, sentnr, sent)]
            Sentence.objects.create(article=a, parnr=parnr, sentnr=sentnr, sentence=sent)

        aid = a.id
        del a
        a2 = Article.objects.get(pk=aid)
        sentences2 = [(s.parnr, s.sentnr, s.sentence) for s in a2.sentences.all()]

        self.assertEqual(set(sentences), set(sentences2))
