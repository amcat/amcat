import toolkit, lexisnexis, dbtoolkit, re, sbd, ctokenizer
_debug = toolkit.Debug('article',1)
_xmltemplatefile = '/home/anoko/resources/files/article_template.xml'

class Article:
    """
    Class representing a newspaper article
    """
    xmltemplate = None

    def __init__(this, db, id, batchid, medium, date, headline, byline,length, pagenr, section, fullmeta,text,type=2):
        this.db         = db
        this.id         = id
        this.batchid    = batchid
        this.medium     = medium
        this.date       = date
        this.headline   = headline
        this.byline     = byline
        this.length     = length
        this.section    = section
        this.pagenr     = pagenr
        this.fullmeta   = fullmeta
        this.text       = text
        this.type       = type
        
        if toolkit.isString(this.fullmeta):
            this.fullmeta = toolkit.dictFromStr(this.fullmeta)

    def toText(this):
        return this.fulltext()

    def toHTML(this, limitpars = None, includeMeta = False):
        res = "<h1>%s</h1>" % this.headline
        if this.byline:
            res += "\n<h2>%s</h2>" % this.byline
        if includeMeta:
            source = this.db.sources.lookupID(this.medium)
            res += '''<table class="meta">
            <tr><td>Source:</td><td>&nbsp;&nbsp;&nbsp;&nbsp;</td><td>%s</td></tr>
            <tr><td>Date:</td><td></td><td>%s</td></tr>
            <tr><td>Page:</td><td></td><td>%s</td></tr>
            <tr><td>Section:</td><td></td><td>%s</td></tr>
            </table>''' % (source, toolkit.writeDate(this.date), this.pagenr, this.section)
        if this.text: 
            if limitpars:
                res += "<p>%s</p>" % "</p><p>".join(this.text.split("\n\n")[:limitpars])
            else:
                res += "<p>%s</p>" % "</p><p>".join(this.text.split("\n\n"))
        return res

    def toXML2(this):
        if not this.xmltemplate:
            this.xmltemplate = open(_xmltemplatefile).read()

        text = toolkit.clean(this.headline, level=1)
        for par in sbd.splitPars(this.text, type=this.type, returnSents=False):
            text += "\n\n%s" % toolkit.clean(par, level=1)
        src = this.db.sources.lookupID(this.medium)
        dct = this.__dict__
        dct.update({'source':src.prettyname,'lang':src.language.strip(),'date':toolkit.writeDate(this.date),'text':text})
        return this.xmltemplate % dct

    def toXML(this):
        # gebruik sentences als die er zijn??
        if not this.xmltemplate:
            this.xmltemplate = open(_xmltemplatefile).read()
        src = this.db.sources.lookupID(this.medium)
        text = '''
        <p n="0" function="headline">
           <s id="0">%(headline)s</s>
        </p>''' % this.headline
        np=2; ns = 1;
        if this.byline:
            text += '\n  <p n="1" function="byline">\n   <s id="%s">%s</s>\n  </p>' % (ns, this.byline)
            ns+=1
        content=this.text.replace("q11 \n","\n\n")
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
            
        dct = this.__dict__
        dct.update({'source':src.prettyname,'lang':src.language.strip(),'date':toolkit.writeDate(this.date),'text':text})
        
        
        xml = this.xmltemplate % dct
        return '<?xml-stylesheet type="text/xsl" href="http://www.cs.vu.nl/~wva/anoko/article.xsl"?>\n%s'% xml
        

    def getPagenr(article):
        """
        Returns the pagenr of the article. If None, invokes parseSection
        on the section and returns the pagenr (if found)
        """
        if this.pagenr:
            return this.pagenr
        elif this.section:
            p = lexisnexis.parseSection(this.section)
            if p:
                this.pagenr = p[1]
                return this.pagenr
            else:
                _debug('Could not parse section "%s" (aid=%s)'  % (this.section, this.id))
                return None
        else:
            _debug(2,'No pagenr or section known for article %s' % this.id)
            return None

    def source(this):
        """
        Looks up the medium (source id) and returns the name
        """
        if this.medium:
            return this.db.sources.lookupID(this.medium).name

    def toDatabase(this):
        """
        Writes the article object to the database
        """

        if this.id:
            raise Exception("Article is from database (id %s), refusing to duplicate!" % this.id)
        
        q = {'date' : toolkit.writeDateTime(this.date, 1),
             'length' : this.length,
             'metastring' : `this.fullmeta`,
             'headline' : this.headline,
             'byline' : this.byline,
             'section' : this.section and this.section[:100],
             'pagenr': this.pagenr,
             'batchid' : this.batchid,
             'mediumid' : this.medium}
        aid = this.db.insert('articles',q)
         
        q = {'articleid' : aid,
             'type' : 2,
             'text' : this.text}
        this.db.insert('texts',q)

        this.id = aid
        return aid

    def __str__(this):
        return ('<article id="%(id)s" date="%(date)s" source="%(medium)s" section="%(section)s" length="%(length)s">' +
                '\n  <headline>%(headline)s</headline>\n</article>') % this.__dict__

    def fulltext(this):
        if this.type == 4:
            result = this.text # (parsed headline is included in text)
            if this.text:
                result = result.replace("\\r/N(soort,ev,neut)/\\r","")
            else:
                #toolkit.warn("No text for article %s?" % this.id)
                return None
        else:
            result = (this.headline or '') +"\n\n"+ (this.byline or "")+"\n\n"+(this.text or "")
        return result.replace("\\r","").replace("\r","\n")

    def sentences(this, split = False, onlyWords = False):
        text = this.text
        if this.type == 4:
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

    def words(this, onlyWords = False, lemma=0): #lemma: 1=lemmaP, 2=lemma, 3=word
        text = this.text
        if not text: return []
        if this.type <> 4:
            text = ctokenizer.tokenize(text)
        #toolkit.warn("Yielding words for %i : %s" % (this.id, text and len(text) or `text`))
        text = re.sub("\s+", " ", text)
        return words(text, onlyWords, lemma)

    def uploadimage(this, *args, **kargs):
        db.uploadImage(this.id, *args, **kargs)

    def getImages(this):
        """
        returns the images belonging to this article (if any)
        """
        SQL = "SELECT ai.sentenceid, length, breadth, abovefold, imgType FROM articles_images ai inner join sentences s on ai.sentenceid=s.sentenceid WHERE articleid=%i" % this.id
        return [Image(this, getCapt=True, *data) for data in this.db.doQuery(SQL)]
        



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

