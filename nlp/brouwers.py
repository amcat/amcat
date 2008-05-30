#! /bin/env python2.2

import dbtoolkit, sys, re, toolkit

POSMAP = {'W' : 'V', 'B' : 'A'}
LENIENT = 0

#if len(sys.argv)==1:a
#x    sys.argv.append(["-c"])

class Brouwers:

    def __init__(this, options):
        this.DB = dbtoolkit.anokoDB(None, 1)
        this.parseOptions(options)
        

    def parseOptions(this, options):
        this.INCLUDE_ID = '-i' in options
        this.INCLUDE_CAT = '-c' in options
        this.INCLUDE_SCAT = '-s' in options
        this.INCLUDE_SSCAT = '-z' in options
        this.INCLUDE_SK = '-k' in options
        this.INCLUDE_EX = '-x' in options
        this.COLLAPSE_EQUAL = not '-e' in options
        
        if not (this.INCLUDE_ID or this.INCLUDE_CAT or this.INCLUDE_SCAT or this.INCLUDE_SSCAT or this.INCLUDE_SK or this.INCLUDE_EX): this.INCLUDE_CAT=1

        
    def slookup(this, word, pos):
        l = this.lookup(word, pos)
        #toolkit.warn("Looking up %s (%s)" % (word, pos))
        list = []
        for candidate in l:
            c = []
            if this.INCLUDE_ID:       c.append(`candidate[0]`)
            if this.INCLUDE_CAT:      c.append(`candidate[1]`)
            if this.INCLUDE_SCAT:     c.append(`candidate[2]`)
            if this.INCLUDE_SSCAT:    c.append(`candidate[3]`)
            if this.INCLUDE_SK:       c.append(`candidate[4]`)
            if this.INCLUDE_EX:       c.append(`candidate[5]`)
            list.append("|".join(c))

        if this.COLLAPSE_EQUAL:
            list = toolkit.unique(list)
    
        return "[%s]" % ",".join(list)

    def tlookup(this, word, pos):
        l = this.lookup(word, pos)
        #toolkit.warn("Looking up %s (%s)" % (word, pos))
        list = []
        for candidate in l:
            c = []
            if this.INCLUDE_ID:       c.append(`candidate[0]`)
            if this.INCLUDE_CAT:      c.append(`candidate[1]`)
            if this.INCLUDE_SCAT:     c.append(`candidate[2]`)
            if this.INCLUDE_SSCAT:    c.append(`candidate[3]`)
            if this.INCLUDE_SK:       c.append(`candidate[4]`)
            if this.INCLUDE_EX:       c.append(`candidate[5]`)
            list.append(c)

        if this.COLLAPSE_EQUAL:
            list = toolkit.unique(list)
    
        return list


    def lookup(this, word, pos):
        #words = dict(zip(sys.argv, [None] * len(sys.argv)))
        #namelist = "('%s')" % "','".join(words.keys())
        namelist = "(%s)" % toolkit.quotesql(word)


        
        all = []
        correct = []

        for id, bpos, name, cat, scat, sscat, sk, ex in this.DB.doQuery("SELECT id,pos,word,cat,scat,sscat, cat_sk, cat_ex from brouwers WHERE word in %s"  % namelist):
            if POSMAP.get(bpos, bpos) == pos:
                correct.append((id, cat, scat, sscat, sk, ex))
            all.append((id, cat, scat, sscat, sk, ex))

        if correct or not LENIENT:
            return correct
        else:
            return all


    def lookupList(this, list):
        result = ""

        for l in re.split('(\s+)', list):
            if re.match('\s+', l):
                result += l
                continue
            w = l
            info = l.split('/')
            if len(info) > 1:
                pos = info[1]
                w = info[0]
            else:
                pos = None
            if len(info) > 2:
                w = info[2]

            result += l+'/'+this.slookup(w,pos)

        return result


if __name__ == '__main__':
    wordlist = " ".join(filter(lambda x:x[0] != '-', sys.argv[1:])) + '\n'

    if wordlist == '\n':
        wordlist = sys.stdin.read()

    print Brouwers(sys.argv).lookupList(wordlist)


