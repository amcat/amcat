
from amcat.models.scraper import Scraper
from django.db import connection, transaction
from datetime import date,timedelta

cursor = connection.cursor()
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
    cursor.execute("select date(date) as day, count(date(date)) as amount from articles where article_id in (select article_id from articlesets_articles where articleset_id = {articleset_id}) group by date(date)".format(articleset_id=articleset_id))
    
    rows = cursor.fetchall()

    for i,rows in enumerate(sort_weekdays(rows)):
        numbers = [row[1] for row in rows]
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
        day = row[0].weekday()
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
    pprint(EXPECTED_N_ARTICLES)
        

    
        
        
