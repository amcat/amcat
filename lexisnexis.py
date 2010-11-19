"""
Helper methods to interpret/parse LexisNexis textual data
"""

import re,toolkit
import articlecreator

# Regular expressions on text file level:
RE_ARTICLESPLIT = re.compile(r'^\s+(?:FOCUS - )?\d+ of \d+ DOCUMENTS?\s*$', re.M)
RE_TITLEPAGE    = re.compile(r'^\s*Print Request:\s+(Selected|Select|All) (Items|Document\(?s\)?):.*$',re.M)
RE_TITLEPAGE2   = re.compile(r'^\s*Printopdracht: (Alle|Selecteer|Aangevinkte) documenten: [\d, -]+\s*$', re.M)
RE_TITLEPAGE3  = re.compile(r'^Zoektermen: .*$')
#RE_QUERY        = re.compile(r'^\s*Research Information:(.*)date[\s\n]*\(geq[\s\n]*\(\d+[/-]\d+[-/]\d+\)[\s\n]+and[\s\n]+leq[\s\n]*\(\d+[/-]\d+[/-]\d+\)+[\s\n]*^\s*$',re.M|re.DOTALL|re.IGNORECASE)
RE_QUERY        = re.compile(r'^\s*(?:Research Information|Terms|Zoektermen):(.*)date[\s\n]*\(?(geq|is|=)[\s\n]*\(?\d+\\?[/-]\d+\\?[-/]\d+\)?([\s\n]+and[\s\n]+leq[\s\n]*\(\d+[/-]\d+[/-]\d+\)+)?\)*[\s\n]*(AND[\s\n]+pub\(|^\s*$)',re.M|re.DOTALL|re.IGNORECASE)
RE_QUERY2        = re.compile(r'^Zoektermen:(.*?)( AND pub.*)?$',re.M|re.IGNORECASE)
RE_QUERY3        = re.compile(r'^Terms: (.*)\s*$', re.M|re.IGNORECASE)
# On Article string level
umlauts = '\xfc\xe4\xdc\xc4\xf6\xd6'

RE_EXTRACTMETA  = re.compile(r'(.*)^\s*BODY:\s*$(.*)^\s*([A-Z\-]+:.*)', re.M | re.S |re.U)
RE_EXTRACTMETA2  = re.compile(r'(.*)^\s*(?:BODY|VOLLEDIGE TEKST):\s*$(.*)()', re.M | re.S |re.U)
RE_EXTRACTMETA3  = re.compile(r'(.*)^\s*GRAPHIC: (.*)()', re.M | re.S |re.U)
RE_EXTRACTMETA3  = re.compile(r'(.*)^\s*LENGTH: \d+ +(?:woorden|words|palabras)$(.*)()', re.M | re.S |re.U)
RE_EXTRACTMETA4 = re.compile(r'(.*^\s*[A-Z\-]+:.*?)$(.*)^\s*([A-Z\-]+:.*)', re.M | re.S |re.U)

RE_ENDBODY = re.compile(r'(.*)^\s*(LOAD-DATE: .*)', re.M | re.S | re.U)

RE_SPLITMETA    = re.compile(r'^([A?-Z-%s]+):'%umlauts, re.M |re.U)
RE_LENGTH       = re.compile(r'(\d+) (?:words|woorden)', re.U)
RE_HEADLINEINBODY = re.compile(r'([\w .,:;\'"%s]{5,200})\n\n(.*)' % umlauts, re.M | re.U | re.S)

def extractQuery(str):
    """Extracts the 'query' part from the LN header"""
    m = RE_QUERY.search(str)
    if not m: m = RE_QUERY2.search(str)
    if not m: m = RE_QUERY3.search(str)
    if not m:
        toolkit.warn("Could not extract query from:\n%s" % str[:200])
        return None

    q = m.group(1)
    q = re.sub("\s+"," ", q)
    q = re.sub("([()])\s+([()])","\\1\\2", q)
    q = q.strip()
    return q

def istitlepage(str):
    """Checks whether the given LN string appears to be the title page"""
    return bool(RE_TITLEPAGE.search(str)) or bool(RE_TITLEPAGE2.search(str)) or bool(RE_TITLEPAGE3.search(str))

def split(str):
    """Splits a LN file into seperate article chunks"""
    return re.split(RE_ARTICLESPLIT, str)

multilang = {'section':['section','rubrique'], 'headline':['\xdcberschrift','titre'],'length':['longeur']}

