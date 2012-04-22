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
Simple regex-based sentence boundary detection
"""

import re, collections


abbrevs = ["ir","mr","dr","dhr","ing","drs","mrs","sen","sens","gov","st",
           "jr","rev","vs","gen","adm","sr","lt","sept"]
months = ["Jan", "Feb", "Mar", "Apr", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

from amcat.models.sentence import Sentence

class SBD(object):

    def __init__(self):
        self._split_regex = None

    @property
    def split_regex(self):
        if self._split_regex is None:
            lenmap = collections.defaultdict(list)
            for a in abbrevs+months:
                lenmap[len(a)].append(a)
                lenmap[len(a)].append(a.title())
            expr = r"(?<!\b[A-Za-z])"
            for x in lenmap.values():
                expr += r"(?<!\b(?:%s))" % "|".join(x)
            #expr += r"(?<Nov(?=. \d))"
            expr += r"[\.?!](?!\.\.)(?<!\.\.)(?!\w|,)(?!\s[a-z])|\n\n"
            expr += r"|(?<=%s)\. (?=[^\d])" % "|".join(months)
            self._split_regex = re.compile(expr)
        return self._split_regex

    def get_sentences(self, article):
        pars = [article.headline]
        if article.byline: text += [article.byline]
        pars += re.split(r"\n\s*\n[\s\n]*", article.text.strip())
        for parnr, par in enumerate(pars):
            for sentnr, sent in enumerate(self.split(par)):
                yield Sentence(sentence=sent, parnr=parnr+1, sentnr=sentnr+1, article=article)

    def split(self, text):
        text = re.sub("\n\n+", "\n\n", text)
        text = text.replace(".'", "'.")

        for sent in self.split_regex.split(text):
            sent = sent.strip()
            if sent:
                sent = re.sub('\s+', ' ', sent)
                yield sent


if __name__ == '__main__':
    from amcat.models.article import Article
    import sys
    a = Article(headline="dit is de kop", text=sys.stdin.read())
    for s in SBD().get_sentences(a):
        print s.parnr, s.sentnr, s.sentence
        
