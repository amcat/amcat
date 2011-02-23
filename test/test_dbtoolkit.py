from __future__ import unicode_literals, print_function, absolute_import
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

import datetime
from amcat.db import dbtoolkit
from amcat.test import amcattest

class TestDBToolkit(amcattest.AmcatTestCase):

    def testDBContext(self):
        with dbtoolkit.db() as db:
            self.assertEqual(db.getValue("select top 1 projectid from projects where projectid=2"), 2)
        self.assertRaises(Exception, db.getValue, "select top 1 projectid from projects")

    def testIntSelectionSQL(self):
        for colname, ints, result in[
            ("bla", [0], "(([bla] in (0)))"),
            ("bla", [], "(1=0)"),
            ("bla", [0,1,2,0], "(([bla] in (0,1,2)))"),
            ]:
            sql = self.db.intSelectionSQL(colname, ints)
            
            if self.db.dbType == "psycopg2":
                result = result.replace("[", '"').replace("]", '"')
            self.assertEqual(sql, result)
            # test generator instead of list
            sql = self.db.intSelectionSQL(colname, (i for i in ints))
            self.assertEqual(sql, result)

    def testUpdateSQL(self):
        for table, where, newvals, result in (
            ("test", dict(a=range(3)), dict(b=1), "UPDATE [test] SET [b]=1 WHERE (([a] in (0,1,2)))"),
            ("test", dict(a=12,c=["a","b"]), dict(b=1,x="b'b"), "UPDATE [test] SET [x]='b''b',[b]=1 WHERE [a] = 12 AND [c] IN ('a','b')"),
            ("test", dict(a="bla'bla"), dict(b=datetime.datetime(2001, 1, 1)), "UPDATE [test] SET [b]='2001-01-01 00:00:00' WHERE [a] = 'bla''bla'"),
            ):
            if self.db.dbType == "psycopg2":
                result = result.replace("[", '"').replace("]", '"')
            self.assertEqual(self.db._updateSQL(table, newvals, where), result)

    def createTestTable(self):
        table = self.db.createTable("updatetest", [("id", "int"), ("i", "int"), ("s", "varchar(255)"), ("d", "timestamp")], temporary=True)
        self.db.insert(table, dict(id=1, i=0), retrieveIdent=False)
        self.db.insert(table, dict(id=2, i=0, s='blabla', d='2001-01-01'), retrieveIdent=False)
        self.db.insert(table, dict(id=3, i=1, s="x'x", d=datetime.datetime(2010,1,1)),  retrieveIdent=False)
        return table

    def testCreateTestTable(self):
        self.createTestTable()

    def testInsert(self):
        table = self.createTestTable()
        data = self.db.doQuery("select * from %s order by id" % table)
        self.assertTrue(data)
        
    def testUpdate(self):
        table = self.createTestTable()
        self.db.update(table, where=dict(i=0), newvals=dict(s="bla'bla", d=None))
        data = self.db.select(table, ("id","i","s","d"), orderby="id")
        self.assertEqual(data, [(1, 0, "bla'bla", None),
                                (2, 0, "bla'bla", None),
                                (3, 1, "x'x", datetime.datetime(2010,1,1)),])
        self.db.update(table, where=dict(i=range(2)), newvals=dict(d=datetime.datetime(1990,1,1)))
        data = self.db.select(table, ("id","i","s","d"), orderby=["id", "i"])
        self.assertEqual(data, [(1, 0, "bla'bla", datetime.datetime(1990,1,1)),
                                (2, 0, "bla'bla", datetime.datetime(1990,1,1)),
                                (3, 1, "x'x", datetime.datetime(1990,1,1)),])

    def testSelectSQL(self):
        for table, columns, where, result in (
            ("test", ["a","b"], dict(x=1), "SELECT [a],[b] FROM [test] WHERE [x] = 1"),
            ("test", ["a"], dict(x="bla'bla",y=None), "SELECT [a] FROM [test] WHERE [y] is null AND [x] = 'bla''bla'"),
            ("test", ["a"], None, "SELECT [a] FROM [test]"),
            ):
            if self.db.dbType == "psycopg2":
                result = result.replace("[", '"').replace("]", '"')
            out = self.db._selectSQL(table, columns, where).replace("  ", " ")
            self.assertEqual(out, result)

    def testSelect(self):
        table = self.createTestTable()
        data = self.db.select(table, ("id","i","s","d"))
        self.assertEqual(data, [(1, 0, None, None),
                                (2, 0, 'blabla', datetime.datetime(2001,1,1)),
                                (3, 1, "x'x", datetime.datetime(2010,1,1)),])
        
        data = self.db.select(table, ("s","d"), where=dict(id=(1,2)))
        self.assertEqual(data, [(None, None),
                                ('blabla', datetime.datetime(2001,1,1))])
        
        data = self.db.select(table, "id", where=dict(s="x'x"), rowfunc=lambda i: i*3)
        self.assertEqual(data, [9])


        data = self.db.select(table, ("s","d"), where=dict(id=1), rowfunc=lambda *l : list(l))
        self.assertEqual(data, [[None, None]])


        
            
        
if __name__ == '__main__':
    amcattest.main()
