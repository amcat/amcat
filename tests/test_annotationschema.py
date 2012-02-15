from amcat.test import amcattest

from amcat.models.coding.annotationschema import AnnotationSchema
from amcat.models.project import Project

from amcat.tools import idlabel
from amcat.db import dbtoolkit


class TestAnnotationSchema(amcattest.AmcatTestCase):

    def testCreate(self):
        p = Project()
        p.save()
        
        s = AnnotationSchema()
        s.project = p
        s.save()

        print("Hallo")
            
    
if __name__ == '__main__':
    amcattest.main()
