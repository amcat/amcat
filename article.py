import toolkit, lexisnexis, dbtoolkit, re, sbd, ctokenizer, mx.DateTime, sources
_debug = toolkit.Debug('article',1)
_xmltemplatefile = '/home/anoko/resources/files/article_template.xml'

class Article:
    """
    Class representing a newspaper article
    """
    xmltemplate = None

    def __init__(self, db, id, batchid, medium, date, headline, length, pagenr, encoding = None):
        self.db         = db
        self.id         = id
        self.batchid    = batchid
        self.medium     = medium
        self.date       = date
        self.headline   = headline
        self.length     = length
        self.pagenr     = pagenr

        self.encoding = encoding
        if encoding: self.headline = dbtoolkit.decode(self.headline, encoding)
        elif headline: self.headline = self.headline.decode('latin-1')
        
        self._meta      = None # stores byline, section, fullmeta

    def __getattr__(self, name):
        if name in ("byline", "section", "fullmeta"):
            if not self._meta: self._getMeta()
            return self._meta[name]
        if name == "text":
            return self.getText()
        raise AttributeError(name)

    def _getMeta(self):
        b,s,m = self.db.doQuery("select byline, section, metastring from articles where articleid=%i" % self.id)[0]
        b = dbtoolkit.decode(b, self.encoding)
        m = dbtoolkit.decode(m, self.encoding)
        s = dbtoolkit.decode(s, self.encoding)
        self.setMeta(b,s,m)

    def setMeta(self, byline, section, fullmeta):
        if toolkit.isString(fullmeta):
            fullmeta = toolkit.dictFromStr(fullmeta, unicode=True)
        self._meta = {"byline": byline, "section": section, "fullmeta" : fullmeta}

    def getText(self, type=2):
        if not self.id: return ''
        return self.db.getText(self.id, type)
    
    def toText(self):
        return self.fulltext()

    def toHTML(self, limitpars = None, includeMeta = False):
        res = u"<h1>%s</h1>" % self.headline
        if self.byline:
            res += "\n<h2>%s</h2>" % self.byline
        if includeMeta:
            source = self.db.sources.lookupID(self.medium)
            res += '''<table class="meta">
            <tr><td>Source:</td><td>&nbsp;&nbsp;&nbsp;&nbsp;</td><td>%s</td></tr>
            <tr><td>Date:</td><td></td><td>%s</td></tr>
            <tr><td>Articleid:</td><td></td><td>%s</td></tr>
            <tr><td>Page:</td><td></td><td>%s</td></tr>
            <tr><td>Section:</td><td></td><td>%s</td></tr>
            </table>''' % (source, toolkit.writeDate(self.date), self.id, self.pagenr, self.section)
        if self.text: 
            if limitpars:
                res += "<p>%s</p>" % "</p><p>".join(self.text.split("\n\n")[:limitpars])
            else:
                res += "<p>%s</p>" % "</p><p>".join(self.text.split("\n\n"))
        return res

    def toXML2(self):
        if not self.xmltemplate:
            self.xmltemplate = open(_xmltemplatefile).read()

        text = toolkit.clean(self.headline, level=1)
        for par in sbd.splitPars(self.text, type=self.type, returnSents=False):
            text += "\n\n%s" % toolkit.clean(par, level=1)
        src = self.db.sources.lookupID(self.medium)
        dct = self.__dict__
        dct.update({'source':src.prettyname,'lang':src.language.strip(),'date':toolkit.writeDate(self.date),'text':text})
        return self.xmltemplate % dct

    def toXML(self):
        # gebruik sentences als die er zijn??
        if not self.xmltemplate:
            self.xmltemplate = open(_xmltemplatefile).read()
        src = self.db.sources.lookupID(self.medium)
        text = '''
        <p n="0" function="headline">
           <s id="0">%(headline)s</s>
        </p>''' % self.headline
        np=2; ns = 1;
        if self.byline:
            text += '\n  <p n="1" function="byline">\n   <s id="%s">%s</s>\n  </p>' % (ns, self.byline)
            ns+=1
        content=self.text.replace("q11 \n","\n\n")
        if len(content.strip().split("\n")[0])>100: content = content.replace("\n","\n\n")
        content = re.sub(r"(.{,50}\.)\n",r"\1\n\n",content)
        
        for par in sbd.splitPars(content):
            if not par:continue
            text += '\n  <p n="%s" function="body">' % np
            for line in par:
                if not line:continue
                line=line.replace("-\n","")
                text += '\n   <s id="%s">%s</s>' % (ns, toolkit.clean(line, level=1, droptags=1, escapehtml=1))
                ns += 1
            text += '\n  </p>'
            np += 1
            
        dct = self.__dict__
        dct.update({'source':src.prettyname,'lang':src.language.strip(),'date':toolkit.writeDate(self.date),'text':text})
        
        
        xml = self.xmltemplate % dct
        return '<?xml-stylesheet type="text/xsl" href="http://www.cs.vu.nl/~wva/anoko/article.xsl"?>\n%s'% xml
        

    def getPagenr(article):
        """
        Returns the pagenr of the article. If None, invokes parseSection
        on the section and returns the pagenr (if found)
        """
        if self.pagenr:
            return self.pagenr
        elif self.section:
            p = lexisnexis.parseSection(self.section)
            if p:
                self.pagenr = p[1]
                return self.pagenr
            else:
                _debug('Could not parse section "%s" (aid=%s)'  % (self.section, self.id))
                return None
        else:
            _debug(2,'No pagenr or section known for article %s' % self.id)
            return None

    def source(self):
        """
        Looks up the medium (source id) and returns the name
        """
        if self.medium:
            return self.db.sources.lookupID(self.medium).name

    def __str__(self):
        return ('<article id="%(id)s" date="%(date)s" source="%(medium)s" length="%(length)s">' +
                '\n  <headline>%(headline)s</headline>\n</article>') % self.__dict__

    def fulltext(self):
        if self.type == 4:
            result = self.text # (parsed headline is included in text)
            if self.text:
                result = result.replace("\\r/N(soort,ev,neut)/\\r","")
            else:
                #toolkit.warn("No text for article %s?" % self.id)
                return None
        else:
            result = (self.headline or '') +"\n\n"+ (self.byline or "")+"\n\n"+(self.text or "")
        return result.replace("\\r","").replace("\r","\n")

    def sentences(self, split = False, onlyWords = False):
        text = self.text
        if self.type == 4:
            text = re.sub("\s+", " ", text)
            sents = re.split(r"(?<!./N\(eigen,ev,neut\)/.) [\.?!]/Punc\([^)]*\)/[\.?!] ",text)
        else:
            text = ctokenizer.tokenize(text)
            text = re.sub("\s+", " ", text)
            sents = text.split(" . ")
        for sentence in sents:
            if sentence.strip():
                if split:
                    yield(words(sentence, onlyWords))
                else:
                    yield(sentence)

    def words(self, onlyWords = False, lemma=0): #lemma: 1=lemmaP, 2=lemma, 3=word
        text = self.text
        if not text: return []
        text = toolkit.stripAccents(text)
        text = text.encode('ascii', 'replace')
        text = ctokenizer.tokenize(text)
        #toolkit.warn("Yielding words for %i : %s" % (self.id, text and len(text) or `text`))
        text = re.sub("\s+", " ", text)
        return words(text, onlyWords, lemma)

    def uploadimage(self, *args, **kargs):
        self.db.uploadimage(self.id, *args, **kargs)

    def getImages(self):
        """
        returns the images belonging to self article (if any)
        """
        SQL = "SELECT ai.sentenceid, length, breadth, abovefold, imgType FROM articles_images ai inner join sentences s on ai.sentenceid=s.sentenceid WHERE articleid=%i" % self.id
        return [Image(self, getCapt=True, *data) for data in self.db.doQuery(SQL)]
        

