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

import tempfile
import os.path
import subprocess
import itertools

import solr

from amcat.tools.toolkit import multidict
from amcat.tools.djangotoolkit import get_ids
from amcat.models import Article

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

    @property
    def url(self):
        return b'http://{self.host}:{self.port}/solr'.format(**locals())
        
    def _connect(self):
        return solr.SolrConnection(self.url)

    #### QUERYING ####

    def query_all(self, query, batch=1000, filters=[], **kargs):
        """Make repeated calls to solr to get all articles"""
        response = self._connect().query(query, fq=filters, rows=batch, **kargs)
        while response.results:
            log.debug("Iterating over all results, n={response.numFound}, "
                      "start={response.start}, |response.results|={n}"
                  .format(n=len(response.results), **locals()))
            for row in response.results:
                if 'score' in row:
                    row['score']  = int(row['score'])
                yield row
            response = response.next_batch()

    def query(self, query, filters=[], **kargs):
        qres = self._connect().query(query, fq=filters, **kargs)

        # Return articles with UTC as timezone (timezone agnostic)
        if len(qres.results) and "date" in qres.results[0]:
            for art in qres.results:
                art['date'] = art['date'].replace(tzinfo=None)

        return qres


    def query_ids(self, query, batch_size=1000000, **kargs):
        ids = set()
        c = self._connect()
        for start in itertools.count(step=batch_size):
            result = c.raw_query(q=query, rows=batch_size, fl="id", wt="csv", start=start)
            _ids = {int(x) for x in result.split("\n")[1:] if x}
            ids |= _ids
            if len(_ids) < batch_size:
                break
        return ids

    
    def query_highlight(self, query, **kargs):
        options = dict(
            highlight=True,
            fields="id,score,body,headline",
            hl_fl="body,headline",
            hl_usePhraseHighlighter='true',
            hl_highlightMultiTerm='true',
            hl_snippets=3,
            hl_mergeContiguous='true',
            )
        options.update(kargs)
        resp = self.query(query, **options)
            
    #### ADDING / REMOVING ARICLES ####

    def add_articles(self, articles):
        """Add the given articles to the solr index"""
        dicts = list(_get_article_dicts(list(get_ids(articles))))
        if dicts:
            log.info("Adding %i articles to solr" % len(dicts))
            conn = self._connect()
            conn.add_many(dicts)
            conn.commit()

    def delete_articles(self, articles):
        article_ids = list(get_ids(articles))
        if article_ids:
            log.info("Removing {n} articles from solr".format(n=len(article_ids)))
            conn = self._connect()
            conn.delete_many(article_ids)
            conn.commit()

def parseSolrHighlightingToArticles(solrResponse):
    scoresDict = dict((x['id'], int(x['score'])) for x in solrResponse.results)
    articleids = map(int, solrResponse.highlighting.keys())
    articlesDict = article.Article.objects.defer('text').in_bulk(articleids)
    for articleid, highlights in solrResponse.highlighting.iteritems():
        articleid = int(articleid)
        if articleid not in articlesDict: continue
        a = articlesDict[articleid]
        a.highlightedHeadline = highlights.get('headline')
        a.highlightedText = highlights.get('body')
        a.hits = scoresDict[articleid]
        yield a


def _highlight_get_context(snippet):
    """
    returns a dict which splits the snippet in the part before the first hit,
    the hit itself and after the hit.
    Hits after the first hit are surrounded by [[brackets]]
    """
    split = re.split('</?em>', snippet, 2)
    if not split or len(split) < 2:
        return None
    return {'before':split[0], 'hit':split[1],
            'after':split[2].replace('<em>', '[[').replace('</em>', ']]')}
        
def _clean(text):
    if text: return re.sub('[\x00-\x08\x0B\x0C\x0E-\x1F]', ' ', text)
        
def _get_article_dicts(article_ids):
    """Yield dicts suitable for uploading to Solr from article IDs"""
    class GMT0(datetime.tzinfo):
        def utcoffset(self, dt): return datetime.timedelta(hours=0)
        def tzname(self, dt): return "GMT"
        def dst(self, dt): return datetime.timedelta(0)
    from amcat.models.articleset import ArticleSetArticle

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
                   date=a.date.replace(tzinfo=GMT0()),
                   sets=sets.get(a.id))

