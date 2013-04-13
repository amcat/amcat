import re
import time
import json
from amcat.models.article import Article


dateline_regex = {
    71 : re.compile("^\*\*(([A-Z][a-zA-Z ]+)|([A-Z ]+))\.\*\*"),
    73 : re.compile("^\*\*(([A-Z][a-zA-Z ]+)|([A-Z ]+))\.\*\*"),
    69 : re.compile("(^[A-Z ]+)|(\*\*([A-Z ]+( \([A-Za-z\- ]+\))?), (maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\*\*)\n"),
    131 : re.compile("\n\n([A-Z][a-z]+( [A-Z][a-z]+)?)\n")
    }

I = 0
def get_dateline(article, setid):
    global I
    pattern = dateline_regex[setid]
    match = pattern.search(article.text)

    if match:
        #I += 1
        #print(I)
        if setid==69:
            if match.group(1):
                return match.group(1)
            else:
                return match.group(2).strip("*")
        return match.group(1)


def run():
    for setid in dateline_regex.keys():
        print(setid)
        for article in Article.objects.filter(articlesetarticle__articleset = setid):
            dateline = get_dateline(article, setid)
            if dateline:
                try:
                    meta = json.loads(article.metastring)
                except Exception as e:
                    print(e)
                    print(article.metastring)
                    time.sleep(10)
                    continue
                meta['dateline'] = dateline
                article.metastring = json.dumps(meta)
                article.save()
    
if __name__ == "__main__":
    run()