def createArticle(db, headline, date, source, batchid, text, texttype=2,
                  length=None, byline=None, section=None, pagenr=None, fullmeta=None):
    """
    Writes the article object to the database
    """

    if toolkit.isDate(date): date = toolkit.writeDateTime(date, 1)
    if type(source) == sources.Source: source = source.id
    if type(fullmeta) == dict: fullmeta = `fullmeta`

    #print `headline`, `byline`, `fullmeta`
    [headline, byline, fullmeta, section], encoding = dbtoolkit.encodeTexts([headline, byline, fullmeta, section])
    #print `headline`, `byline`, `fullmeta`
    
    q = {'date' : date,
         'length' : length,
         'metastring' : fullmeta,
         'headline' : headline,
         'byline' : byline,
         'section' : section,
         'pagenr': pagenr,
         'batchid' : batchid,
         'mediumid' : source,
         'encoding' : encoding}
    #print `q`
    aid = db.insert('articles',q)

    text, encoding = dbtoolkit.encodeText(text)
    
    q = {'articleid' : aid,
         'type' : texttype,
         'encoding' : encoding,
         'text' : text}
    db.insert('texts',q)

    return fromDB(db, aid)



def words(text, onlyWords=False, lemma=0): #lemma: 1=lemmaP, 2=lemma,3 =word
    for w in text.split(" "):
        if not w: continue
        if lemma==1: w= toolkit.wplToWc(w)
        elif lemma==2: w= w.split("/")[-1]
        elif lemma==3: w= w.split("/")[0]
        if (not onlyWords) or w.isalpha():#re.search("\w", w):
            yield w

