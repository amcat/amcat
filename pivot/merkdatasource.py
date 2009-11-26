import xapian, dbtoolkit, toolkit
from datasource import DataSource, Mapping, Field
from itertools import imap, izip

class MerkDataSource(DataSource):
    def __init__(self, db):
        DataSource.__init__(self,self.createMappings())
        self.db = db

    def createMappings(self):
        article = MerkDataField(self, "article",["articles"],"articleid")
##??        merk = MerkDataField(self, "Merk",["merken"],"merkid")

        return [
            MerkDataMapping(article, merk),
            }

class MerkDataField(Field):
    def __init__(self, datasource, concept, tables, column):
        Field.__init__(self, datasource, concept)
        self.tables = tables
        self.column = column