def parseSection(section):
    """Splits a LexisNexis section into a section and pagenr"""
    if not section: return None
    m = re.match(r'(.*?)(?:pg\.?\s*|blz\.?\s*)(\d+)(.*)', section, re.IGNORECASE)
    #print `section`
    #print ">>>>>>>>>>", m and m.groups()
    #print "<<<<<<<<<<", m and int(m.group(2))
    if not m:
        m = re.match(r'(.*?)(\d+)(.*)', section, re.IGNORECASE)
    if m:
        return (m.group(1) + m.group(3)).strip(), int(m.group(2))
    return None

def parseArticle(articleString, db, batchid, commit):
    """
    Creates a new Article by parsing a Lexis Nexis plain text format article string
    """
    # Parse string, extract metadata, interpret prolog

    #print `articleString`
    #print "******************"
    
    (prolog, body, meta) = parseLexisNexis(articleString)
    (date1, medium, possibleheadline) = interpretProlog(prolog, db.sources, meta)


    #print `prolog`, '\n', `body`, '\n', `meta`

    if (medium == 8):
        #print "Doing AD split for %s" % meta.get ('headline', 'missing')[:40]
        body = splitad(body)
        #print body

    # interpret section
    for orig, trans in multilang.items():
        if orig not in meta:
            for tran in trans:
                if tran in meta: meta[orig] = meta[tran]
                
    sectionpage = parseSection(meta.get('section', None))
    if sectionpage is not None:
        meta['section'] = sectionpage[0]
        meta['pagenr'] = sectionpage[1]
    if 'text' in meta:
        del(meta['text'])

    # interpret length
    length = None
    if 'length' in meta:
        m = re.match(RE_LENGTH, meta['length'])
        if m:
            length = int(m.group(1))
    if not length: length = len(body.split())

    # extract crucial meta info
    headline = meta.get ('headline', 'missing')[:740]
    byline = meta.get('byline', None)
    section = meta.get('section', None)
    pagenr = meta.get('pagenr', None)

    if headline == 'missing' and possibleheadline:
        headline = possibleheadline[:740]
    if headline == 'missing':
        m = RE_HEADLINEINBODY.match(body.strip())
        if m:
            #print "XXXX"
            headline = m.group(1)
            body = m.group(2)

    #print "hl:",headline, "\nbody:", len(body), "\n", `body[:100]`, "\n>>>>>>>>>>"

    meta = `meta`
    try:
        if type(headline) == str:
            headline = unicode(headline, 'latin-1')
        if type(meta) == str:
            meta = unicode(meta, 'latin-1')
        if type(byline) == str:
            byline = unicode(byline, 'latin-1')
        if type(body) == str:
            body = unicode(body, 'latin-1')
    except Exception, e:
        raise Exception('unicode problem %s %s %s: %s' % (headline, meta, byline, e))
    
    #print headline, section
    if commit:
        articlecreator.createArticle(db, headline, date1, medium, batchid, body, texttype=2,
                                     length=length, byline=byline, section=section, pagenr=pagenr, fullmeta=meta, retrieveArticle=0)
    #article.Article(db, None, batchid, medium, date1, headline, byline, length, pagenr, section, meta, body)

def parseLexisNexis(text):
    """
    Breaks up a Lexis Nexis article into a tuple of (prolog, body, meta)
    Assumes input of the form >>prolog<< (KEY: Value)* BODY: >>body<< (KEY:Value)*
    meta will be a dictionary containing the KEY: Value pairs (excluding BODY:)
    """
    match = re.match(RE_EXTRACTMETA, text)
    if not match: match = re.match(RE_EXTRACTMETA2, text)
    if not match: match = re.match(RE_EXTRACTMETA3, text)
    if not match: match = re.match(RE_EXTRACTMETA4, text)
    if not match: print "<text exception='lexisnexis.py:143 could not parse article'>\n%s\n</text>" % text.encode('ascii','replace'); raise Exception("Could not parse article")

    body = match.group(2).strip()
    meta = match.group(1) + match.group(3)

    match = re.match(RE_ENDBODY, body)
    if match:
        body = match.group(1)
        meta += "\n\n"+match.group(2)

    fields = re.split(RE_SPLITMETA, meta)
    # fields contains [prolog, key0, val0, key1, val1,...]

    prolog = fields[0]
    fields = toolkit.pairs(fields[1:], 1)
    # fields now containt [(key0, val0),(key1, val1)...]

    meta = {}
    for key, val in fields:
        meta[key.lower()] = toolkit.clean(val)
    
    return (prolog, body, meta)

