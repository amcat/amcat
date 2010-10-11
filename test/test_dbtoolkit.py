import dbtoolkit, unittest, dbtoolkit, amcattest, datetime

class TestProject(amcattest.AmcatTestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)

    def testUpdateSQL(self):
        for table, where, newvals, result in (
            ("test", dict(a=range(3)), dict(b=1), "UPDATE [test] SET [b]=1 WHERE (([a] in (0,1,2)))"),
            ("test", dict(a=12,c=["a","b"]), dict(b=1,x="b'b"), "UPDATE [test] SET [x]='b''b',[b]=1 WHERE [a] = 12 AND [c] IN ('a','b')"),
            ("test", dict(a="bla'bla"), dict(b=datetime.datetime(2001, 1, 1)), "UPDATE [test] SET [b]='2001-01-01 00:00:00' WHERE [a] = 'bla''bla'"),
            ):
            self.assertEqual(self.db._updateSQL(table, newvals, where), result)

    def createTestTable(self):
        self.db.doQuery("create table #updatetest (id int, i int, s varchar(255), d datetime)")
        self.db.insert("#updatetest", dict(id=1, i=0), retrieveIdent=False)
        self.db.insert("#updatetest", dict(id=2, i=0, s='blabla', d='2001-01-01'), retrieveIdent=False)
        self.db.insert("#updatetest", dict(id=3, i=1, s="x'x", d=datetime.datetime(2010,1,1)),  retrieveIdent=False)
        return "#updatetest"
    
    def testInsert(self):
        table = self.createTestTable()
        data = self.db.doQuery("select * from #updatetest order by id")
        self.assertTrue(data)
        
    def testUpdate(self):
        table = self.createTestTable()
        self.db.update("#updatetest", where=dict(i=0), newvals=dict(s="bla'bla", d=None))
        data = self.db.select(table, ("id","i","s","d"))
        self.assertEqual(data, [(1, 0, "bla'bla", None),
                                (2, 0, "bla'bla", None),
                                (3, 1, "x'x", datetime.datetime(2010,1,1)),])
        self.db.update("#updatetest", where=dict(i=range(2)), newvals=dict(d=datetime.datetime(1990,1,1)))
        data = self.db.select(table, ("id","i","s","d"))
        self.assertEqual(data, [(1, 0, "bla'bla", datetime.datetime(1990,1,1)),
                                (2, 0, "bla'bla", datetime.datetime(1990,1,1)),
                                (3, 1, "x'x", datetime.datetime(1990,1,1)),])

    def testSelectSQL(self):
        for table, columns, where, result in (
            ("test", ["a","b"], dict(x=1), "SELECT [a],[b] FROM [test] WHERE [x] = 1"),
            ("test", ["a"], dict(x="bla'bla",y=None), "SELECT [a] FROM [test] WHERE [y] is null AND [x] = 'bla''bla'"),
            ("test", ["a"], None, "SELECT [a] FROM [test]"),
            ):
            self.assertEqual(self.db._selectSQL(table, columns, where), result)

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
    unittest.main()
