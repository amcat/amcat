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
from amcat.scripts.tools import database

import amcat.scripts.forms
from django import forms
from django.db.models import Sum, Count
from amcat.models.medium import Medium
from amcat.tools.table import table3
from amcat.tools import keywordsearch
from django.db import connections

import datetime

class AggregationForm(amcat.scripts.forms.SelectionForm):
    """the form used by the Aggregation script"""
    xAxis = forms.ChoiceField(choices=(
                                ('date', 'Date'), 
                                ('medium', 'Medium'),
                                ('total', 'Total')
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
    relative = forms.BooleanField(label="Make values relative to (and exclude) first column", required=False)

class AggregationScriptForm(AggregationForm, amcat.scripts.forms.SelectionForm):
    pass
    
    
class AggregationScript(script.Script):
    input_type = None
    options_form = AggregationScriptForm
    output_type = table3.Table


    def run(self, input=None):
        """ returns a table containing the aggregations"""
        xAxis = self.options['xAxis']
        dateInterval = self.options['dateInterval']

        table = keywordsearch.getTable(self.options, self.progress_monitor)
        
        if self.options['relative']:
            q = getattr(table, "queries", None)
            table = RelativeTable(table)
            table.queries = q
            
        if xAxis == 'date':
            # TODO: fill out on elastic queries
            #table = FilledOutTable(table, dateInterval=dateInterval)
            table.rowNamesRequired = True # make sure row names are printed
            
        return table

class RelativeTable(table3.WrappedTable):
    def getColumns(self):
        return list(self.table.getColumns())[1:]
    def getValue(self, row, column):
        total_col = list(self.table.getColumns())[0]
        val = self.table.getValue(row, column)
        if val == 0: return val
        total = self.table.getValue(row, total_col)
        return float(val) / total if total else None

class FilledOutTable(table3.WrappedTable):
    def getRows(self):
        return fill_out(self.table.getRows(), self._kargs['dateInterval'])

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

        if m > _max_month:
            m  -= _max_month
            y += 1

def fill_days(van, tot):
    van = datetime.datetime.strptime(van, "%Y-%m-%d")
    tot = datetime.datetime.strptime(tot, "%Y-%m-%d")
    while True:
        yield van.strftime("%Y-%m-%d")
        van += datetime.timedelta(days=1)
        if van > tot:
            break
            
def _get_n_weeks(year):
    for i in range(31, 24, -1):
        d = datetime.datetime(year, 12, i)
        wk = d.isocalendar()[1]
        if wk != 1:
            return wk
            

if __name__ == '__main__':
    for x in fill_months("2001-01", "2002-02"):
        print x
    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAggregation(amcattest.AmCATTestCase):
    def test_n_weeks(self):
        self.assertEqual(_get_n_weeks(2013), 52)
        self.assertEqual(_get_n_weeks(2012), 52)
        self.assertEqual(_get_n_weeks(2011), 52)
        self.assertEqual(_get_n_weeks(2010), 52)
        self.assertEqual(_get_n_weeks(2009), 53)
        self.assertEqual(_get_n_weeks(2008), 52)        
        
    def test_fill_days(self):
        self.assertEqual(list(fill_days('2003-12-27', '2004-01-03')),
                         ['2003-12-27', '2003-12-28', '2003-12-29', '2003-12-30', '2003-12-31', '2004-01-01', '2004-01-02', '2004-01-03'])

    @amcattest.skip_TODO("Filling out dates not implemented for elastic")
    def test_dates(self):

        base = dict(xAxis='date', yAxis='medium', counterType='numberOfArticles', datetype='all')
        
        a1 = amcattest.create_test_article(date='2001-01-01')
        a2 = amcattest.create_test_article(date='2001-03-02', medium=a1.medium)
        a3 = amcattest.create_test_article(date='2001-08-12', medium=a1.medium)
        aset = amcattest.create_test_set(articles=[a1,a2,a3])
        aset.refresh_index()

        
        
        t = AggregationScript.run_script(dict(articlesets=[aset.id], projects=[aset.project_id],dateInterval='month', **base))

        self.assertEqual(set(t.to_list(row_names=True, tuple_name=None)), {('2001-%02i' % i, int(i in (1,3,8))) for i in range(1,9)})
        

        t = AggregationScript.run_script(dict(articlesets=[aset.id], projects=[aset.project_id],dateInterval='quarter', **base))
        self.assertEqual(set(t.to_list(row_names=True, tuple_name=None)), {('2001-1', 2), ('2001-2', 0), ('2001-3', 1)})
        
