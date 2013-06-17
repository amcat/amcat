"""The nu.nl scraper is in need of a terms list to use in the website's search function

This script will determine the list that will provide the best results"""

from amcat.models.article import Article
import re

def wordlist():
    articles = Article.objects.filter(articlesetarticle__articleset=135)
    worddict = {}
    for i, article in enumerate(articles[:1000]):
        #removing punctuation
        text = re.sub(
            "[^a-zA-Z]+",
            " ",
            article.text)

        words = set([w.lower() for w in text.split(" ")])
        print("{i} - {article}".format(**locals()))
        for w in words:
            if w in worddict.keys():
                worddict[w] += 1
            else:
                worddict[w] = 1

    for w in list(reversed(sorted(worddict.items(), cmp = lambda x, y: cmp(x[1], y[1]))))[:50]:
        print(w)


if __name__ == "__main__":
    wordlist()
