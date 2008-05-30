import sys, re, toolkit

LEMMADICT_FILE = '/home/anoko/resources/wvalemma/lemmadict.txt'
POS_LEMMADICT_FILE = '/home/anoko/resources/wvalemma/lemmadict_pos.txt'
GUESS_PROGRAM = '/home/anoko/resources/wvalemma/guess'
SEPARATOR = '/'

def lemma2surface(line):
    result = ""
    for token in re.split("(\s+)", line):
        if re.match("\s+", token):
            result += token
        else:
            result += token.split("/")[0]
    return result

class Lemmatizer:

    def __init__(this, options = []):
        this.parseOptions(options)
        this.readDictionaries()

    def warn(this, msg):
        if this.VERBOSE:
            import toolkit
            toolkit.warn(msg)

    def readDictionaries(this):
        this.lemmadict = {}
        this.warn("Reading lemma dictionary")
        for l in open(LEMMADICT_FILE):
            wrd, lemma = l.split('|')
            this.lemmadict[wrd] = lemma[:-1]

        if this.USE_POS:
            this.poslemmadict = {}
            this.warn("Reading tagged lemma dictionary")
            for l in open(POS_LEMMADICT_FILE):
                wrd, pos, lemma = l.split('|')
                this.poslemmadict[wrd+'/'+pos.lower()] = lemma[:-1]

        this.revlemma = None
        this.revposlemma = None

    def reverseDictionaries(this):
        this.revlemma = {}
        for key, val in this.lemmadict.items():
            this.revlemma[val] = this.revlemma.get(val, []) + [key]

        if this.USE_POS:
            this.revposlemma = {}
            for key, val in this.poslemmadict.items():
                pos = key[-1]
                key = key[:-2]
                val = val + "/" + pos
                this.revposlemma[val] = this.revposlemma.get(val, []) + [key]
        

    def delemmatize(this, word, pos=None):
        if this.revlemma == None:
            this.reverseDictionaries()
    
        if pos==None or (not this.USE_POS):
            result = this.revlemma.get(word, [])
        else:
            result = this.revposlemma.get(word + "/" + pos.lower(), [])
        if result == []:
            if this.OUTPUT_ORIGINAL_IF_UNKNOWN:
                return [word]
        return result
        

    def lemmatize(this, word):
        word = word.strip()
        if this.OUTPUT_WORD:
            result = "%s%s" % (word, SEPARATOR)
        else:
            result = ""
            
        if this.LOWERCASE: word = word.lower()
        if this.USE_POS:
            try:
                w, pos = word.split('/')[:2]
                word = w
                if len(pos) > 1: pos = pos[0]
                wp = w + '/' + pos.lower()
                if wp in this.poslemmadict:
                    return result + this.poslemmadict[wp]
                elif this.FORCE_POS:
                    return result + word
            except ValueError, details:
                if this.VERBOSE: warn("could not parse word: %s (%s)" % (word, details) )


        if word in this.lemmadict:
            return result + this.lemmadict[word]
        elif this.USE_GUESS:
            import os
            return result + os.popen2('echo "%s" | %s' % (re.sub(r'"', '\\"', word), GUESS_PROGRAM))[1].read().strip()
        elif this.OUTPUT_ORIGINAL_IF_UNKNOWN:
            return result + word
        else:
            return result + '?'
    

    def parseOptions(this, options):
        if '-h' in options or '--help' in options:
            print "%s [-h] [-v] [-o] [-w] [-g] [WORDS]\n\nLemmatizes all words on command line or (if none)  on standard input stream (one word per line). Lemmatization is based on a lemma dictionary in file '%s' (format: one WORD|LEMMA entry per line)\nOptions:\n-h  Show this information and exit\n-v  Verbose: output some debugging infor\n-o  Output '?' for unknown words (otherwise output original word)\n-w  Also output original word\n-l  Convert input to lowercase before finding lemma\n-g  Use program '%s' for guessing unknown words\n-p  Assume input is POS-tagged; words should look like WORD/POS where the first character of POS should be 'n','v','a' (case insensitive). Other (word) characters are allowed but will be ignored.\n-q  If WORD/POS not found, do not fallback to WORD but consider unknown\n-d Delemmatize instead of lemmatize\n-r first lemmatize each word, then delemmatize it, do not combine with -w\n\n" % (options[0], LEMMADICT_FILE, GUESS_PROGRAM)
            sys.exit(1)
            
        this.OUTPUT_ORIGINAL_IF_UNKNOWN = not '-o' in options
        this.OUTPUT_WORD = '-w' in options
        this.VERBOSE     = '-v' in options
        this.LOWERCASE   = '-l' in options
        this.USE_GUESS   = '-g' in options
        this.USE_POS     = '-p' in options
        this.FORCE_POS   = '-q' in options
        this.DELEMMATIZE = '-d' in options
        this.DELEMLEM    = '-r' in options
        



    def lemmatizeList(this, wordlist):
        result = ""
        #toolkit.ticker.interval = 1000
        list = re.split('(\s+)', wordlist)
        for l in list:
            if not l: continue
            #toolkit.ticker.tick("/ %d = %2f%%" % (len(list), 100.0 * toolkit.ticker.i / len(list)))
            if re.match('\s+', l):
                result += l
            else:
                
                if this.DELEMLEM:
                    result += "/".join(this.delemmatize(this.lemmatize(l)))
                elif this.DELEMMATIZE:
                    result += "/".join(this.delemmatize(l))
                else:
                    result += this.lemmatize(l)
        return result


if __name__ == '__main__':
    l= Lemmatizer(sys.argv[1:])
    print l.lemmatizeList(sys.stdin.read())

        
