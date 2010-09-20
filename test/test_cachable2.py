import unittest, dbtoolkit
from cachable2 import Cachable, Property, DBProperty, UnknownTypeException

class TestDummy(Cachable):
    prop = Property()
    prop2 = Property()

class TestUser(Cachable):
    __table__ = 'users'
    __idcolumn__ = 'userid'
    username = DBProperty()
    email = DBProperty()
    fullname = DBProperty()
    active = DBProperty()

class TestAmcatMemcache(unittest.TestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)
         
    def testType(self):
        TestDummy.prop.observedType=None
        TestDummy.prop2.observedType=None
        d = TestDummy(self.db, -1)
        d.prop = 1
        d.prop2 = "bla"
        # test observed from explicit get
        dummy = d.prop
        self.assertEqual(TestDummy.prop.getType(), int) 
        self.assertRaises(UnknownTypeException, TestDummy.prop2.getType) 
        # test observed from cache on object
        self.assertEqual(d.getType(TestDummy.prop2), str) 

    def testDBType(self):
        # test get from db
        TestUser.username.observedType=None
        TestUser.active.observedType=None
        u = TestUser(self.db, 2)
        del u.username
        del u.active
        self.assertRaises(UnknownTypeException, TestUser.username.getType)
        self.assertEqual(u.getType(TestUser.username), str)
        self.assertEqual(TestUser.username.getType(), str)

        self.assertRaises(UnknownTypeException, TestUser.active.getType)
        self.assertEqual(u.getType(TestUser.active), bool)

    def testDBProperty(self):
        u = TestUser(self.db, 2)
        self.assertEqual(u.username, 'wva')


    def testProperty(self):
        u = TestDummy(self.db, 4)
        val = 'test'
        # does getting / setting prop work?
        u.prop = val
        self.assertEqual(u.prop, val)

        # are prop values shared by distinct objects with same key?
        u2 = TestDummy(self.db, 4)
        self.assertEqual(u2.prop, val)
        del u.prop
        self.assertRaises(NameError, getattr, u2, 'prop')  # abstract

    def testNonProperty(self):
        # do non-property members work as normal
        u = TestDummy(self.db, 4)
        val = 'nogeentest'        
        u.notaprop = val
        self.assertEqual(u.notaprop, val)

        # are prop values not shared by distinct objects with same key?
        u2 = TestDummy(self.db, 4)
        self.assertRaises(AttributeError, getattr, u2, 'notaprop')
        u2.notaprop = "different"
        self.assertNotEqual(u.notaprop, u2.notaprop)
        
        

if __name__ == '__main__':
    unittest.main()
