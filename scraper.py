import log, toolkit, dbtoolkit, re, urllib2, article, urllib
from BeautifulSoup import BeautifulSoup
from PIL import Image
import cStringIO, articlecreator
from datetime import datetime, date

l = log.Logger(dbtoolkit.amcatDB(), __name__, log.levels.notice)

class ArticleDescriptor(object):
    def __init__(self, body, headline, date=None, byline=None, pagenr=None, url=None, section=None, imagebytes=None, imagetype=None, fullmeta=None, **args):
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
    def createArticle(self, db, batchid, mediumid, date, imagescale=.67):
        body = stripText(self.body)
        byline = stripText(self.byline)
        headline = stripText(self.headline)
        if date is None: date = self.date
        if date is None: raise Exception("No date for article %s" % self.url)

        if not body and not headline:
            l.notice('missing body and headline %s' % self.url)
            return None
        elif not body:
            l.notice('Missing body %s' % self.url)
            return None
        elif not headline: l.notice('Missing headline %s' % self.url)
        
        a = articlecreator.createArticle(db, headline, self.date, mediumid, batchid, body, 
                                  pagenr=self.pagenr, byline=self.byline, url=self.url,
                                  section=self.section, fullmeta=self.fullmeta)
        if self.imagebytes:
            imagebytes = convertImage(self.imagebytes, imagescale)
            articlecreator.storeImage(db,a.id,imagebytes, self.imagetype)
        self.aid = a.id
        return a
    def __str__(self):
        return "ArticleDescriptor(%r, %r, %r, ..)" % (self.body and self.body[:5]+"...", self.headline, self.date)
    __repr__ = __str__


def convertImage(img, scale=.67, quality=.2):
    img2 = toolkit.convertImage(img, 'jpeg', scale=scale, quality=quality)
    #print "Reduced image size from %i to %i bytes (%1.2f%%)" % (len(img), len(img2), float(len(img2)) * 100. / len(img))
    return img2

class ArticleScraper(object):
    def __init__(self, db, batch, mediumid, name, date=None, imagescale = .67):
        self.db = db
        self.batch = batch
        self.mediumid = mediumid
        self.articleCount, self.downloadCount = 0,0
        self.name = name
        self.date = date
        self.log = log.Logger(dbtoolkit.amcatDB(), __name__, log.levels.notice)
        self.limit_page = None
        self.limit_articlesperpage = None
        self.force = False
        self.imagescale = imagescale
        self.commitPage = False

    def urlExists(self, url):
        sql = "select top 1 url from articles where batchid=%i and mediumid=%i and url=%s" % (self.batch, self.mediumid, dbtoolkit.quotesql(url))
        data = self.db.doQuery(sql)
        return bool(data)
        
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
                                
        
    def scrape(self, context=None):
        self.checkDate(context)
        self.startScrape()
        pages = list(set(self.getPages(context)))
        if not pages:
            self.logException('No pages found for scraper %s / %s, date %s' % (self.__class__, self.name, context))
            return
        if self.limit_page: pages = sorted(list(pages))[:self.limit_page]                       
        for page in pages:
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
    
    def dateStr(self, date):
        """ date format as used in most URLs, override as appropriate """
        return date.strftime("%Y%m%d")
    def endPage(self, context, page):
        if self.commitPage:
            self.db.commit()
    def login(self):
        pass
    def getPages(self, context):
        return [None]
    def getArticles(self, context, page):
        abstract
        return [address1, address2]
    def getArticle(self, context, page, address):
        abstract
        return ArticleDescriptor()
    def init(self, context):
        pass

    def logInfo(self, msg):
        l.info(msg, application=self.name)
        
    def logException(self, msg=""):
        l.error(msg + '\n' + toolkit.returnTraceback(), application=self.name)

    def startScrape(self):
        self.resetStatistics()
        self.createSession()
        self.login()
    def endScrape(self, context):
        self.logStatistics()
        self.db.commit()
      
    def createSession(self):
        self.session = urllib2.build_opener(urllib2.HTTPCookieProcessor())
        urllib2.install_opener(self.session)
        self.session.addheaders = [ ('user-agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.0; en-GB; rv:1.8.1.4) Gecko/20070515 Firefox/2.0.0.4') ]  
        
    

    def createArticle(self, artdesc):
        url = artdesc.url
        if url and self.urlExists(url):
            self.logInfo('Skipping duplicate url %r' % url)
            return
        result = artdesc.createArticle(self.db, self.batch, self.mediumid, self.date, imagescale = self.imagescale)
        if result: self.articleCount += 1
        return result

        
    def download(self, url, allowRedirect=False, useSoup=False, postdata=None, canretry=True):
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
        return decode(response)
    
    def createIndexArticle(self, articleDict, pagenr, url, date=None, section=None, imagebytes=None, imagetype='jpg'):
        """
        supply an articledict {aid : [coord, coord, ...]}
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

    def logStatistics(self):
        self.logInfo('Downloaded %i urls. Added %i articles' % (self.downloadCount, self.articleCount))
    def resetStatistics(self):
        self.articleCount, self.downloadCount = 0,0
    def convertImage(self, image, *args, **kargs):
        return convertImage(image, *args, **kargs)
    
stripRegExpTuple = (
    (re.compile(ur'<(script|style).*?</(script|style)>', re.IGNORECASE | re.DOTALL), u''),
    (re.compile(ur'<br ?/?>|</?p>|</div>', re.IGNORECASE), u'\n'),
    (re.compile(ur'<[^>]*>|\r'), u''),
    (re.compile(ur'[ \t]+'), u' '),
    (re.compile(ur'^ +\n|\n +$', re.MULTILINE), u'\n'),
    (re.compile(ur'\n\n+'), u'\n\n'),
)
                
def stripText(text, removeSpecial=False):
    if not text: return text

    for regExp, replacement in stripRegExpTuple:
        #print regExp
        text = regExp.sub(replacement, text)

    if removeSpecial:
        text = re.sub(ur'[^\w \-,\.\!\?\:/]+', '', text)

    text = toolkit.unescapeHtml(text)
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

    
