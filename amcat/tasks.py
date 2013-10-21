from celery import task, group, chord
import time

# test 'tasks' for emulating scraping

class FakeScraper:
    def get_units(self, i):
        time.sleep(1)
        return range(i)

    def scrape_unit(self, unit):
        print ">> Scraping", unit
        time.sleep(unit)
        return "DOCUMENT_%i" % unit

@task
def scraper_getunits(scraper, context):
    print "<< scraper_getunits", [scraper, context]
    units = scraper().get_units(context)
    print ">> scraper_getunits", units
    return units

@task
def scraper_scrape(unit, scraper):
    print "<< scraper_scrape", unit
    doc = scraper().scrape_unit(unit)
    print ">> scraper_scrape", doc
    return doc

@task
def store_results(docs):
    print ">> store_results", docs
    return len(docs)

@task
def dmap(it, subtask):
    # Map a callback over an iterator and return as a group
    return group(subtask.clone([arg,]) for arg in it)()

@task
def do_scrape(scraper, context):
    units = scraper().get_units(context)
    c = chord(scraper_scrape.s(unit, scraper) for unit in units)(store_results.s())
    return c



