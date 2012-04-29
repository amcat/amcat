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


from __future__ import unicode_literals, print_function, absolute_import

import logging
import re
import datetime

import solr

from amcat.tools.toolkit import multidict
from amcat.tools.djangotoolkit import get_ids
from amcat.models import Article, ArticleSetArticle

log = logging.getLogger(__name__)



class Query(object):
    """
    A query object that contains both a (Solr) query and an optional label
    """
    def __init__(self, query, label=None):
        self.query = query
        self.label = label or query

class Solr(object):
    """Object oriented and AmCAT aware wrapper around the solr module"""
    def __init__(self, port=8983, host="localhost"):
        self.port = port
        self.host = host

    def _connect(self):
        return solr.SolrConnection(b'http://{self.host}:{self.port}/solr'.format(**locals()))

    #### QUERYING ####

    def query(self, query, filters=[], **kargs):
        return self._connect().query(query, fq=filters, **kargs)

    def query_ids(self, query, filters=[], **kargs):
        """Return a sequence of article ids for the given query"""
        for row in self.query(query, filters, fields="id", score=False, **kargs):
            yield row["id"]

    #### ADDING / REMOVING ARICLES ####

    def add_articles(self, articles):
        """Add the given articles to the solr index"""
        dicts = list(_get_article_dicts(list(get_ids(articles))))
        log.debug("Adding %i articles to solr" % len(dicts))
        conn = self._connect()
        conn.add_many(dicts)
        conn.commit()

    def delete_articles(self, articles):
        article_ids = list(get_ids(articles))
        log.debug("Removing {n} articles from solr".format(n=len(article_ids)))
        conn = self._connect()
        conn.delete_many(article_ids)
        conn.commit()


class GMT1(datetime.tzinfo):
    """very basic timezone object, needed for solrpy library.."""
    def utcoffset(self, dt):
        return datetime.timedelta(hours=1)
    def tzname(self, dt):
        return "GMT +1"
    def dst(self, dt):
        return datetime.timedelta(0)

def _clean(text):
    """Clean the text for indexing to avoid illegal character exception"""
    #See also:      http://mail-archives.apache.org/mod_mbox/lucene-solr-user/200901.mbox
    #                     /%3C2c138bed0901040803x4cc07a29i3e022e7f375fc5f@mail.gmail.com%3E
    if text: return re.sub('[\x00-\x08\x0B\x0C\x0E-\x1F]', ' ', text)

def _get_article_dicts(article_ids):
    """Yield dicts suitable for uploading to Solr from article IDs"""
    sets = multidict((aa.article_id, aa.articleset_id)
                     for aa in ArticleSetArticle.objects.filter(article__in=article_ids))
    for a in Article.objects.filter(pk__in=article_ids):
        yield dict(id=a.id,
                   headline=_clean(a.headline),
                   body=_clean(a.text),
                   byline=_clean(a.byline),
                   section=_clean(a.section),
                   projectid=a.project_id,
                   mediumid=a.medium_id,
                   date=a.date.replace(tzinfo=GMT1()),
                   sets=sets.get(a.id))


def query_args_from_form(form):
    """ takes a form as input and ceate filter queries for start/end date, mediumid and set """
    startDateTime = (form['startDate'].strftime('%Y-%m-%dT00:00:00.000Z')
                     if 'startDate' in form else '*')
    endDateTime = form['endDate'].strftime('%Y-%m-%dT00:00:00.000Z') if 'endDate' in form else '*'
    filters = []
    if startDateTime != '*' or endDateTime != '*': # if at least one of the 2 is a date
        filters.append('date:[%s TO %s]' % (startDateTime, endDateTime))
    if 'mediums' in form:
        mediumidQuery = ('mediumid:%d' % m.id for m in form['mediums'])
        filters.append(' OR '.join(mediumidQuery))
    if 'articleids' in form:
        articleidQuery = ('id:%d' % a for a in form['articleids'])
        filters.append(' OR '.join(articleidQuery))
    if 'articlesets' in form and form['articlesets']:
        setsQuery = ('sets:%d' % s.id for s in form['articlesets'])
        filters.append(' OR '.join(setsQuery))
    else:
        projectQuery = ('projectid:%d' % p.id for p in form['projects'])
        filters.append(' OR '.join(projectQuery))

    return dict(filters=filters, start=form['start'], rows=form['length'])



###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

import tempfile
import os.path
import subprocess
from contextlib import contextmanager