def fromDB2(id, db=None, type=2):
    return fromDB(db, id, type)


def fromDB(db, id, type=2):
    """
    Article Factory method to create an article from the database
    """

    if not db:
        db = dbtoolkit.anokoDB()

    data = None; text = None
    try:
        d = db.doQuery("SELECT articleid, batchid, mediumid, date, headline, byline, length, pagenr, section, metastring "+
                     " FROM articles WHERE articleid=%s" % id)
        try:
            text = db.doQuery("SELECT text FROM texts WHERE articleid=%s AND type=%s" % (id, type))
            if text: text = text[0][0]
            else: text = None
        except Exception, e:
            # Problem getting text, might be too large for python_sybase, try java
            #print "java!"
            text = javatext(id, type)
        data = list(d[0]) + [text]
        return Article(db,*data, **{'type':type}) 
    except Exception, e:
        _debug(1,"Error on reading article %s"% id)
        toolkit.warn(e)
        return None



def javatext(id, type):
    import os
    CMD = 'java -cp .:/home/anoko/libjava/msbase.jar:/home/anoko/libjava/mssqlserver.jar:/home/anoko/libjava/msutil.jar:/home/anoko/libjava AnokoDB "select text from texts where articleid=%s and type=%s"' % (id, type)
    #print CMD
    i,o = os.popen2(CMD)
    i.close()
    return o.read()
                    

class Articles:
    """
    Iterator class containing a list of article id's
    Will return the (text of) an article on each iteration
    The aidlist must be an iterable sequence of objects that
      can be converted to integers using int(object), such as
      a file containing article ids
    If the aidlist is an exhaustive iterator (such as a file)
      and it needs to be iterator over more than once, use
      cache_aidlist
    """
    
    def __init__(this, aidlist, db, cache_aidlist=0, textonly=False, type=2, tick=False):
        this.aidlist = aidlist
        this.db = db
        this.textonly = textonly
        this.type=type
        this.tick = tick
        
        if tick or cache_aidlist:
            this.aidlist = list(this.aidlist)
        if tick:   
            this.ticker = toolkit.Ticker()
            this.ticker.warn("Iterating over articles", estimate=len(this.aidlist))
            #this.ticker.interval=10
        
    def __iter__(this):
        this.reset() # creates this.iterator
        return this
    
    def next(this):
        if this.tick:
            this.ticker.tick()
        token = this.iterator.next()
        if toolkit.isString(token): token=token.strip()
        if not token: return this.next()
        article = this.db.article(int(token), type=this.type)
        if not article:
            _debug(2, "Could not find article %s" % token)
            return this.next()
        elif this.textonly:
            return article.fulltext()
        else:
            return article

    def reset(this):
        this.iterator = iter(this.aidlist)

class Image:
    def __init__(this, article, sentid, length, breadth, abovefold, typ, caption=None, getCapt=False):
        this.article = article
        this.sentid = int(sentid)
        this.length = int(length)
        this.breadth = int(breadth)
        this.abovefold = bool(abovefold)
        this.typ = typ
        this.caption = caption
        if getCapt:
            this.caption = getCaption(this.article.db, sentid)

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
                try:
                    db.insert("sentences", {"articleid":article.id, "parnr" : parnr, "sentnr" : sentnr, "sentence" : sent, 'longsentence': longsent})
                except Exception, e:
                    error += '%s: %s\n' % (article.id , e)
    return error
    
    

if __name__ == '__main__':
    import sys, dbtoolkit
    sys.argv += [35407547, 2]
    a = fromDB(dbtoolkit.anokoDB(), sys.argv[1], sys.argv[2])
    print a.text
