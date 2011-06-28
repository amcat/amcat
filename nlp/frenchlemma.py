# -*- coding: utf-8 -*-

from amcat.contrib import treetaggerwrapper
from amcat.tools import toolkit
import subprocess, re

RESOURCES = '/home/wva/toolkits/'
TAGGER = RESOURCES + 'treetagger/cmd/tree-tagger-french-utf8'
LEMMADIR = RESOURCES + 'flemm'
LEMMATISER = LEMMADIR + '/flemm_stdinout.pl'
PERL = "/usr/bin/perl"
LEMMACMD = "%s -I%s %s --entree - --sortie - --format normal --tagger treetagger" % (
    PERL, LEMMADIR, LEMMATISER)
BOUNDARY = " XXXXXXXXXXXXXXXXXX "

POSMAP = {"PRO": "O",
          "VER" : "V",
          "ADJ" : "A",
          "ADV" : "B",
          "DET" : "D",
          "NOM" : "N",
          "NAM" : "M",
          "SENT" : ".",
          "PRP" : "P",
          "PUN" : ".",
          "KON" : "C",
          "INT" : "I",
          "ABR" : "X",
          "NUM" : "Q",
          "SYM" : "?",
          "" : "?",
          }

def tagText(text):
    out, err = toolkit.execute(TAGGER, text)
    if not err.endswith("finished.\n"):
        raise Exception(`err`)
    return out


def lemmatiseText(text):
    tags = tagText(text)
    out, err = toolkit.execute(LEMMACMD,  tags)
    if err != 'Reading input from stdin\nSending output to stdout\n':
        raise Exception(err)
    return out

def lemmata2tokens(lemmata):
    for i, line in enumerate(lemmata.strip().split("\n")):
        if not line.strip(): continue
        if line.strip() == ':Vm--': continue # HEVERLEE is mutilated, why??
        info = line.split(" || ")[0].split("\t") # if multiple options, pick first
        if len(info) != 3:
            raise Exception("Cannot interpret line %r, %r" % (line, info))
        word, posstr, lemma = info
        if ":" in posstr:
            major, minor = posstr.split(":")
        else:
            major, minor = posstr, None
        cat = POSMAP[major.split("(")[0]]
        
                               
        yield (i, word, lemma, cat, major, minor) 


def encode(s):
    if type(s) == str:
        try:
            s = s.decode("utf-8")
        except:
            s = s.decode("latin-1")
    return s.encode("utf-8")

        
def parseSentences(sentences):
    text = BOUNDARY.join(encode(s) for (sid, s) in sentences)
    output =  lemmatiseText(text)
    splitter  = "{0}.*{0}\n".format(BOUNDARY.strip())
    output = re.split(splitter, output)

    if len(output) != len(sentences):

        raise Exception("|output| <> |sentences|!")
    for (sid, sent), lemmata in zip(sentences, output):
        try:
            tokens = list(lemmata2tokens(lemmata))
        except:
            print `sent`
            print `lemmata`
            for info in lemmata2tokens(lemmata):
                print info
            
            raise
        yield sid, (('tokens', tokens), )
        
        


if __name__ == '__main__':
    import sys

    txt = sys.stdin.read().decode("utf-8")
    print list(lemmatiseSentences([(12, txt)]))
    
