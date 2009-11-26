import xapian, amcatxapian, dbtoolkit, toolkit


class XapianHitsSource(DataSource):
    def __init__(self, db):
        DataSource.__init__(self, self.createMappings())
        
        
