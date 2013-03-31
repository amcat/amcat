import re

from amcat.models.article import Article


dateline_regex = {
    71 : re.compile("^\*\*(([A-Z][a-zA-Z ]+)|([A-Z ]+))\.\*\*"),
    73 : re.compile("^\*\*(([A-Z][a-zA-Z ]+)|([A-Z ]+))\.\*\*"),
    69 : re.compile("(^[A-Z ]+)|(\*\*[A-Z ]+( \([A-Za-z\- ]+\))?, (maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\*\*\n"),
    131 : re.compile("\n\n([A-Z][a-z]+( [A-Z][a-z]+)?)\n")
    }

def get_dateline(text, setid):
    pattern = dateline_regex[setid]
    match = pattern.search(text)
    if match:
        return match.group(1)
    else:
        return None

def run():
    for setid in dateline_regex.keys():
        for article in Article.objects.filter(articlesetarticle__articleset = setid):
            article.dateline = get_dateline(article.text, setid)
            print(article.dateline)
            #article.save()
    
if __name__ == "__main__":
    run()
