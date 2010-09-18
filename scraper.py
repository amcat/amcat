import log, toolkit, dbtoolkit, re, urllib2, article, urllib
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from PIL import Image
import cStringIO, articlecreator
from datetime import datetime, date
#import wordfrequency

l = log.Logger(dbtoolkit.amcatDB(), __name__, log.levels.notice)

class ArticleDescriptor(object):
    def __init__(self, body, headline, date=None, byline=None, pagenr=None, url=None, section=None, imagebytes=None, imagetype=None, fullmeta=None, batch=None, mediumid=None, externalid=None, parentUrl=None, rawtext=False, stripAccents=True, **args):
        self.body = body
        self.headline = headline
        self.date = date
        self.byline = byline
        self.pagenr = pagenr
        self.url = url
        self.section = section
        self.args = args
        self.imagebytes = imagebytes
        self.imagetype = imagetype
        self.fullmeta = fullmeta
        self.aid = None
        self.batch = batch
        self.mediumid = mediumid
        self.externalid = externalid
        self.parentUrl = parentUrl
        self.rawtext = rawtext
        self.stripAccents = stripAccents
 
    def createArticle(self, db, batchid, mediumid, date, imagescale=.67):
        body = self.body if self.rawtext else self.stripText(self.body)
        byline = self.stripText(self.byline)
        headline = self.stripText(self.headline)
        if date is None: date = self.date
        if date is None: raise Exception("No date for article %s" % self.url)
        
        if not self.batch: self.batch = batchid
        if not self.mediumid: self.mediumid = mediumid
        if not body and not headline:
            l.notice('missing body and headline %s' % self.url)
            return None
        elif not body:
            l.notice('Missing body %s' % self.url)
            return None
        elif not headline: l.notice('Missing headline %s' % self.url)
        
        a = articlecreator.createArticle(db, headline, self.date, self.mediumid, self.batch, body, 
                                  pagenr=self.pagenr, byline=self.byline, url=self.url,
                                  section=self.section, fullmeta=self.fullmeta, externalid=self.externalid,
                                  parentUrl=self.parentUrl)
        if self.imagebytes:
            imagebytes = convertImage(self.imagebytes, imagescale)
            articlecreator.storeImage(db,a.id,imagebytes, self.imagetype)
        self.aid = a.id
        return a
    def __str__(self):
        return "ArticleDescriptor(%r, %r, %r, ..)" % (self.body and self.body[:5]+"...", self.headline, self.date)
    __repr__ = __str__

    def stripText(self, text):
        return stripText(text, stripAccents = self.stripAccents)


def convertImage(img, scale=.67, quality=.2):
    img2 = toolkit.convertImage(img, 'jpeg', scale=scale, quality=quality)
    #print "Reduced image size from %i to %i bytes (%1.2f%%)" % (len(img), len(img2), float(len(img2)) * 100. / len(img))
    return img2

class Scraper(object):
    def __init__(self, db, batch, mediumid, name, date=None, imagescale=.67, tick=False):
        self.db = db
        self.batch = batch
        self.mediumid = mediumid
        self.articleCount, self.downloadCount = 0,0
        self.name = name
        self.date = date
        self.log = log.Logger(dbtoolkit.amcatDB(), __name__, log.levels.notice)
        self.imagescale = imagescale
        query = "select url, articleid from articles where batchid = '%i'" % self.batch
        if self.mediumid: query += " and mediumid = '%i'" % self.mediumid
        data = self.db.doQuery(query)
        self.urls = dict(data)
        self.tick = tick

    def urlExists(self, url):
        return url in self.urls

    def checkDate(self, context):
        if isinstance(context, datetime) or isinstance(context, date):
            bmd = self.batch, self.mediumid, dbtoolkit.quotesql(context)
            sql = "select count(*) from articles where batchid=%i and mediumid=%i and date=%s" % bmd
            #print sql
            d = self.db.getValue(sql)
            if d and not self.force:
                raise Exception("Refusing to scrape, %s articles already exist in batch %i, medium %i, date %s" % tuple([d]+list(bmd)))
        else:
            toolkit.warn(type(context))
    def dateStr(self, date):
        """ date format as used in most URLs, override as appropriate """
        return date.strftime("%Y%m%d")
                                
    def logInfo(self, msg):
        self.log.info(msg, application=self.name)    
    def logWarning(self, msg):
        self.log.warning(msg, application=self.name)
    def logException(self, msg=""):
        self.log.error(msg + '\n' + toolkit.returnTraceback(), application=self.name)
    def createArticle(self, artdesc):
        url = artdesc.url
        if artdesc.url and self.urlExists(artdesc):
            self.logInfo('Skipping duplicate url %r' % artdesc.url)
            return
        result = artdesc.createArticle(self.db, self.batch, self.mediumid, self.date, imagescale = self.imagescale)
        if result:
            self.articleCount += 1
            self.urls[url] = result.id
        self.linkChildWithParent(artdesc)
        return result
    def logStatistics(self):
        self.logInfo('Downloaded %i urls. Added %i articles' % (self.downloadCount, self.articleCount))
    def resetStatistics(self):
        self.articleCount, self.downloadCount = 0,0
    def convertImage(self, image, *args, **kargs):
        return convertImage(image, *args, **kargs)
    def linkChildWithParent(self, c_desc):
        if not c_desc.aid:
            return
        
        if not c_desc.parentUrl:
            return
            
        if c_desc.parentUrl in self.urls:
            parentid = self.urls.get(c_desc.parentUrl)
        else:
            parentid = self.db.getValue(
                "select articleid from articles wherer batchid=%i and url=%s" %
                (self.batch, toolkit.quotesql(c_desc.parentUrl)))

        if not parentid:
            self.logWarning("Could not find parent article <%s>" % c_desc.parentUrl)
        else:
            self.urls[c_desc.parentUrl] = parentid
            self.db.insert("articles_postings",
                dict(articleid=c_desc.aid, parent_articleid=parentid),
                retrieveIdent=False)
            #self.logInfo(">>> Linked %i to %i" % (c_desc.aid, parentid))

    def startScrape(self):
        self.resetStatistics()
    def endScrape(self, context):
        self.logStatistics()
        self.db.commit()
        #wordfrequency.save() rob?

