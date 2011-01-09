"""
Helper methods to interpret/parse LexisNexis textual data
"""

import re
from amcat.tools import toolkit, scraper

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

RE_EXTRACTMETAS = [
    re.compile(r'(.*)^\s*BODY:\s*$(.*)^\s*([A-Z\-]+:.*)', re.M | re.S |re.U),
    re.compile(r'(.*)^\s*(?:BODY|VOLLEDIGE TEKST):\s*$(.*)()', re.M | re.S |re.U),
#    re.compile(r'(.*)^\s*GRAPHIC: (.*)()', re.M | re.S |re.U),
#    re.compile(r'(.*)^\s*(?:LENGTH:|L\xc4NGE:) \d+ +(?:woorden|W\xf6rter|words|palabras)$(.*)()', re.M | re.S |re.U),
#    re.compile(r'(.*^\s*(?:HIGHLIGHT|L\xc4NGE|LONGUEUR):.*?$)(.*)()', re.M | re.S |re.U),
#    re.compile(r'(.*^\s*[A-Z\-]+:.*?)$(.*)^\s*([A-Z\-]+:.*)', re.M | re.S |re.U),
    ]

RE_ENDBODY = re.compile(r'(.*)^\s*(LOAD-DATE: .*)', re.M | re.S | re.U)

RE_SPLITMETA    = re.compile(r'^([A?-Z-%s]+):'%umlauts, re.M |re.U)
RE_GETMETA    = re.compile(r'^([A-Z-]+):(.*)$' , re.M |re.U)
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

def parseArticle(articleString, sources):
    """Parse a LN article and return an articledescriptor
    @return: L{amcat.tools.scraper.ArticleDescriptor}
    """
    # Parse string, extract metadata, interpret prolog

    (prolog, body, meta) = parseLexisNexis(articleString)
    (date1, medium, possibleheadline) = interpretProlog(prolog, sources, meta)

    if (medium == 8):
        #print "Doing AD split for %s" % meta.get ('headline', 'missing')[:40]
        body = splitad(body)

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

    try:
        if type(headline) == str:
            headline = unicode(headline, 'latin-1')
        if type(byline) == str:
            byline = unicode(byline, 'latin-1')
        if type(body) == str:
            body = unicode(body, 'latin-1')
    except Exception, e:
        raise Exception('unicode problem %s %s %s: %s' % (headline, meta, byline, e))
    
    #print headline, section
    return scraper.ArticleDescriptor(body, headline, date1, byline, pagenr, section=section, mediumid=medium, fullmeta = meta)

def parseLexisNexis(text):
    """
    Breaks up a Lexis Nexis article into a tuple of (prolog, body, meta)
    Assumes input of the form >>prolog<< (KEY: Value)* BODY: >>body<< (KEY:Value)*
    meta will be a dictionary containing the KEY: Value pairs (excluding BODY:)
    """
    for pattern in RE_EXTRACTMETAS:
        
        match = re.match(pattern, text)
        if match: break

    if match:
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
    else:
        # parse 'section' by section, split off newlines
        # this can possibly be used for all articles, but keep
        # as fallback for now (the old method "ain't broke")

        sections = re.split(r"\n\s*\n", text)
        prolog = []
        meta = {}
        body = []
        bodydone = False
        for section in sections:
            m = RE_GETMETA.match(toolkit.stripAccents(section))
            if m:
                if body: bodydone = True # no more body after first meta after body
                key, val = m.groups()
                meta[key.lower()] = toolkit.clean(val)
            elif not meta: # 'body' before meta is prolog
                prolog.append(section)
            elif not bodydone:
                body.append(section)
        prolog = "\n\n".join(prolog)
        body = "\n\n".join(body)


    if not body.strip(): raise Exception("Cannot parse body from %r" % text)
    if not body.strip(): raise Exception("Cannot parse prolog from %r" % text)
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
    for dateline in reversed(lines):
        raw = dateline
        dateline = dateline.strip()
        if date:
            mostlikelysource=dateline # line before date is most likely source
            break
        date = toolkit.readDate(dateline, lax=1, rejectPre1970=True)
                
        if len(dateline) > 5 and raw[0] <> ' ' and not date:
            possibleheadline = dateline # line after date is possible headline

    source = mostlikelysource
    medium = sources.lookupName(source)
    for line in reversed(lines):
        if medium: break
        source = line
        if source.strip().startswith('USA TODAY'): source = 'USA TODAY'
        if 'Gannett Company' in source: source = 'USA TODAY'
        if source.strip().endswith('The Washington Post'): source = 'The Washington Post' 
        medium = sources.lookupName(source)

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
