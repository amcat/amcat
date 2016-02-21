from amcat.tools import amcattest
from amcat.tools.table import tableoutput
from amcat.tools.table.table3 import Table, ListTable, ObjectTable, ObjectColumn, \
    SortedTable, ColumnViewTable


class TestTable(amcattest.AmCATTestCase):
    def test_init(self):
        """Does init use 'empty' parameters?"""
        a = []
        t = Table(columns=a)
        self.assertIs(t.columns, a)

    def test_list_table(self):
        """Can we create a list table and output as ascii"""
        t = ListTable(colnames=["a1", "a2", "a3"],
                      data=[[1, 2, 3],
                            [74321, 8, 9],
                            [4, 5, "asdf"],
                      ])
        result = tableoutput.table2unicode(t)
        correct = '''
 ╔═══════╤════╤══════╗
 ║ a1    │ a2 │ a3   ║
 ╟───────┼────┼──────╢
 ║ 1     │ 2  │ 3    ║
 ║ 74321 │ 8  │ 9    ║
 ║ 4     │ 5  │ asdf ║
 ╚═══════╧════╧══════╝'''
        self.assertEquals(_striplines(result), _striplines(correct.strip()))

    def test_object_table(self):
        """Does creating object tables work"""

        class Test(object):
            def __init__(self, a, b, c):
                self.a, self.b, self.c = a, b, c

        l = ObjectTable(rows=[Test(1, 2, 3), Test("bla", None, 7), Test(-1, -1, None)])
        l.addColumn(lambda x: x.a, "de a")
        l.addColumn("b")
        l.addColumn(ObjectColumn("en de C", lambda x: x.c))

        result = tableoutput.table2unicode(l)
        # get rid of pesky unicode
        result = result.translate(dict((a, 65 + a % 26) for a in range(0x2500, 0x2600)))

        correct = '''OKKKKKKEKKKKEKKKKKKKKKR
L de a K b  K en de C L
ZIIIIIIQIIIIQIIIIIIIIIC
L 1    K 2  K 3       L
L bla  K    K 7       L
L -1   K -1 K         L
UKKKKKKHKKKKHKKKKKKKKKX'''
        self.assertEquals(_striplines(result), _striplines(correct.strip()))

    def test_sort(self):
        """Do wrapped tables work?"""
        t = ListTable(colnames=["a1", "a2", "a3"],
                      data=[[1, 2, 3], [7, 8, 9], [4, 5, -4]])

        s = SortedTable(t, key=lambda row: row[1])
        self.assertEqual([list(row) for row in s], [[1, 2, 3], [4, 5, -4], [7, 8, 9]])
        v = ColumnViewTable(s, ["a1", "a3"])
        self.assertEqual([list(row) for row in v], [[1, 3], [4, -4], [7, 9]])

        s = SortedTable(t, key=lambda row: row[2])
        self.assertEqual([list(row) for row in s], [[4, 5, -4], [1, 2, 3], [7, 8, 9]])


def _striplines(x):
    """Strip each line in x to make comparison easier"""
    return "\n".join(l.strip() for l in x.split("\n")).strip()