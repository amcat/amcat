from celery import task, group
import time
from celery.utils.log import get_task_logger; log = get_task_logger(__name__)
import logging
from amcat.models.scraper import Scraper

#Things that cannot be serialized:
#- Scraper script (unless...)
#- Any Django model

class LockHack(object):
    #awaiting a better solution
    def acquire(self):pass
    def release(self):pass

@task()
def run_scraper(scraper):
    log.setLevel(logging.INFO)
    scraper._initialize()
    scraper.opener.cookiejar._cookies_lock = LockHack()
    log.info("Running scraper {scraper._id}: {scraper.__class__.__name__}".format(**locals()))
    result = group([scrape_unit_save_unit.s(scraper, unit) for unit in scraper._get_units()]).delay()
    return (scraper, result)
    
@task()
def scrape_unit_save_unit(scraper, unit):
    log.info("Recieved unit: {unit}".format(**locals()))
    articles = list(scraper._scrape_unit(unit))
    if len(articles) == 0:
        log.warning("scrape_unit returned 0 units")
    articles = [scraper._postprocess_article(article) for article in articles]
    #articles' parents at this point still link to the unprocessed articles
    for article in articles:
        #find some unique identifier 
        urls = dict([(article.url, article) for article in articles])
        article.parent = urls[article.url]
    #articles' parents are now unsaved models. they need to be saved in the right order.
    return save_ordered(articles)

def save_ordered(articles):
    queue = [a for a in articles if a.parent == None]
    for article in queue:
        saved = article.save()
        #get children, add to queue
        for child in articles:
            if child.parent == article and child != parent: #...
                child.parent = saved
                queue.append(child)
    #safety measure
    for article in articles:
        if article not in queue:
            article.save()
    log.info("saved {n} articles".format(n = len(articles)))
    return articles
