
from amcat.models.scraper import Scraper
from amcat.models.article import Article
from django.db.models import Count
from datetime import date,timedelta

scrapers = Scraper.objects.all()

def scraper_ranges(scraper):
    returns = [
        (0,0),
        (0,0),
        (0,0),
        (0,0),
        (0,0),
        (0,0),
        (0,0)
        ]

    articleset_id = scraper.articleset_id
    rows = Article.objects.filter(articlesetarticle__articleset = articleset_id).extra({'date':"date(date)"}).values('date').annotate(created_count=Count('id'))
                         
    for i,rows in enumerate(sort_weekdays(rows)):
        numbers = [row['created_count'] for row in rows]
        third_q = third_quartile(numbers)
        returns[i] = (third_q/1.5,third_q*2)
        

    return returns


def sort_weekdays(rows):
    days = [
        [], #Monday
        [],
        [],
        [],
        [],
        [],
        []  #Sunday
        ]

    for row in rows:
        day = row['date'].weekday()
        days[day].append(row)

    for rows in days:
        yield rows
        
def third_quartile(numbers):
    numbers = sorted(numbers)
    L = len(numbers)
    if L == 0:
        return 0
    elif L == 1:
        return numbers[0]
    else:
        pointer = int(L*(3.0/4.0))
        return numbers[pointer]

def generate_ranges():
    d_ranges = {}
    for scraper in scrapers:
        d_ranges[scraper] = scraper_ranges(scraper)
    return d_ranges


expected_articles = generate_ranges()


if __name__ == '__main__':
    from pprint import pprint
    pprint(expected_articles)
        

    
        
        