def interpretProlog(text, sources, meta):
    """
    Interprets a Lexis Nexis article prolog and extracts date and source
    """
    # first line contains copyright message, possibly source
    # last line contains date
    # last non-empty line before last contains source again

    lines = [l for l in text.split('\n') if l.strip()]
    medium = None
    date = None
    mostlikelysource = None
    possibleheadline = None
    for dateline in toolkit.reverse(lines):
        raw = dateline
        dateline = dateline.strip()
        if date:
            mostlikelysource=dateline # line before date is most likely source
            break
        date = toolkit.readDate(dateline, lax=1, rejectPre1970=True)
        if len(dateline) > 5 and raw[0] <> ' ' and not date:
            possibleheadline = dateline # line after date is possible headline

    source = mostlikelysource
    medium = sources.lookupName(source, 1)
    for line in toolkit.reverse(lines):
        if medium: break
        source = line
        if source.strip().startswith('USA TODAY'): source = 'USA TODAY'
        if 'Gannett Company' in source: source = 'USA TODAY'
        if source.strip().endswith('The Washington Post'): source = 'The Washington Post' 
        medium = sources.lookupName(source, 1)

    if not medium:
        if 'Newstex Web Blogs' in meta.get('publication-type'):
            medium = sources.lookupName('Newstex Web Blogs')

    if not medium:
        if mostlikelysource is None:
            raise Exception("Could not find source in %s\n\n%s" % (text, meta))
        print text.encode('ascii','replace')
        raise Exception('Could not find source "%s"' % mostlikelysource)
    if medium.id < 0:
        toolkit.warn('Source <0: %s : %s' % (source, medium))

    if not date:
        raise Exception('Could not find date/time, best bet: "%s" or "%s"' %(lines[-1], lines[-2]))
    
    return date, medium.id, possibleheadline


def splitad(text):
    # AD changed the lexisnexis format to only have \n\n after the lead, so insert
    # paragraph break after short lines
    pars = text.split("\n\n")

    #if len(pars[-1]) < 4: del(pars[-1])

    l = max(len(x) for x in pars)
    
    if len(pars) <= 4 and l > 500:
        #print "Really splitting"
        # this seems to be a 'wrong split', so split at incomplete lines
        res = []
        for txt in pars:
            if len(txt) > 500:
                txt = re.sub("\n(.{,50})\n(?!\n)", "\n\\1\n\n", txt)
                txt = re.sub("\n(.{,65}\.)\n(?!\n)", "\n\\1\n\n", txt)
            res.append(txt)
        text = "\n\n".join(res)
    #else:
    #    print "No",len(pars),l
    
    return text


def readfile(txt, db, batchid, commit):
    texts = split(txt)
    errors = u''
    errorCount = 0
    i = 0
    if istitlepage(texts[0]): del texts[0]
    for text in texts:
        if not text.strip(): continue
        try:
            parseArticle(text, db, batchid, commit)
            i += 1
        except Exception, e:
            print `text`
            #raise
            import traceback, sys
            tb = sys.exc_info()[2]
            errmsg = "%s at %s" % (e, " / ".join(traceback.format_tb(tb, 3)))
            errors += '\n%s\n' % errmsg
            errorCount += 1
    if commit:
        db.conn.commit()
    return i, errors, errorCount

def readfiles(db, projectid, batchname, files, verbose=False, commit=True, fixedquery=None):
    batches = []
    query, batchid = None, -1
    articleCount = 0
    errors = u''
    errorCount = 0
    for file in files:
        if verbose: print "Reading file.. %s" % file
        if type(file) in (str, unicode):
            txt = file
        else:
            txt = file.read().strip()
        if type(txt) == str:
            txt = txt.decode('windows-1252') # ik gok dat dat hun encoding is
            txt = txt.replace(u'\r\n', u'\n')
            txt = txt.replace(u'\xa0', u' ') # nbsp --> normal space
        
        #toolkit.stripAccents(file.read()).strip().replace('\r\n', '\n')
        if fixedquery:
            q = fixedquery
        else:
            q = extractQuery(txt)
        if not q: raise Exception('Could not extract lexisnexis query from file %s!' % file.name)
            # errors += 'Could not extract lexisnexis query from file %s!!\n'
            # errorCount += 1
            # continue
        if q <> query:
            query = q
            if verbose:
                print "Creating new batch..."
                print "Query:", `q`
            if commit:
                batchid = db.newBatch(projectid, batchname, query, verbose=1)
            batches.append(batchid)
        articleCountFile, errorsFile, fileErrorCount = readfile(txt, db, batchid, commit)
        articleCount += articleCountFile
        errors += errorsFile
        errorCount += fileErrorCount

    return articleCount, batches, errors, errorCount

    
if __name__ == '__main__':
    import dbtoolkit, sys
    projectid = int(sys.argv[1])
    files = sys.argv[2:]
    db = dbtoolkit.amcatDB()
    batchname = files[0].split(".")[0].split("/")[-1]
    files = map(open, files)
    ac, batches, errors, ec = readfiles(db, projectid, batchname, files, verbose=False)
    print "%i articles "% ac
    print "errors:\n%s" % (errors,)
