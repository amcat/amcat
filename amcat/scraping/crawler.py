from amcat.scraping.scraper import HTTPScraper, ScraperForm, AuthForm
import logging; log = logging.getLogger(__name__)
from urlparse import urljoin
import urllib2
from urllib import quote


class Crawler(HTTPScraper):
    options_form = ScraperForm
    initial_url = ""
    queue = set([])
    completed_urls = []
    include_patterns = []
    deny_patterns = []

    def _get_units(self):
        for unit in self.crawl_page(self.initial_url):
            yield unit
        while self.queue:
            for unit in self.crawl_page(self.queue.pop()):
                yield unit

    def crawl_page(self,url):
        log.debug("Queue: {n_queue}, Done: {n_completed}; Crawling {url!r}".format(n_queue = len(self.queue), n_completed = len(self.completed_urls), **locals()))
        self.completed_urls.append(url)
        try:
            doc = self.getdoc(url)
        except (urllib2.HTTPError,urllib2.URLError) as e:
            return
        if doc == None:
            return
        if self.article_url(url):
            yield [url,doc]
        urls = [urljoin(url,a.get('href')) for a in doc.cssselect("a")]
        for url in urls:
            try:
                url = quote(url, safe="%/:=&?~#+!$,;'@()*[]")
            except KeyError:
                break
            if self.correct_url(url):
                self.queue.add(url)

    def correct_url(self,url):
        conditions = [
            "c = url[0:4] == 'http'",
            "c = any([pattern.search(url) for pattern in self.include_patterns])",
            "c = not any([pattern.search(url) for pattern in self.deny_patterns])",
            "c = url not in self.completed_urls",
            ]
        for con in conditions:
            exec con
            if not c:
                return False
            # check condition one by one for speed

        return True

class AuthCrawler(Crawler):
    """Base class for crawlers that require a login"""
    options_form = AuthForm

    def _login(self, username, password):
        """Login to the resource to crawl, if needed. Will be called 
        at the start of get_units()"""
        raise NotImplementedError()

    def _initialize(self):
        self._login(self.options['username'], self.options['password'])
