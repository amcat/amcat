import toolkit, dbtoolkit, sources, binascii, article, types

def createArticle(db, headline, date, source, batchid, text, texttype=2,
                  length=None, byline=None, section=None, pagenr=None, fullmeta=None, url=None, externalid=None, parentUrl=None, retrieveArticle=1):
    """
    Writes the article object to the database
    """
    # TODO link to parent if parentUrl is not None

    if toolkit.isDate(date): date = toolkit.writeDateTime(date, 1)
    if type(source) == sources.Source: source = source.id
    if type(fullmeta) == dict: fullmeta = `fullmeta`

    if url and len(url) > 490: url = url[:490] + "..."

    (headline, byline, fullmeta, section), encoding = article.encodeAndLimitLength([headline, byline, fullmeta, section], [740, 999999, 999999, 90])
    
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
        SQL = "DELETE FROM articles_image WHERE articleid=%i" % (id,)
        db.doQuery(SQL)                                              
        imgdata = binascii.hexlify(imgdata)                               
        SQL = "INSERT INTO articles_image VALUES (%i, 0x%s, %s)" % (id, imgdata, dbtoolkit.quotesql(format))                                                                                         
        db.doQuery(SQL)      