class ArticleScraper(Scraper):
    def __init__(self, db, batch, mediumid, name, date=None, imagescale = .67):
        Scraper.__init__(self, db, batch, mediumid, name, date, imagescale)
        self.limit_page = None
        self.limit_articlesperpage = None
        self.force = False
        self.commitPage = False

    #######################################################
    ## Main scraping logic and aux methods               ##
    #######################################################        
    def scrape(self, context=None):
        self.checkDate(context)
        self.startScrape()
        pages = list(set(self.getPages(context)))
        if not pages:
            self.logException('No pages found for scraper %s / %s, date %s' % (self.__class__, self.name, context))
            return
        if self.limit_page: pages = sorted(list(pages))[:self.limit_page]                       
        for page in pages:
            print page
            try:
                articles = self.getArticles(context, page)
                if self.limit_articlesperpage: articles = list(articles)[:self.limit_articlesperpage]
                for address in articles:
                    try:
                        artdescs = self.getArticle(context, page, address)
                        if artdescs is None: continue
                        if isinstance(artdescs, ArticleDescriptor):
                            artdescs = [artdescs]
                        for artdesc in artdescs:
                            self.createArticle(artdesc)
                    except:
                        self.logException('Article exception %s' % address)
                self.endPage(context, page)
            except:
                self.logException('Page exception %s' % str(page))
        self.endScrape(context)
    def startScrape(self):
        Scraper.startScrape(self)
        self.createSession()
        self.login()
    def createSession(self):
        self.session = urllib2.build_opener(urllib2.HTTPCookieProcessor())
        urllib2.install_opener(self.session)
        self.session.addheaders = [ ('user-agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.0; en-GB; rv:1.8.1.4) Gecko/20070515 Firefox/2.0.0.4') ]  
    def endPage(self, context, page):
        if self.commitPage:
            self.db.commit()
    def download(self, url, allowRedirect=False, useSoup=False, postdata=None, canretry=True, useStoneSoup=False):
        self.logInfo('downloading %s' % url)
        if postdata:
            response = self.session.open(url, urllib.urlencode(postdata))
        else:
            response = self.session.open(url)
        if not allowRedirect and response.url != url:
            if canretry:
                self.logInfo('Redirect attempted, logging in again (-> %r)' % (response.url))
                self.login()
                self.download(url, allowRedirect, useSoup, postdata, canretry=False)
            else:
                raise Exception('disallowed redirect from %s to %s' % (url, response.url))
        self.downloadCount += 1
        if useSoup:
            return BeautifulSoup(response)
        if useStoneSoup:
            return BeautifulStoneSoup(response)
        return decode(response)
    
    def createIndexArticle(self, articleDict, pagenr, url, date=None, section=None, imagebytes=None, imagetype='jpg'):
        """
        supply an articledict {aid : [coord, coord, ...]}

        TODO: use URLs instead of article IDs...?
        """
        if self.urlExists(url):
            self.logInfo('Skipping duplicate url %r' % url)
            return
        if date is None: date = self.date
        if date is None: raise Exception("No date for index article %s" % url)
        body = '[IMAGEMAP-1]\n'
        for a in articleDict:
            if not isinstance(a, article.Article): continue
            for coords in articleDict[a]:
                coords = ", ".join(str(int(c * self.imagescale)) for c in coords)
                body += '[%s->%s]\n' % (coords, a.id)
        a = articlecreator.createArticle(self.db, "[INDEX] page %s" % pagenr, date, self.mediumid, self.batch, body, section=section, url=url, pagenr=pagenr)
        if imagebytes:
            articlecreator.storeImage(self.db,a.id,convertImage(imagebytes), imagetype)
        return a

    #########################################################
    ## Methods to override by subclass to control scraping ##
    #########################################################
    def login(self):
        "Login at the site if needed. Subclass may override"
        pass
    def getPages(self, context):
        """Get pages for the given context (ie date); return sequence of 'page' objects.
        Subclass may override if there is more than one page"""
        return [None]
    def getArticles(self, context, page):
        """Get the articles on the given context and page; return sequence of 'article' objects.
        Subclasses *must* override. """
        abstract
    def getArticle(self, context, page, address):
        """Get the article(s) corresponding to the given address, page, and context.
        Return (a sequence of) ArticleDescriptor.
        Subclasses *must* override."""
        abstract
        return ArticleDescriptor()
    def init(self, context):
        "Initialize the given context. WvA: Unclear when it is called, if at all???"
        pass


