
#ranges: {<scraper>:[(1,3),(2,4)... for each day in the week starting monday

from amcat.models.article import Article

from datetime import date,timedelta
def days(start,end):
    if start>end:
        raise ValueError("start must be before end")
    
    while start<=end:
        yield end
        end -= timedelta(days=1)


from amcat.scripts.script import Script
class OmniScraper(Script):

    def get_normal_ranges(self):
        log.debug("importing normal ranges...")
        from expected_articles import expected_articles as ranges

    def run(self,input):    
        for scraper, rangelist in ranges.items():
            start = date(2012,01,01);end=date.today() - timedelta(days=6)
            for day in days(start,end):

                log.debug("getting amount of articles of scraper {} day {}".format(scraper,day))
                n_articles = self.get_n_articles(scraper,day)
                (lower,upper) = rangelist[day.weekday()]
                log.debug("n_articles: {}, lower: {}, upper: {}".format(n_articles,lower,upper))
                if n_articles < lower:
                    s_instance = scraper.get_scraper(date=day)
                    log.info("running scraper {s_instance} for date {day}".format(**locals()))
                    s_instance.run(None)
                           

    def get_n_articles(self,scraper,day):
        n_articles = Article.objects.filter(
            articlesetarticle__articleset = scraper.articleset_id,
            date = day
            ).count()
        return n_articles


if __name__ == '__main__':
    from amcat.scripts.tools import cli
    from amcat.tools import amcatlogging
    amcatlogging.info_module("amcat.scraping.scraper")
    amcatlogging.debug_module("amcat.scraping.controller")
    cli.run_cli(OmniScraper)
    
