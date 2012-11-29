print("getting expected amounts of articles per scraper per day...")
from n_articles_day import EXPECTED_N_ARTICLES as ranges
print("done")

#ranges: {<scraper>:[(1,3),(2,4)... for each day in the week starting monday

from django.db import connection,transaction
cursor = connection.cursor()

from datetime import date,timedelta
def days(start,end):
    if start>end:
        raise ValueError("start must be before end")
    
    while start<=end:
        yield end
        end -= timedelta(days=1)


from amcat.scripts.script import Script
class OmniScraper(Script):

    def run(self,input):    
        for scraper, rangelist in ranges.items():
            start = date(2012,01,01);end=date.today() - timedelta(days=6)
            for day in days(start,end):

                print("getting amount of articles of scraper {} day {}".format(scraper,day))
                n_articles = self.get_n_articles(scraper,day)
                (lower,upper) = rangelist[day.weekday()]
                print("n_articles: {}, lower: {}, upper: {}".format(n_articles,lower,upper))
                if n_articles < lower:
                    s_instance = scraper.get_scraper(date=day)
                    print("running scraper {s_instance} for date {day}".format(**locals()))
                    s_instance.run(None)
                           

    def get_n_articles(self,scraper,day):


        query = """
        select count(*) from articles
        where article_id in(
            select article_id from articlesets_articles
            where articleset_id = {s_a_id}
        )
        and date = '{d}'""".format(
            s_a_id = scraper.articleset_id,
            d = day
            )
        
        cursor.execute(query)
        n_articles = cursor.fetchone()[0]
        return n_articles




if __name__ == '__main__':
    from amcat.scripts.tools import cli
    from amcat.tools import amcatlogging
    amcatlogging.info_module("amcat.scraping.scraper")
    amcatlogging.debug_module("amcat.scraping.controller")
    cli.run_cli(OmniScraper)
    