class TextImporter(Scraper):
    def __init__(self, db, batch, mediumid, name, *args, **kargs):
        Scraper.__init__(self, db, batch, mediumid, name, *args, **kargs)

    #######################################################
    ## Main scraping logic and aux methods               ##
    #######################################################        
    def scrape(self, context=None):
        self.startScrape()
        files = list(set(self.getFiles(context)))
        if not files:
            self.logException('No files found for scraper %s / %s, date %s' % (self.__class__, self.name, context))
            return
        if self.tick: files = toolkit.tickerate(files)
        for file in files:
            try:
                if type(file) in (str, unicode): file = open(file)
                documents = self.splitFile(context, file)
                for doc in documents:
                    try:

                        artdescs = self.getArticle(context, file, doc)
                        if artdescs is None: continue
                        if isinstance(artdescs, ArticleDescriptor):
                            artdescs = [artdescs]
                        for artdesc in artdescs:
                            self.createArticle(artdesc)
                    except Exception, e:
                        import traceback
                        traceback.print_exc()
                        self.logException('Article exception file %s doc %r' % (file, doc[:40]))
            except:
                self.logException('SplitFile exception %s' % str(file))
        self.endScrape(context)
        
    #########################################################
    ## Methods to override by subclass to control scraping ##
    #########################################################
    def getFiles(self, context):
        """Return a sequence of filenames or files to be scraped.
        If strings are returned, they will be opened using open(.), otherwise
        they will be passed on to splitFile as-is.
        Subclasses *must* override"""
        abstract
    def splitFile(self, context, file):
        """Split the given file into documents, returning document objects
        (eg strings) that will be passed onto getArticle(.).
        Subclasses *may* override. Default returns entire file as one string"""
        return [file.read()]
    def getArticle(self, context, file, doc):
        """Convert the given document into one or more ArticleDescriptors
        Subclasses *must* override"""
        abstract
    
stripRegExpTuple = (
    (re.compile(ur'<(script|style).*?</(script|style)>', re.IGNORECASE | re.DOTALL), u''),
    (re.compile(ur'<br ?/?>|</?p>|</div>', re.IGNORECASE), u'\n'),
    (re.compile(ur'<[^>]*>|\r'), u''),
    (re.compile(ur'[ \t]+'), u' '),
    (re.compile(ur'^ +\n|\n +$', re.MULTILINE), u'\n'),
    (re.compile(ur'\n\n+'), u'\n\n'),
)
                
def stripText(text, removeSpecial=False, stripAccents=True):
    if not text: return text

    for regExp, replacement in stripRegExpTuple:
        #print regExp
        text = regExp.sub(replacement, text)

    if removeSpecial:
        text = re.sub(ur'[^\w \-,\.\!\?\:/]+', '', text)

    text = toolkit.unescapeHtml(text)
    if stripAccents:
        text = toolkit.stripAccents(text)
    
    return text.strip()

def decode(response):
    html = response.read()
    encoding = None
    m = re.search('charset=([\w\-]+)', response.info().get('content-type', ''))
    if m: encoding = m.group(1)
    else:
        m = re.search('charset=([\w\-]+)', html)
        if m: encoding = m.group(1)
    encodings = (encoding, 'latin-1', 'utf-8')
    for encoding in encodings:
        try:
            html = html.decode(encoding)
            toolkit.warn("Decoded with %s" % encoding)
            break
        except:
            pass
    if type(html) != unicode:
        raise Exception('Failed to decode response: %s' % url)
    return html


tagsRegExp = re.compile(r'<[^<]*?>')
def removeTags(text):
    if not text: return text
    return tagsRegExp.sub("", text)  

    