@contextmanager
def _test_solr(port=1234, temp_home=None, solr_home=None, **kargs):
    """Create ad hoc instance of solr for testing"""
    ps = subprocess.check_output('ps aux | grep "java -Djetty.port=1234"', shell=True)
    if '-Dsolr.data' in ps:
        raise Exception("Test solr already running!")
    
    if temp_home is None: temp_home = tempfile.mkdtemp()
    if solr_home is None:
        import amcat
        amcat_home = os.path.dirname(amcat.__file__)
        solr_home = os.path.abspath(os.path.join(amcat_home, "../amcatsolr"))
    if not os.path.exists(os.path.join(solr_home, "solr/solr.xml")):
        raise Exception("Solr.xml not found at {solr_home}".format(**locals()))

    # Start test solr instance
    args = {'-Djetty.port':str(port),'-Dsolr.data.dir':temp_home}
    cmd = ["java"] + ["=".join(kv) for kv in args.items()] + ["-jar","start.jar"]
    log.debug("Calling solr with cmd={cmd}, cwd={solr_home}".format(**locals()))
    solr_process = subprocess.Popen(cmd, cwd=solr_home, stderr=subprocess.PIPE)
    try:
        wait_for = u'Registered new searcher'
        log.debug("Waiting for line {wait_for!r}".format(**locals()))
        while True:
            line =  solr_process.stderr.readline()
            if wait_for in line: break
        log.info("Solr test instance running at port {port}, pid={solr_process.pid}"
                 .format(**locals()))
        yield Solr(port=port)
    finally:
        log.debug("Terminating solr process at pid {solr_process.pid}".format(**locals()))
        solr_process.terminate()
        solr_process.wait()
        log.info("Terminated solr process")

class TestAmcatSolr(amcattest.PolicyTestCase):
    def test_query(self):
        with _test_solr() as solr:
            a1 = amcattest.create_test_article(text='dit is een test')
            a2 = amcattest.create_test_article(text='en alweer een test')
            solr.add_articles([a1, a2])
            self.assertEqual(set(solr.query_ids("test")), set([a1.id, a2.id]))
            self.assertEqual(set(solr.query_ids("alweer")), set([a2.id]))
            solr.delete_articles([a2])
            self.assertEqual(set(solr.query_ids("test")), set([a1.id]))
            self.assertEqual(set(solr.query_ids("alweer")), set([]))
                



    def test_query_args_from_form(self):
        queries = [Query("alweer"), Query('test', 'TEST')]
        args = dict(sortColumn='', useSolr=True, queries=[],
                    query='test\r\nalweer',
                    start=0, length=100,
                    articleids=[], articlesets=[], mediums=[], projects=[],
                    columns= [u'article_id', u'date', u'medium_id', u'medium_name', u'headline'],
                    highlight=False, columnInterval='month', datetype='all', sortOrder='')


    def test_clean(self):
        """Test whether cleaning works correctly"""
        i = "\x00A\x01B\x08C\x0BD\x0CE\x0EF\x1DG\x1FH"
        o = " A B C D E F G H"
        self.assertEqual(_clean(i), o)

    def test_create_article_dicts(self):
        """Test whether article dicts are created correctly"""
        from amcat.models.article import Article
        s1,s2 = [amcattest.create_test_set() for _x in range(2)]
        p  = amcattest.create_test_project()
        m = amcattest.create_test_medium()
        a1 = amcattest.create_test_article(headline="bla \x1d blo", text="test",
                                           project=p, medium=m)

        a2 = amcattest.create_test_article(headline="blabla", text="t\xe9st!",
                                           byline="\u0904\u0905 test", project=p, medium=m)
        s1.add(a1)
        s2.add(a1)
        s2.add(a2)

        # force getting to make db rountrip and deserialize date
        ad1, ad2 = list(_get_article_dicts(Article.objects.filter(pk__in=[a1.id, a2.id])))
        for k,v in dict(id=a1.id, headline="bla   blo", body="test", byline=None,
                        section=None, projectid=p.id, mediumid=m.id,
                        sets=set([s1.id, s2.id])).items():
            self.assertEqual(ad1[k], v, "Article 1 %s %r!=%r" % (k, ad1[k], v))

        for k,v in dict(id=a2.id, headline="blabla", body="t\xe9st!", byline="\u0904\u0905 test",
                        section=None, projectid=p.id, mediumid=m.id,
                        sets=set([s2.id])).items():
            self.assertEqual(ad2[k], v, "Article 2 %s %r!=%r" % (k, ad2[k], v))