def filters_from_form(form):
    """takes a form as input and ceate filter queries for start/end date, mediumid and set """
    startDateTime = (form['startDate'].strftime('%Y-%m-%dT00:00:00.000Z')
                     if 'startDate' in form else '*')
    endDateTime = form['endDate'].strftime('%Y-%m-%dT00:00:00.000Z') if 'endDate' in form else '*'
    filters = []
    if startDateTime != '*' or endDateTime != '*': # if at least one of the 2 is a date
        filters.append('date:[%s TO %s]' % (startDateTime, endDateTime))
    if form.get('mediums'):
        mediumidQuery = ('mediumid:%d' % m.id for m in form['mediums'])
        filters.append(' OR '.join(mediumidQuery))
    if form.get('articleids'):
        articleidQuery = ('id:%d' % a for a in form['articleids'])
        filters.append(' OR '.join(articleidQuery))
    if form.get('articlesets'):
        setsQuery = ('sets:%d' % s.id for s in form['articlesets'])
        filters.append(' OR '.join(setsQuery))
    else:
        projectQuery = ('projectid:%d' % p.id for p in form['projects'])
        filters.append(' OR '.join(projectQuery))
    return filters

def query_args_from_form(form):
    """ takes a form as input and return a dict of filter, start, and rows arguments for query"""
    return dict(filters=filters_from_form(form), start=form['start'], rows=form['length'])

class TestDummySolr(object):
    """
    A SOLR instance that doesn't do anything
    """
    def query(self, *args, **kargs):
        return []
    def query_ids(self, *args, **kargs):
        return set()
    def add_articles(self, *args, **kargs):
        pass
    def delete_articles(self, *args, **kargs):
        pass

class TestSolr(Solr):
    """
    Create a temporary SOLR instance to use for testing purposes
    """

    
    def __init__(self, port=1234, temp_home=None, solr_home=None, **kargs):
        super(TestSolr, self).__init__(port=port, host='localhost')
        self.temp_home = tempfile.mkdtemp() if temp_home is None else temp_home
        if solr_home is None:
            import amcat
            amcat_home = os.path.dirname(amcat.__file__)
            self.solr_home = os.path.abspath(os.path.join(amcat_home, "../../amcatsolr"))
        else:
            self.solr_home = solr_home
        if not os.path.exists(os.path.join(self.solr_home, "solr/solr.xml")):
            raise Exception("Solr.xml not found at {self.solr_home}".format(**locals()))
        self.solr_process = None

    def _check_test_solr(self):
        cmd = 'ps aux | grep "java -Djetty.port={self.port}"'.format(**locals())
        ps = subprocess.check_output(cmd, shell=True)
        if '-Dsolr.data' in ps: # don't check string occurring in ps line
            raise Exception("Test solr already running on port {self.port}!".format(**locals()))

    def start(self):
        self._check_test_solr()
        args = {'-Djetty.port':str(self.port),'-Dsolr.data.dir':self.temp_home}
        cmd = ["java"] + ["=".join(kv) for kv in args.items()] + ["-jar","start.jar"]
        log.debug("Calling solr with cmd={cmd}, cwd={self.solr_home}".format(**locals()))
        self.solr_process = subprocess.Popen(cmd, cwd=self.solr_home, stderr=subprocess.PIPE)
        wait_for = u'Registered new searcher'
        log.debug("Waiting for line {wait_for!r}".format(**locals()))
        while True:
            line = self.solr_process.stderr.readline()
            if wait_for in line: break
            if "SEVERE:" in line: raise Exception(line)
        log.info("Solr test instance running at port {self.port}, pid={self.solr_process.pid}"
                 .format(**locals()))

    def stop(self):
        if self.solr_process:
            self.solr_process.terminate()
            self.solr_process.wait()
            log.info("Terminated solr process")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest



