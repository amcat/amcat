import re

from amcat.models.article import Article


#site : (regex pattern, set id)
site_info = {
    'ad' : (re.compile("http://www.ad.nl/ad/nl/[0-9]+/([a-zA-Z]+)/article/"), 149),
    'nrc' : (re.compile(".nl/([a-z]+)/[0-9]+/[0-9]+/[0-9]+/"), 150),
    'parool' : (re.compile("http://www.parool.nl/parool/nl/[0-9]+/([A-Z\-]+)/article/"), 139),
    'volkskrant' : (re.compile("http://www.volkskrant.nl/vk/nl/[0-9]+/([a-zA-Z\-]+)/article/"), 146)
    }


def get_section(url):
    site = url.split(".")[1]
    if site == 'nrcnext':
        site = 'nrc'
    pattern = site_info[site][0]
    match = pattern.search(url)
    if match:
        return match.group(1)


def run():
    for setid in [s[1] for s in site_info.values()]:
        for article in Article.objects.filter(articlesetarticle__articleset = setid):
            print("url: {article.url}".format(**locals()))
            if article.url:
                article.section = get_section(article.url)
            if article.section:
                article.section = article.section.capitalize()
                article.save()

if __name__ == "__main__":
    run()

