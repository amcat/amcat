import re

def _getQuoteWords(words):
    if type(words) not in (str, unicode): words = " ".join(words)
    words = re.sub(r'[^\w\s]+', '', words)
    wordset = set(re.split(r'\s+', words.lower()))
    return wordset
    
def quote(words, words_or_wordfilter, quotelen=4, totalwords=25, boldfunc = lambda w : "<em>%s</em>" % w):
    """Return a 'google-blurb' from words containing certain words

    @param words: a sequence of words to take the quote from
    @param words_or_wordfilter: a set of words to base the quote on, or a function
      that returns True for words that should be in the quote
    @param quotelen: the number of 'found' words in the quote
    @param totalwords: the total number of words to return
    @param boldfunc: called to transform the found words (eg to make them bold
    @return: a string containing the quote, with ... between snippets
    """
    if callable(words_or_wordfilter):
        filt = words_or_wordfilter
    else:
        wordset = _getQuoteWords(words_or_wordfilter)
        filt = lambda x: int(x.lower() in wordset)

    positions = {}
    for i, w in enumerate(words):
        if filt(w):
            positions[i] = 0

    default = " ".join(words[:totalwords] + ["..."])
            
    for pos in sorted(positions.keys()):
        nbs = 0
        for w in positions:
            dist = abs(w - pos)
            nbs += int(dist > 0 and dist <= quotelen)
        positions[pos] = nbs
    if not positions: return None
    quotewords = set() # wordids
    boldwords = set()
    while len(quotewords) < totalwords:
        pos, nbs = sortByValue(positions, reverse=True)[0]
        boldwords.add(pos)
        quote = range(max(0, pos - quotelen), min(len(words), pos + quotelen + 1))
        quotewords |= set(quote)
        del positions[pos]
        if not positions: break
    if not quotewords: return None
    lag = -1
    result = []
    quotewords = sorted(quotewords)
    for i in quotewords:
        if i > lag+1: result += ["..."]
        result += [boldfunc(words[i])] if (i in boldwords and boldfunc) else [words[i]]
        lag = i
    if quotewords[-1] <> len(words) - 1:
        result += ["..."]
    
    return " ".join(result)
