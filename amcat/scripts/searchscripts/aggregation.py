###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

"""
Script that performs a query on the database or on Solr and returns a table with the aggregated data.
the x and y axis can be chosen. When using Solr the counter can be set to 'numberOfHits' to aggragate the hit count.
Also aggregation by searchTerm is Solr specific.
"""

from amcat.scripts import script
from amcat.scripts.tools import solrlib, database
import amcat.scripts.forms
from django import forms
from django.db.models import Sum, Count
from amcat.models.medium import Medium
from amcat.tools import table
from django.db import connections

import datetime

class AggregationForm(amcat.scripts.forms.SelectionForm):
    """the form used by the Aggregation script"""
    xAxis = forms.ChoiceField(choices=(
                                ('date', 'Date'), 
                                ('medium', 'Medium')
                             ), initial = 'date')
    yAxis = forms.ChoiceField(choices=(
                            ('total', 'Total'), 
                            ('searchTerm', 'Search Term'), 
                            ('medium', 'Medium')
                         ), initial='medium')
    dateInterval = forms.ChoiceField(
                        choices=(
                            ('day', 'Day'), 
                            ('week', 'Week'), 
                            ('month', 'Month'), 
                            ('quarter', 'Quarter'), 
                            ('year', 'Year')
                        ), initial='month', required=False)
    counterType = forms.ChoiceField(choices=(
                        ('numberOfArticles', 'Number of Articles'), 
                        ('numberOfHits', 'Number of Hits')
                   ), initial='numberOfArticles')

class AggregationScriptForm(AggregationForm, amcat.scripts.forms.SelectionForm):
    pass
    
    
class AggregationScript(script.Script):
    input_type = None
    options_form = AggregationScriptForm
    output_type = table.table3.Table


    def run(self, input=None):
        """ returns a table containing the aggregations"""
        
        if self.options['useSolr'] == False: # make database query
            queryset = database.getQuerySet(**self.options).distinct()
            xAxis = self.options['xAxis']
            yAxis = self.options['yAxis']
            if xAxis == 'date':
                dateInterval = self.options['dateInterval']
                if not dateInterval: raise Exception('Missing date interval')
                engine = connections.databases['default']["ENGINE"]
                if engine == 'django.db.backends.postgresql_psycopg2':
                    dateStrDict = {'day':'YYYY-MM-DD', 'week':'YYYY-WW', 'month':'YYYY-MM', 'quarter':'YYYY-Q', 'year':'YYYY'}
                    xSql = "to_char(date, '%s')" % dateStrDict[dateInterval]
                elif engine == 'django.db.backends.sqlite3':
                    xSql = {'day':"strftime('%Y-%m-%d', date)",
                            'month':"strftime('%Y-%m', date)",
                            'year':"strftime('%Y', date)",
                            'quarter':"strftime('%Y', date) || '-' ||  cast((cast(strftime('%m', date) as integer) + 2) / 3 as string)",
                            }[dateInterval]
                else:
                    raise Exception("Aggregation not supported for engine {engine}".format(**locals()))
            elif xAxis == 'medium':
                xSql = 'medium_id'
            else:
                raise Exception('unsupported xAxis')
                
            if yAxis == 'medium':
                ySql = 'medium_id'
            elif yAxis == 'total':
                ySql = None
            elif yAxis == 'searchTerm':
                raise Exception('searchTerm not supported when not performing a search')
            else:
                raise Exception('unsupported yAxis')
                
            select_data = {"x": xSql}
            vals = ['x']
            if ySql:
                select_data["y"] = ySql
                vals.append('y')

            # the following line will perform a group by database query
            data = queryset.extra(select=select_data).values(*vals).annotate(count=Count('id'))
            xDict = {}
            if xAxis == 'medium':
                xDict = Medium.objects.in_bulk(set(row['x'] for row in data)) # retrieve the Medium objects
            yDict = {}
            if yAxis == 'medium':
                yDict = Medium.objects.in_bulk(set(row['y'] for row in data)) # retrieve the Medium objects
            
            table3 = table.table3.DictTable(0) # the start aggregation count is 0
            table3.rowNamesRequired = True # make sure row names are printed

            for row in data:
                x = row['x']
                y = row.get('y', 'total')
                count = row['count']
                table3.addValue(xDict.get(x, x), yDict.get(y, y), count)

            print table3.rows
            table3.rows = list(fill_out(table3.rows, dateInterval))
            print table3.rows
                
            return table3
        else:
            return solrlib.basicAggregate(self.options)
            

