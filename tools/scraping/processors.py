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
"""This module contains the main scraping-logic. All scrapers have to inherit
from BaseScraper, which provides an multithreaded scraping environment.

Tested on:
 * Python 2.6
 * Python 2.7
 """
from django import forms

from lxml.html import builder
from functools import partial
from lxml import html

from amcat.tools import toolkit as atoolkit
from amcat.scripts import script

import ConfigParser as configparser
import Queue as queue

from amcat.tools.scraping import objects
from amcat.tools.scraping import toolkit
from amcat.tools.scraping import exporter

import os, time, sys
import datetime
import threading
import traceback
import urlparse
import logging
import urllib, urllib2
import urlparse

log = logging.getLogger(__name__)

__all__ = ['Scraper',]

class InheritError(Exception):
    pass

class Worker(object):
    """Workers consume work in the scrapers' work-queue. Each document yielded by
    scraper.get will result in a documment added to the document_queue.

    All items in the document-queue are consumed by the commit-thread."""
    def __init__(self, scraper):
        self.alive = True
        self.scraper = scraper
        self.queue = self.scraper.work_queue

        self.thread = threading.Thread(target=self.main)
        self.thread.start()

    def main(self):
        """For each document placed in scraper.work_queue by scrape(), pass it to
        get() and iterate over the results to put them in the document-queue."""
        while self.alive or not self.queue.empty():
            try:
                work = self.queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                work.prepare(self.scraper)
            except:
                traceback.print_exc(file=sys.stdout)
            else:
                try:
                    for doc in self.scraper.get(work):
                        self.scraper.document_queue.put(doc)
                except Exception as e:
                    self.queue.task_done()
                    traceback.print_exc(file=sys.stdout)
                    sys.exit(1)

            self.queue.task_done()

    def quit(self):
        """End the workers' main loop. A worker only quits when the work-queue is empty"""
        self.alive = False
        self.thread.join()

class Form(forms.Form):
    """
    Standard form for scrapers. Each scraper-form has to inherit this one.
    """
    threads = forms.IntegerField(initial=1)

    set = forms.CharField(max_length=100)
    project = forms.IntegerField(initial=-1)

    #dummy = forms.BooleanField(initial=False)

class Scraper(script.Script):
    """Base scraper object. 

    Documentation:
     * TODO"""
    # See script documentation for documentation for these variables
    input_type = None
    options_form = Form
    output_type = None

    # If this variable is not set when initializing this class, all
    # articles need to have a 'medium' property.
    medium = None

    def __init__(self, options=None, **kargs):
        super(Scraper, self).__init__(options, **kargs)
        self.alive = True

        # Setup queues
        self.work_queue = queue.Queue(maxsize=80)
        self.document_queue = queue.Queue(maxsize=5000)

        self.exporter = exporter.Exporter(self.options['set'],
                                          self.medium,
                                          self.options['project'])

        self.workers = []
        for i in range(self.options['threads']):
            w = Worker(self)
            self.workers.append(w)

        self.commit_thread = threading.Thread(target=self._commit)
        self.commit_thread.start()

    def _commit(self):
        """This function commits all documents in document_queue. To
        stop the loop, call `quit`."""
        while not self.document_queue.empty() or self.alive:
            # Keep running until all documents are committed, despite not
            # being alive. 
            try:
                doc = self.document_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            self.exporter.commit(doc)
            self.document_queue.task_done()

    ### SCRIPT FUNCTIONS ###
    def run(self, input=None):
        self.scrape()


    ### SCRAPER FUNCTIONS ###
    def init(self):
        return []

    def get(self, doc):
        return []

    def update(self, *args, **kargs):
        return []

    ### PUBLIC FUNCTIONS ###
    def scrape(self, auto_quit=True, update=False, **kwargs):
        """Scrape for a certain date. Scrapers may support date=None.

        @type auto_quit: Boolean
        @param auto_quit: Automatically quit when done with this date

        @param kwargs: arguments to pass to scraper.init"""
        try:
            func = self.update if update else self.init
            for work in func(**kwargs):
                if not isinstance(work, objects.Document):
                    raise(ValueError("init() should yield a Document-object not %s" % type(work)))
                self.work_queue.put(work)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)

        if auto_quit: self.quit()

    def quit(self, close_exporter=True):
        """Quit commit loop. *Must* be called after scraping.

        @type close_exporter: Boolean
        @param close_exporter: Wether or not to close the exporter. Defaults to True."""
        for worker in self.workers:
            worker.quit()

        self.alive = False
        self.commit_thread.join()
        if close_exporter:
            self.exporter.close()

class HTTPScraper(Scraper):
    def __init__(self, options=None, **kargs):
        super(HTTPScraper, self).__init__(options, **kargs)

        # Create session
        c = urllib2.HTTPCookieProcessor()
        s = urllib2.build_opener(c)
        s.addheaders = [('User-agent', 'Mozilla/5.0 (X11; Linux i686; rv:6.0.2) Gecko/20100101 Firefox/6.0.2')]
        urllib2.install_opener(s)

        self.session = s

        try:
            self.login()
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.quit()

    def login(self):
        pass

    def getdoc(self, url, read=True, lxml=True, encoding=None, attempts=3):
        """Fetch a document from `url`. This method tries to determine the encoding of the document
        by looking at the HTTP headers. If those are missing, it leaves lxml to decide the
        encoding. 

        Furthermore, it tries three times to fetch the url before raising an error.

        @type url: str / unicode
        @param url: url to fetch

        @type read: boolean
        @param read: if False, return file-like object

        @type lxml: boolean
        @param lxml: if False, return bytes only

        @type encoding: boolean
        @param encoding: force an encoding of the document

        @type attempts: integer
        @param attempts: bail out after n tries"""
        def _getenc(ro):
            """Return charset (from HTTP-Headers). If not found, return None."""
            ht = 'Content-Type'

            headers = dict(ro.getheaders()) if hasattr(ro, 'getheaders') else dict(ro.headers)
            if ht in headers:
                for arg in headers[ht].split(';'):
                    if arg.strip().startswith('charset='):
                        return arg.strip()[8]

        log.info('Retrieving "%s"' % urllib.unquote(url))
        for i in range(attempts):
            try:
                fo = self.session.open(url)
                if not read:
                    return fo
                elif not lxml:
                    return fo.read()

                enc = encoding or _getenc(fo)
                if enc is not None:
                    # Encoding found or forced!
                    res = unicode(fo.read(), encoding=enc)
                    #log.info('retrv')
                    return html.fromstring(res)
                else:
                    # Let lxml decide the encoding
                    
                    a= html.parse(fo).getroot()
                    #log.info('retrv')
                    return a
            except urllib2.URLError as e:
                if (i+1 < attempts):
                    time.sleep(1.5)
                    continue
                else:
                    raise(e)

