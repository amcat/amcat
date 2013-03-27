import re

from amcat.models.article import Article


#site : (regex pattern, set id)
site_info = {
    'ad' : (re.compile("http://www.ad.nl/ad/nl/[0-9]+/([a-zA-Z]+)/article/"), 149),
    'nrc' : (re.compile("http://www.nrc.nl/([a-z]+)/[0-9]+/[0-9]+/[0-9]+/[a-zA-Z0-9\-]+"), 150),
    'parool' : (re.compile("http://www.parool.nl/parool/nl/[0-9]+/([A-Z\-]+)/article/"), 139),
    'volkskrant' : (re.compile("http://www.volkskrant.nl/vk/nl/[0-9]+/([a-zA-Z\-]+)/article/"), 146)
    }


def get_section(url):
    site = url.split("//www.")[1].split(".nl/")[0]
    pattern = site_info[site][0]
    match = pattern.search(url)
    print(match)
    print(match.group(1))
    return match.group(1)


def run():
    for setid in [s[1] for s in site_info.values()]:
        print(setid)
        for article in Article.objects.filter(articlesetarticle__articleset = setid):
            article.section = get_section(article.url).capitalize()
            print(article.section)
            #article.save()

if __name__ == "__main__":
    run()

