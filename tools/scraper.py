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
(Base) classes for scraping.

ArticleDescriptor is a container for hold article fields (TODO can be replaced by dict??)
Scraper is an (internal) abstract base class representing any X -> [articles] scraper 
ArticleScraper is a base class representing scraping from the web. It assumes that sites have
  are pages that contain articles. To be subclassed by actual scrapers.
TextImporter is a base class representing importing articles from (e.g. text) files.
  If assumes that there are files containing documents.
"""

from __future__ import unicode_literals, print_function, absolute_import

from amcat.tools import toolkit
from amcat.db import dbtoolkit
from amcat.model import article

import logging, re, urllib2, urllib, sys
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
import cStringIO
from datetime import datetime, date
import sys
#import wordfrequency


log = logging.getLogger(__name__)

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
            log.warn('missing body and headline %s' % self.url)
            return None
        elif not body:
            log.warn('Missing body %s' % self.url)
            return None
        elif not headline: log.warn('Missing headline %s' % self.url)
        
        a = createArticle(db, headline, self.date, self.mediumid, self.batch, body, 
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
    def __init__(self, db, batch=None, mediumid=None, name=None, date=None, imagescale=.67, tick=False):
        self.db = db
        self.batch = batch
        self.mediumid = mediumid
        self.articleCount, self.downloadCount = 0,0
        self.name = name
        self.date = date
        self.imagescale = imagescale
        if self.batch:
            query = "select url, articleid from articles where batchid = '%i'" % self.batch
            if self.mediumid: query += " and mediumid = '%i'" % self.mediumid
            data = self.db.doQuery(query)
            self.urls = dict(data)
        else:
            self.urls = {}
        self.tick = tick

    def urlExists(self, url):
        return url in self.urls

    def checkDate(self, context):
        if isinstance(context, datetime) or isinstance(context, date):
            bmd = self.batch, self.mediumid, dbtoolkit.quotesql(context)
            sql = "select count(*) from articles where batchid=%i and mediumid=%i and date=%s" % bmd
            #printsql
            d = self.db.getValue(sql)
            if d and not self.force:
                raise Exception("Refusing to scrape, %s articles already exist in batch %i, medium %i, date %s" % tuple([d]+list(bmd)))
        else:
            toolkit.warn(type(context))
    def dateStr(self, date):
        """ date format as used in most URLs, override as appropriate """
        return date.strftime("%Y%m%d")
                                
    def createArticle(self, artdesc):
        url = artdesc.url
        if artdesc.url and self.urlExists(artdesc):
            log.info('Skipping duplicate url %r' % artdesc.url)
            return
        result = artdesc.createArticle(self.db, self.batch, self.mediumid, self.date, imagescale = self.imagescale)
        if result:
            self.articleCount += 1
            self.urls[url] = result.id
        self.linkChildWithParent(artdesc)
        return result
    def logStatistics(self):
        log.info('Downloaded %i urls. Added %i articles' % (self.downloadCount, self.articleCount))
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
            log.warning("Could not find parent article <%s>" % c_desc.parentUrl)
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
    def __init__(self, db, batch=None, mediumid=None, name=None, date=None, imagescale = .67):
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
            log.warn('No pages found for scraper %s / %s, date %s' % (self.__class__, self.name, context))
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
                    except KeyboardInterrupt:
                        raise KeyboardInterrupt
                    except:
                        log.warn('Article exception %s' % address)
                self.endPage(context, page)
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                log.warn('Page exception %s' % str(page))
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
        log.info('downloading %s' % url)
        if postdata:
            response = self.session.open(url, urllib.urlencode(postdata))
        else:
            response = self.session.open(url)
            
        if url.find('#') > -1: url = url[:url.find('#')]
        if not allowRedirect and response.url != url:
            if canretry:
                log.info('Redirect attempted, logging in again (-> %r)' % (response.url))
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
            log.info('Skipping duplicate url %r' % url)
            return
        if date is None: date = self.date
        if date is None: raise Exception("No date for index article %s" % url)
        body = '[IMAGEMAP-1]\n'
        for a in articleDict:
            if not isinstance(a, article.Article): continue
            for coords in articleDict[a]:
                coords = ", ".join(str(int(c * self.imagescale)) for c in coords)
                body += '[%s->%s]\n' % (coords, a.id)
        a = createArticle(self.db, "[INDEX] page %s" % pagenr, date, self.mediumid, self.batch, body, section=section, url=url, pagenr=pagenr)
        if imagebytes:
            storeImage(self.db,a.id,convertImage(imagebytes), imagetype)
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

    #######################################################
    ## Main scraping logic and aux methods               ##
    #######################################################        
    def scrape(self, context=None):
        self.startScrape()
        files = list(set(self.getFiles(context)))
        if not files:
            log.warn('No files found for scraper %s / %s, date %s' % (self.__class__, self.name, context))
            return
        if self.tick: files = toolkit.tickerate(files)
        for file in files:
            try:
                documents = self.splitFile(context, file)
                for doc in documents:
                    try:

                        artdescs = self.getArticle(context, file, doc)
                        if artdescs is None: continue
                        if isinstance(artdescs, ArticleDescriptor):
                            artdescs = [artdescs]
                        for artdesc in artdescs:
                            self.createArticle(artdesc)
                    except KeyboardInterrupt:
                        raise KeyboardInterrupt
                    except Exception, e:
                        import traceback
                        traceback.print_exc()
                        log.warn('Article exception file %s doc %r' % (file, doc[:40]))
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except Exception, e:
                import traceback
                traceback.print_exc()
                log.warn('SplitFile exception %s at %s' % (e, str(file)))
        self.endScrape(context)
        
    #########################################################
    ## Methods to override by subclass to control scraping ##
    #########################################################

    def getFiles(self, context):
        """Return a sequence of filenames or files to be scraped.
        If strings are returned, they will be opened using open(.), otherwise
        they will be passed on to splitFile as-is.
        Subclasses *may* override; default will return context as-is"""
        return context
    def splitFile(self, context, file):
        """Split the given file into documents, returning document objects
        (eg strings) that will be passed onto getArticle(.).
        Subclasses *may* override. Default opens and reads file and returns as one string"""
        if type(file) in (str, unicode): file = open(file)
        file = file.read()
        return [file]
    def getArticle(self, context, file, doc):
        """Convert the given document into one or more ArticleDescriptors
        Subclasses *must* override"""
        abstract
        
class ArticlesImage(object):
    """Split one `short news` image to seperate images
    
    @example:
    >>> f = open('image.jpg')
    >>> i = ArticlesImage(f)
    >>> tuple(i.article_images)
    (<Image._ImageCrop image mode=RGB size=250x457 at 0xA26A1CC>,
    <Image._ImageCrop image mode=RGB size=250x337 at 0xA26A2CC>,
    <Image._ImageCrop image mode=RGB size=250x337 at 0xA26A2EC>,
    <Image._ImageCrop image mode=RGB size=250x342 at 0xA26A30C>)
    
    For more information on Image._ImageCrop, see PIL Documentation
    """
    def __init__(self, f):
        from PIL import Image
        self.max = 255 #+ 255 + 255
        self.min_headline = 20
        
        self.oi = Image.open(f)
        self.bw = self.oi.convert('1')
        self.inv = tuple((self.max - x for x in xrange(self.max + 1)))
        
        self.row_scores_cache = None
    
    #### PRIVATE FUNCTIONS AND PROPERTIES ####
    
    def _getPixelScores(self, r):
        """For each pixel in `r` return an (inverted) score"""
        w = self.oi.size[0]
        for c in xrange(w):
            #pixel_score = sum(self.i.getpixel((c, r)))
            #yield self.inv[pixel_score]
            #print self.bw.getpixel((c, r))
            yield self.inv[self.bw.getpixel((c, r))]
            
    def _getLines(self):
        prev = self._is_white(self._row_scores[0])
        
        height = 0
        for s in self._row_scores:
            white = self._is_white(s)
            
            if prev == white:
                height += 1
             
                continue
                
            
            yield (prev, height + 1)
            prev, height = white, 0
    
    def _getHeadlines(self):
        for i, line in enumerate(self.lines):
            white, height = line
            
            if not white and height > self.min_headline:
                yield i
                
    def _is_white(self, row_score):
        return (row_score == 0)
    
    @property
    def _row_scores(self):
        """Return inverted score for each row"""
        
        # Return cache if possible
        if self.row_scores_cache: return self.row_scores_cache
        
        # Calculate row scores
        w, h = self.oi.size
        
        scores = []
        for row in xrange(h):
            scores.append(sum(self._getPixelScores(row)))
        self.row_scores_cache = scores
        
        return scores
    

    #### PUBLIC FUNCIONS AND PROPERTIES ####
            
    @property
    def lines(self):
        return tuple(self._getLines())
    
    @property
    def headlines(self):
        """Get headlines
        
        @yield: y1, y2"""
        headlines = tuple(self._getHeadlines())
        
        if headlines: 
            prev = headlines[0]
            start = 0
         
        for i, h in enumerate(headlines):
            if (h - prev) > 2:
                yield headlines[start], headlines[i-1]
                start = i
               
            if i is (len(headlines) - 1):
                # End of loop
                yield headlines[start], h
            
            prev = h
            
    @property
    def articles(self):
        headlines = tuple(self.headlines)
        for i, h in enumerate(headlines):
            if i is (len(headlines) - 1):
                yield h[0], len(self.lines)
                break
            
            yield h[0], headlines[i + 1][0] - 2
            
    @property
    def article_images(self):
        for a in self.articles:
            upper, lower = self.getYCoordinates(*a)
            yield self.oi.crop((0, upper, self.oi.size[0], lower))
            
    def getYCoordinates(self, line1, line2):
        """Get the top y-coordinate and bottom y-coordinate"""
        heights = [x[1] for x in self.lines]
        
        begin = sum(heights[:line1]) - (heights[line1 - 1] / 2)
        end = sum(heights[:line2 + 1]) + (heights[line1 + 1] / 2)
        
        return begin, end
    
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

    


# TODO This should be merged into the normal .create() structure asap! 
import binascii, types

def createArticle(db, headline, date, source, batchid, text, texttype=2,
                  length=None, byline=None, section=None, pagenr=None, fullmeta=None, url=None, externalid=None, parentUrl=None, retrieveArticle=1):
    """
    Writes the article object to the database
    """
    # TODO link to parent if parentUrl is not None

    if toolkit.isDate(date): date = toolkit.writeDateTime(date, 1)
    if type(source) != int: source = source.id
    if type(fullmeta) == dict: fullmeta = `fullmeta`

    if url and len(url) > 490: url = url[:490] + "..."

    (headline, byline, fullmeta, section), encoding = encodeAndLimitLength([headline, byline, fullmeta, section], [740, 999999, 999999, 90])
    
    if pagenr and type(pagenr) in (types.StringTypes): pagenr = pagenr.strip()
    if text: text = text.strip()
    if length == None and text: length = len(text.split())

    
    q = {'date' : date,
         'length' : length,
         'metastring' : fullmeta,
         'headline' : headline,
         'byline' : byline,
         'section' : section,
         'pagenr': pagenr,
         'batchid' : batchid,
         'mediumid' : source,
         'url':url,
         'externalid':externalid,
         'encoding' : encoding,
         # We don't store the parentUrl. Instead, we use the articles_postsings
         # table to store this information. This is done by the scraper class.
        }
    aid = db.insert('articles', q)
    text, encoding = dbtoolkit.encodeText(text)
    
    q = {'articleid' : aid,
         'type' : texttype,
         'encoding' : encoding,
         'text' : text}
    db.insert('texts', q, retrieveIdent=0)
    
    if retrieveArticle:
        return article.Article(db, aid)
    
def storeImage(db,id, imgdata, format):
    from pil import image
    SQL = "DELETE FROM articles_image WHERE articleid=%i" % (id,)
    db.doQuery(SQL)                                              
    imgdata = binascii.hexlify(imgdata)                               
    SQL = "INSERT INTO articles_image VALUES (%i, 0x%s, %s)" % (id, imgdata, dbtoolkit.quotesql(format))                                                                                         
    db.doQuery(SQL)      


def encodeAndLimitLength(variables, lengths):
    originals = map(lambda x: x and x.strip(), variables)
    numchars = 5
    while True:
        variables, enc = dbtoolkit.encodeTexts(variables)
        done = True
        for i, (var, maxlen, original) in enumerate(zip(variables, lengths, originals)):
            if var and (len(var) > maxlen):
                done = False
                variables[i] = original[:maxlen-numchars] + " ..."
        if done: return variables, enc
        numchars += 5