def fill_months(van, tot, interval=1, max_month=12, output="{y}-{m:02}"):
    y,m = map(int, van.split("-"))
    toty, totm = map(int, tot.split("-"))
    while True:
        date = output.format(**locals())
        yield date

        if y > toty or (y == toty and m >= totm):
            break
        
        m += interval

        _max_month = max_month(y) if callable(max_month) else max_month

        print y, _max_month
        if m > _max_month:
            m  -= _max_month
            y += 1

def fill_days(van, tot):
    van = datetime.datetime.strptime(van, "%Y-%m-%d")
    tot = datetime.datetime.strptime(tot, "%Y-%m-%d")
    while True:
        yield van.strftime("%Y-%m-%d")
        van += datetime.timedelta(days=1)
        if van >= tot:
            break
            
def _get_n_weeks(year):
    for i in range(31, 24, -1):
        d = datetime.datetime(year, 12, i)
        wk = d.isocalendar()[1]
        if wk != 1:
            return wk
            

def fill_out(rows, interval):
    rows = sorted(rows)
    if interval == 'month':
        return fill_months(rows[0], rows[-1])
    elif interval == 'quarter':
        return fill_months(rows[0], rows[-1], max_month=4, output="{y}-{m}")
    elif interval == 'year':
        return map(str, range(int(rows[0]), int(rows[-1]) + 1))
    elif interval == 'week':
        return fill_months(rows[0], rows[-1], max_month=_get_n_weeks)
    elif interval == 'day':
        return fill_days(rows[0], rows[-1])
    else:
        raise Exception("Cannot fill %s" % interval)
        
if __name__ == '__main__':
    for x in fill_months("2001-01", "2002-02"):
        print x
    
    #from amcat.scripts.tools import cli
    #cli.run_cli(AggregationScript)



###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAggregation(amcattest.PolicyTestCase):
    def test_n_weeks(self):
        self.assertEqual(_get_n_weeks(2013), 52)
        self.assertEqual(_get_n_weeks(2012), 52)
        self.assertEqual(_get_n_weeks(2011), 52)
        self.assertEqual(_get_n_weeks(2010), 52)
        self.assertEqual(_get_n_weeks(2009), 53)
        self.assertEqual(_get_n_weeks(2008), 52)        
        
    def test_fill_days(self):
        self.assertEqual(list(fill_days('2003-12-27', '2004-01-03'))
                         ['2003-12-27', '2003-12-28', '2003-12-29', '2003-12-30', '2003-12-31', '2004-01-01', '2004-01-02'])
    
    def test_dates(self):

        base = dict(xAxis='date', yAxis='medium', counterType='numberOfArticles', datetype='all')
        
        a1 = amcattest.create_test_article(date='2001-01-01')
        a2 = amcattest.create_test_article(date='2001-03-02', medium=a1.medium)
        a3 = amcattest.create_test_article(date='2001-08-12', medium=a1.medium)
        aset = amcattest.create_test_set(articles=[a1,a2,a3])

        
        
        t = AggregationScript.run_script(dict(articlesets=[aset.id], projects=[aset.project_id],dateInterval='month', **base))
        
        self.assertEqual(set(t.to_list(row_names=True, tuple_name=None)), {('2001-%02i' % i, int(i in (1,3,8))) for i in range(1,9)})
        

        t = AggregationScript.run_script(dict(articlesets=[aset.id], projects=[aset.project_id],dateInterval='quarter', **base))
        self.assertEqual(set(t.to_list(row_names=True, tuple_name=None)), {('2001-1', 2), ('2001-2', 0), ('2001-3', 1)})
        
