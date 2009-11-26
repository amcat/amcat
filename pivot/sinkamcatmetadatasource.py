import amcatmetadatasource, dbtoolkit, tabulator
from mst import getSolution
from datasource import FunctionalDataModel

class SinkData(object):
    def __init__(self, table):
        self.table = table
        self.rows = len(self.table)
        self.columns = len(self.table[0])
        self.matrix = []

    def createTableMatrix(self):
        for r in range(self.rows):
            self.matrix.append(self.getRow(r))
        return self.matrix

    def createSortedTableMatrix(self,column):
        ls = list(self.getColumn(column))
        ls.sort()
        sortedTable = []
        for row in self.table:
            for r, l in enumerate(ls):
                if l == row[column]:
                    sortedTable.append(self.getRow(r))
        return sortedTable

    def getRow(self, index):
        rowlist = []
        for rowitem in self.table[index]:
            rowlist.append(rowitem)
        return rowlist
    
    def getColumn(self, index):
        cols = []
        for i in range(self.getNumberOfRows()):
            cols.append(self.table[i][index])
        return cols

    def getNumberOfRows(self):
        return len(self.table)

    def getNumberOfColumns(self):
        return len(self.table[0])


if __name__ == '__main__':
    import tabulator, dbtoolkit, amcatmetadatasource
    from mst import getSolution
    from datasource import FunctionalDataModel
    from amcatmetadatasource import AmcatMetadataSource
    
    db = dbtoolkit.amcatDB()
    ads = AmcatMetadataSource(db)
    dm = FunctionalDataModel(getSolution)
    dm.register(ads)
    
    filters = { "project" : [368], "article" : [44134023, 44134026, 44134078]  }
    select = ["project","article", "date", "batch"]

    data = tabulator.tabulate(dm, select, filters)
    sink = SinkData(data)
    print sink.createSortedTableMatrix(2)