def fromXML2(str):
    import xml.dom.minidom
    articles = []
    doc = xml.dom.minidom.parseString(str)
    for art in doc.getElementsByTagName("article"):
        
        id       = int(toolkit.xmlElementText(art, "dc:identifier"))
        headline = toolkit.xmlElementText(art, "dc:title")
        print toolkit.xmlElementText(art, "publisherid")
        mediumid = int(toolkit.xmlElementText(art, "publisherid"))
        date     = toolkit.readDate(toolkit.xmlElementText(art, "dc:date"))
        text     = toolkit.xmlElementText(art, "content")
        
        a = Article(None, id, None, mediumid, date, headline, None, None, None, None, None,text, type=4)
        articles.append(a)

    return articles

def fromDB(db, id):
    return list(articlesFromDB(db,(id,)))[0]

def articlesFromDB(db, ids):
    """
    Article Factory method to create an article from the database
    """
    if not ids:
        return 
    if not db:
        db = dbtoolkit.anokoDB()

    data = None; text = None
    sql = """SELECT articleid, batchid, mediumid, date, headline, length, pagenr, encoding
             FROM articles WHERE articleid in (%s)""" % ",".join(str(id) for id in ids)
    for d in db.doQuery(sql):
        yield Article(db,*d)

CACHE_SIZE = 20
def Articles(aidlist, db, tick=False):
    """
    Generator that yields articles using caching to minimize db roundtrips
    """
    aidlist = list(aidlist)
    while aidlist:
        cache = articlesFromDB(db, aidlist[:CACHE_SIZE])
        for a in cache:
            yield a
        aidlist = aidlist[CACHE_SIZE:]

class Image:
    def __init__(self, article, sentid, length, breadth, abovefold, typ, caption=None, getCapt=False):
        self.article = article
        self.sentid = int(sentid)
        self.length = int(length)
        self.breadth = int(breadth)
        self.abovefold = bool(abovefold)
        self.typ = typ
        self.caption = caption
        if getCapt:
            self.caption = getCaption(self.article.db, sentid)

def getCaption(db, sentid):
    aid, parnr = db.doQuery("SELECT articleid, parnr FROM sentences WHERE sentenceid=%i"%sentid)[0]
    data = db.doQuery("SELECT sentence FROM sentences WHERE articleid=%i AND parnr=%i AND sentnr=2" % (aid, parnr))
    if data:
        return data[0][0]
    else:
        return None
                      

def fromXML2(str):
    import xml.dom.minidom
    articles = []
    str = str.replace("&","+")
    doc = xml.dom.minidom.parseString(str)
    for art in doc.getElementsByTagName("article"):
        
        id       = int(toolkit.xmlElementText(art, "dc:identifier"))
        headline = toolkit.xmlElementText(art, "dc:title")
        mediumid = int(toolkit.xmlElementText(art, "publisherid"))
        date     = None#toolkit.readDate(toolkit.xmlElementText(art, "dc:date"))
        text     = toolkit.xmlElementText(art, "content")
        
        a = Article(None, id, None, mediumid, date, headline, None, None, None, None, None,text, type=4)
        articles.append(a)

    return articles


def splitArticles(aids, db, tv=False):
    from itertools import izip, count
    error = ''
    for article in Articles(aids, db, tick=True):
        if db.doQuery("SELECT TOP 1 articleid FROM sentences WHERE articleid = %s and parnr >= 0" % article.id):
            toolkit.warn("Article %s already split, skipping!" % article.id)
            continue
        text = article.text
        if not text:
            toolkit.warn("Article %s empty, adding headline only" % article.id)
            text = ""
        text = re.sub(r"q11\s*\n", "\n\n",text)
        #if article.byline: text = article.byline + "\n\n" + text
        if article.headline: text = article.headline.replace(";",".")+ "\n\n" + text
        spl = sbd.splitPars(text)
        for parnr, par in izip(count(1), spl):
            for sentnr, sent in izip(count(1), par):
                #return `{"articleid":article.id, "parnr" : parnr, "sentnr" : sentnr, "sentence" : sent.strip()[:7000]}`
                sent = sent.strip()
                if len(sent) > 450:
                    longsent = sent
                    sent = sent[:450] + '[...]'
                else:
                    longsent = None
                [sent, longsent], encoding = dbtoolkit.encodeTexts([sent, longsent])
                try:
                    db.insert("sentences", {"articleid":article.id, "parnr" : parnr, "sentnr" : sentnr, "sentence" : sent, 'longsentence': longsent, 'encoding': encoding})
                except Exception, e:
                    error += '%s: %s\n' % (article.id , e)
    return error
    
    

if __name__ == '__main__':
    import sys, dbtoolkit, toolkit
    aids = toolkit.intlist(sys.stdin)
    db = dbtoolkit.anokoDB()
    splitArticles(aids, db)
    db.conn.commit()
    