class TestAmcatSolr(amcattest.PolicyTestCase):
    def clear_solr(self, solr):
        ids = set(solr.query_ids("*:*", rows=99999))
        solr.delete_articles(ids)
    
    def do_test_article_date(self, solr):
        """
        Tests whether article dates stay the same with a roundtrip
        amcat --> solr --> amcat.

        Call from test_query class to avoid creating another testsolr instance
        """
        db_a = amcattest.create_test_article(text='een dit is een test bla', headline='bla bla', date='2010-01-01')
        db_a = Article.objects.get(id=db_a.id)

        solr.add_articles([db_a])
        solr_a = solr.query("test", fields=["date"]).results[0]
        self.assertEqual(db_a.date, solr_a['date'])

        # test date representation in solr
        import re, urllib
        url = "http://{solr.host}:{solr.port}/solr/select/?q=id%3A{db_a.id}".format(**locals())
        xml = urllib.urlopen(url).read()
        m = re.search('<date name="date">([^>]+)</date>', xml)
        if not m:
            self.fail("Date not found in Solr XML")
        solr_date = m.group(1)
        self.assertEqual(solr_date, db_a.date.strftime("%Y-%m-%dT%H:%M:%SZ"))

    def test_query(self):
        if amcattest.skip_slow_tests():
            return
        
        with TestSolr() as solr:
            a1 = amcattest.create_test_article(text='een dit is een test bla', headline='bla bla')
            a2 = amcattest.create_test_article(text='en alweer een test blo')
            # can we add articles, and are the right articles returned?
            solr.add_articles([a1, a2])
            self.assertEqual(set(solr.query_ids("test")), set([a1.id, a2.id]))
            self.assertEqual(set(solr.query_ids("alweer")), set([a2.id]))
            
            # test phrase queries
            self.assertEqual(len(solr.query('"een test"').results), 2)
            self.assertEqual(len(solr.query('"test bla"').results), 1)
            self.assertEqual(len(solr.query('"een bla"').results), 0)
            # BUG: door de complex phrase query is de ordering er nu af?
            #self.assertEqual(len(solr.query('"bla test"').results), 0) 
            self.assertEqual(len(solr.query('"test bl*"').results), 2)
            self.assertEqual(len(solr.query('"een bl*"').results), 0)
            self.assertEqual(len(solr.query('"een bl*"~2').results), 2)
            self.assertEqual(len(solr.query('"een (bl* -blo)"~2').results), 1)
            self.assertEqual(len(solr.query('"een (bla OR blo)"~2').results), 2)
            self.assertEqual(len(solr.query('"dit bl*"~5').results), 1)
            
            # can we delete an article, and are the scores correct?
            solr.delete_articles([a2])
            self.assertEqual(set(solr.query("alweer")), set([]))
            self.assertEqual(solr.query("test", fields=["id", "mediumid"]).results,
                             [dict(score=1.0, id=a1.id, mediumid=a1.medium_id)])
            self.assertEqual(solr.query("een", fields=["id"]).results,
                             [dict(score=2.0, id=a1.id)])
            self.assertEqual(solr.query("bla", fields=["id", "sets"]).results,
                             [dict(score=3.0, id=a1.id)])
            # does update via 'add' work, and is set membership done correctly?
            s1 = amcattest.create_test_set()
            s1.add(a1)
            a1.headline="bla"
            a1.save()
            solr.add_articles([Article.objects.get(pk=a1.id)])
            self.assertEqual(solr.query("bla", fields=["id", "sets"]).results,
                             [dict(score=2.0, id=a1.id, sets=[s1.id])])
            # test query_all
            arts = [amcattest.create_test_article(text='en alweer een test')
                    for i in range(195)]
            solr.add_articles(arts)
            # normal query returns 10 results
            self.assertEqual(len(solr.query("test").results), 10)
            self.assertEqual(len(solr.query("test", rows=100).results), 100)
            self.assertEqual(len(list(solr.query_all("test"))), 196) # a1 + 195 new

            self.clear_solr(solr)
            self.do_test_article_date(solr)
            self.clear_solr(solr)
            self.do_test_highlight(solr)

            
    def todo_test_version(self):
        with TestSolr() as solr:
            url = "{solr.url}/admin/registry.jsp".format(**locals())
            import urllib
            resp = urllib.urlopen(url).read()
            m = re.search(r"<solr-impl-version>(\d+.\d+).(\d+)", resp)
            log.debug("Solr version: {}".format(m.groups()))
            self.assertEqual(float(m.group(1)), 3.6)
            
    def test_query_args_from_form(self):
        m = amcattest.create_test_medium()
        s1 = amcattest.create_test_set()
        s2 = amcattest.create_test_set()

        form = dict(sortColumn='', useSolr=True,
                    start=100, length=100,
                    articleids=[], articlesets=[s1,s2], mediums=[m], projects=[],
                    columns= [u'article_id', u'date', u'medium_id', u'medium_name', u'headline'],
                    highlight=False, columnInterval='month', datetype='all', sortOrder='')
        args = query_args_from_form(form)
        self.assertEqual(args, dict(start=100, rows=100, filters=[
                    u'mediumid:{m.id}'.format(**locals()),
                    u'sets:{s1.id} OR sets:{s2.id}'.format(**locals())]))

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


    def do_test_highlight(self, solr):
        blabla  = "bla bla bla bla bla bla \n" *50
        text = blabla + "bla een piet is een piet piet bla bla bla ble" + blabla
        a = amcattest.create_test_article(text=text, headline='bla piet')
        solr.add_articles([a])
        solr.query_highlight("piet")

#from amcat.tools import amcatlogging; amcatlogging.debug_module()