class PCMScraper(HTTPScraper):
    """Scraper for PCM Newspapers"""
    def login(self):
        doc = self.getdoc(self.login_url)
        frm = toolkit.parse_form(doc.cssselect('form')[0])
        frm.update(self.login_data)

        return self.session.open(self.login_url, urllib.urlencode(frm)).read()

class CommentScraper(Scraper):
    """A CommentScraper replaces `get` with `main` and `comments`."""
    def get(self, date):
        for doc in self.main(date):
            yield doc

            com = doc.copy(parent=doc)
            for c in self.comments(com):
                yield c

    def main(self, date):
        return []

    def comments(self, com):
        return []

class GoogleScraper(HTTPScraper):
    """Some websites don't have archives. Google enables us to search for those pages."""
    def __init__(self, options=None, domain=None, pps=100, **kargs):
        """
        @type domain: str
        @param domain: domain to limit search to

        @type pps: int
        @param pps: pages per search"""
        super(GoogleScraper, self).__init__(options, **kargs)

        self.google_url = 'http://www.google.nl/search?'
        self.domain = domain
        self.pps = pps

        # Init cookies
        self.getdoc(self.google_url)

    def _genurl(self, term, page=0):
        q = term + ' site:%s' % self.domain if self.domain else term

        query = {
            'num' : self.pps,
            'hl' : 'nl',
            'btnG' : 'Zoeken',
            'q' : q,
            'start' : page * self.pps
        }

        return self.google_url + urllib.urlencode(query)

    def formatterm(self, date):
        return None

    def init(self, date, page=0):
        """
        @type date: datetime.date, datetime.datetime
        @param date: date to scrape for.
        """
        term = self.formatterm(date)
        url = self._genurl(term, page)

        results = self.getdoc(url).cssselect('h3.r > a.l')
        for a in results:
            url = a.get('href')
            yield objects.HTMLDocument(url=url, date=date)

        if len(results) == self.pps:
            for d in self.init(date, page=page+1):
                yield d

class PhpBBScraper(HTTPScraper):
    def init(self):
        """
        PhpBB forum scraper
        """
        index = self.getdoc(self.index_url)

        for cat_title, cat_doc in self.get_categories(index):
            for page in self.get_pages(cat_doc):
                for fbg in page.cssselect('.forumbg'):
                    if 'announcement' in fbg.get('class'):
                        continue

                    for a in fbg.cssselect('.topics > li a.topictitle'):
                        url = urlparse.urljoin(self.index_url, a.get('href'))
                        yield objects.HTMLDocument(headline=a.text, url=url, category=cat_title)

    def get_pages(self, cat_doc, debug=False):
        """Get each page specified in pagination division."""
        yield cat_doc # First page, is always available

        if cat_doc.cssselect('.pagination .page-sep'):
            pages = cat_doc.cssselect('.pagination a')
            try:
                pages = int(pages[-1].text)
            except:
                pages = int(pages[-2].text)

            spage = cat_doc.cssselect('.pagination span a')[0]

            if int(spage.text) != 1:
                url = list(urlparse.urlsplit(spage.get('href')))

                query = dict([(k, v[-1]) for k,v in urlparse.parse_qs(url[3]).items()])
                ppp = int(query['start'])

                for pag in range(1, pages):
                    query['start'] = pag*ppp
                    url[3] = urllib.urlencode(query)

                    yield self.getdoc(urlparse.urljoin(self.index_url, urlparse.urlunsplit(url)))

    def get_categories(self, index):
        """
        @yield: (category_name, lxml_doc)
        """
        hrefs = index.cssselect('.topiclist a.forumtitle')

        for href in hrefs:
            url = urlparse.urljoin(self.index_url, href.get('href'))
            yield href.text, self.getdoc(url)
    
    def get(self, thread):
        fipo = True # First post?
        for page in self.get_pages(thread.doc, debug=True):
            for post in page.cssselect('.post'):
                ca = thread if fipo else thread.copy(parent=thread)
                ca.props.date = atoolkit.readDate(post.cssselect('.author')[0].text_content()[-22:])
                ca.props.text = post.cssselect('.content')

                try:
                    ca.props.author = post.cssselect('.author strong')[0].text_content()
                except:
                    try:
                        ca.props.author = post.cssselect('.author a')[0].text_content()
                    except:
                        # Least reliable method
                        ca.props.author = post.cssselect('.author')[0].text_content().split()[0]

                yield ca

                fipo = False


class ContinuousScraper(Scraper):
    """This scraper class is meant to run continually in the background.
    """
    def __init__(self, options=None, **kargs):
        super(ContinuousScraper, self).__init__(options, **kargs)

        




