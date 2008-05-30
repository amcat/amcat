import dbtoolkit, alpino, toolkit, traceback, sys

class Converter:
    def __init__(self, db):
        self.db = db
        self.lemmas = dict(((lem.lower().strip(), pos), lid) for (lid, lem, pos) in db.doQuery("SELECT lemmaid, lemma, pos FROM words_lemmata"))
        print self.lemmas[(":", ".")]
        self.words = dict(((lid, word.lower().strip()), wid) for (wid, lid, word) in db.doQuery("SELECT wordid, lemmaid, word FROM words_words"))
        self.rels = dict(db.doQuery("SELECT name, relid FROM parses_rels"))
        self.poss = dict(((a,b), id) for (a,b,id) in db.doQuery("SELECT major, minor, posid FROM parses_pos"))

    def _lemmaid(self, node):
        #print "   Finding lemmaid for %s" % node
        pos = {"verb" : 'V', "adj" : 'A', "noun" : 'N', "vg" : "C", "name" : "M", "adv" : "B",
               "det" : "D", "prep":"P", "comp":"C", "num":'Q', "punct" : '.',"pron":'O',
               "part" : 'R',"pp" : 'P', "fixed" : "R", "tag" : "I", "comparative" : 'C',
               "prefix" : '?', "--": "?", "sbar": "?", "tmp_adv" : "B", "max":"?"}[node.pos.main]
        l = node.lemma.lower().strip()
        lp = l, pos
        if lp in self.lemmas:
            #print "      Returning lemmaid from cache %i" % self.lemmas[lp]
            return self.lemmas[lp]
        #print "      %r Not found in cache" % (lp,)
        lemmaid = self.db.insert("words_lemmata", {"lemma": l, "pos" : pos})
        #print "      Inserted new lemmaid %i" % lemmaid
        self.lemmas[lp] = lemmaid
        return lemmaid

    def _wordid(self, node):
        #print "  Finding wordid for %s" % node
        lemmaid = self._lemmaid(node)
        w = node.word.lower().strip()
        #print "    Lemmaid = %i" % lemmaid
        lw = lemmaid, w
        if lw in self.words:
            #print "    Returning from cache %i" % self.words[lw]
            return self.words[lw]
        wordid = self.db.insert("words_words", {"lemmaid": lemmaid, "word" : w})
        self.words[lw] = wordid
        #print "    Inserted new wordid %i" % wordid
        return wordid

    def _relid(self, rel):
        if rel in self.rels:
            return self.rels[rel]      
        relid = self.db.insert("parses_rels", {"name": rel})
        self.rels[rel] = relid
        return relid

    def _posid(self, node):
        #print "  Finding posid for %s" % node
        key = node.pos.major, ",".join(node.pos.minor)
        if key in self.poss:
            #print "    Returning from cache %i" % self.poss[key]
            return self.poss[key]
        posid = self.db.insert("parses_pos", {"major":key[0], "minor":key[1]})
        #print "    Inserted new posid %i" % posid
        self.poss[key] = posid
        return posid

    def convert(self, sentid, jobid=4):
        #print "Doing %i" % sentid
        triples = self.db.getValue("SELECT parse FROM sentences_parses WHERE parsejobid=%i AND sentenceid=%i" % (jobid, sentid))
        s = alpino.fromFullTriples(triples)

        for node in s.nodeindex.values():
            l = self._wordid(node)
            p = self._posid(node)
            db.insert("parses_words", {"sentenceid": sentid, "wordbegin" : node.begin,
                                       "wordid" : l, "posid" : p}, retrieveIdent=False)
        for node in s.nodeindex.values():
            for rel, children in node.children.items():
                r = self._relid(rel)
                for child in children:
                    db.insert("parses_triples", {"sentenceid": sentid, "relation" : r, "parentbegin" : node.begin,
                                                 "childbegin" : child.begin}, retrieveIdent=False)
        #print "Done %i" % sentid
            
if __name__== '__main__':
    import sys
    db = dbtoolkit.anokoDB(auto_commit = False)
    c = Converter(db)
    jobid= int(sys.argv[1])
    skips = set([-1])
    toolkit.ticker.interval = 1000
    while True:
        skip = ",".join(str(i) for i in skips)
        sids = db.doQuery("select top 1000 sentenceid from sentences_parses where parsejobid=%i and parse is not null and sentenceid not in (select sentenceid from parses_triples) and sentenceid not in (%s)" % (jobid, skip))
        if not sids: break
        for sid, in sids:
            #toolkit.ticker.tick()
            try:
                c.convert(sid, jobid)
            except Exception, e:
                print "Error on converting %i" % sid
                print e
                traceback.print_exc(file=sys.stdout)
                skips.add(sid)
        toolkit.ticker.warn("Committing")
        db.conn.commit()
            
               
        
