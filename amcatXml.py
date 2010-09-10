import toolkit,dbtoolkit,article, traceback, sys
import xml.sax

class ArticleWriter:
    def __init__(self, db, batchid):
        self.db = db
        self.batchid = batchid
        self.articleCount = 0

    def writeArticle(self, batchid, text, meta):
        if not text.strip() and not meta.get('headline', '').strip():
            raise Exception('Missing text and headline')
        
        #toolkit.ticker.tick(interval=1000)
        #toolkit.warn('Attempting to write article %s' % meta.get('headline', '?'))
        if 'date' in meta:
            date = toolkit.readDate(meta['date'])
        else:
            raise Exception('Missing date')

        mediumid = meta.get('mediumid',None)
        if not mediumid:
            raise Exception('Missing mediumid')
        headline = meta.get('headline')
        byline = meta.get('byline', None)
        section = meta.get('section',None)
        pagenr = meta.get('pagenr',None)
        url = meta.get('url',None)
        id = meta.get('id',None)
        length = len(text.split())
        for key in meta.keys():
            if key in ('headline', 'byline', 'section', 'pagenr', 'mediumid', 'date', 'url', 'id'):
                del meta[key]
        meta = `meta`
        try:
            if type(headline) == str:
                headline = unicode(headline.strip(), 'latin-1')
            if type(meta) == str:
                meta = unicode(meta, 'latin-1')
            if type(byline) == str:
                byline = unicode(byline.strip(), 'latin-1')
            if type(text) == str:
                text = unicode(text.strip(), 'latin-1')
        except Exception, e:
            raise Exception('unicode problem %s %s %s: %s' % (headline, meta, byline, e))
        
        article.createArticle(self.db, headline, date, mediumid, batchid, text, texttype=2,
                      length=length, byline=byline, section=section, pagenr=pagenr, fullmeta=meta, 
                      url=url, externalid=id, retrieveArticle=0)
        self.articleCount += 1


    def doArticle(self,text, meta):
        self.writeArticle(self.batchid, text, meta)



class XMLArticleHandler(xml.sax.ContentHandler):

    def __init__(self, articleHandler):
        self.meta = {}
        self.persistentMeta = {}
        self.handler = articleHandler
        self.activeMeta = None
        self.text = ""
        self.errors = u''
        self.errorCount = 0

    def newArticle(self):
        self.meta = self.persistentMeta.copy()
        self.text = ""
        self.activeMeta = None

    def writeArticle(self):
        self.handler.doArticle(self.text, self.meta)

    def startElement(self, name, attrs):
        if name=='article':
            self.newArticle()
        elif name=='articles':
            self.persistentMeta.update(attrs)
        else:
            self.meta[name] = ""
            self.activeMeta = name

    def endElement(self, name):
        #toolkit.warn("Ending %s" % name)
        if name=='article':
            try:
                self.writeArticle()
            except Exception, e:
                trace = ''.join(traceback.format_exception(*sys.exc_info()))
                toolkit.warn('Exception near article %s\n%s' % (self.meta.get('headline', '?'), trace))
                self.errors += '\n%s\n' % trace
                self.errorCount += 1
        else:
            self.activeMeta = None

    def characters(self, text):
        if self.activeMeta:
            self.meta[self.activeMeta] += text
        else:
            self.text += text


def readfiles(db, projectid, batchname, files):
    batchid = db.newBatch(projectid, batchname, 'N/A (imported from XML)')
    toolkit.warn("Created batch with id %d" % batchid)        

    articleCount = 0
    errors = u''
    errorCount = 0
    for file in files:
        try:
            articleHandler = ArticleWriter(db, batchid)
            xmlHandler = XMLArticleHandler(articleHandler)
            toolkit.warn("Reading file %s..."% file)
            xml.sax.parse(file, xmlHandler)
            articleCount += articleHandler.articleCount
            errors += '\n%s\n' % xmlHandler.errors
            errorCount += xmlHandler.errorCount
        except Exception, e:
            print e
            errors += '\n%s\n' % e
            errorCount += 1
            continue
    #errors += '\nTotal Error Count: %s articles' % errorCount
    if articleCount > 0:
        db.conn.commit()
    else:
        db.conn.rollback() # werkt dit?
    return articleCount, batchid, errors, errorCount
