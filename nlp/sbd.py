import re,os, toolkit

abbrevs = ["ir","mr","dr","dhr","ing","drs","mrs","sen","sens","gov","st","jr","rev","vs","gen","adm","sr","lt","sept"]
months = "Jan Feb Mar Apr Jun Jul Aug Sep Oct Nov Dec".split()

expr = None

def split(text, type=2):
    """python gaat op zoek naar einde van een regel dmv zoeken naar een punt.
    echter hij sluit uit dat het gaat om eigennamen,
    waardoor bv A.den Doolaard niet als einde van een zin wordt gezien.
    type = 4 als gelemmatized anders 2 (default=2)
    terug een lijst van stringen"""
    if type==4:
        return re.split(r"(?<!./N\(eigen,ev,neut\)/.) [\.?!]/Punc\([^)]*\)/[\.?!] ",text)
    else:
        text = text.replace(".'", "'.")
        global expr
        if expr is None:
            lenmap = toolkit.DefaultDict(list)
            for a in abbrevs+months:
                lenmap[len(a)].append(a)
                lenmap[len(a)].append(a.title())
            expr = r"(?<!\b[A-Za-z])"
            for x in lenmap.values(): expr += r"(?<!\b(?:%s))" % "|".join(x)
            #expr += r"(?<Nov(?=. \d))"
            expr += r"[\.?!](?!\w|,)(?!\s[a-z])|\n\n"
            expr += r"|(?<=%s)\. (?=[^\d])" % "|".join(months)
            print expr
            expr = re.compile(expr)
            
        sents = expr.split(text)
        sents = [sent for sent in sents if sent.strip()]
        return sents
        

def splitPars(text, type=2, returnSents=True, flatten=False):
    if type==4:
        pars = re.split(r"\n\n|(?:\s*(?![\*\[\]+])\W/N\(soort,ev,neut\)/\W)+",text)
    else:
        pars = text.strip().split("\n\n")
    if returnSents:
        if not flatten: return  map(lambda x:split(x,type), pars)
        sents = []
        for par in pars:
            sents += split(par, type)
        return sents
            
    else:
        return pars

def splitParsJava(text, tv = False):
    command = tv and "java -cp /home/anoko/resources/javasbd SBDtv" or "java -cp /home/anoko/resources/javasbd SBD"
    i,o = os.popen2(command)
    i.write(text)
    i.close()
    pars = o.read().replace("\xa0","").split("\n\n")
    pars = [par.split("\n") for par in pars if par.strip()]
    return pars

if __name__ == '__main__':
    import sys
    print splitPars(sys.stdin.read())
    #print splitParsJava(sys.stdin.read())
    

