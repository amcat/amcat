import unittest, dbtoolkit
from cachable2 import Cachable, Property, DBProperty,DBProperties, UnknownTypeException, ForeignKey

class TestDummy(Cachable):
    prop = Property()
    prop2 = Property()

class TestLanguage(Cachable):
    __table__ = 'languages'
    __idcolumn__ = 'languageid'
    label = DBProperty()
    
class TestRole(Cachable):
    __table__ = 'roles'
    __idcolumn__ = 'roleid'
    label = DBProperty()
    
class TestUser(Cachable):
    __table__ = 'users'
    __idcolumn__ = 'userid'
    username, email, fullname, active = DBProperties(4)
    language = DBProperty(lambda : TestLanguage, getcolumn="language")
    roles = ForeignKey(TestRole, table="users_roles")

class TestAmcatMemcache(unittest.TestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)

    def testForeignKey(self):
        self.assertEqual(TestUser.roles.getType(), TestRole)
        self.assertTrue(TestUser.roles.getCardinality())
        self.assertFalse(TestUser.language.getCardinality())
        self.assertFalse(TestDummy.prop.getCardinality())

        u = TestUser(self.db, 2)
        self.assertTrue(set(u.roles))
        self.assertTrue(TestRole(self.db, 1) in set(u.roles))
        
        u = TestUser(self.db, 5)
        self.assertFalse(set(u.roles))
        
        roles = list(TestRole.getAll(self.db))
        self.assertTrue(roles)
        self.assertTrue(roles[0].label)
        
        
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

    def testTypedDBProperty(self):
        TestUser.language.observedType=None
        self.assertEqual(TestUser.language.getType(), TestLanguage)
        u = TestUser(self.db, 2)
        self.assertEqual(type(u.language), TestLanguage)
        self.assertEqual(u.language.label, 'nl')        
        u = TestUser(self.db, 5)
        self.assertEqual(u.language, None)
        
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
    
    #TestDummy.prop.observedType=None
    #d = TestDummy([], -1)
    #d.prop = 1
    #dummy = d.prop
    #print dummy
    #print TestDummy.prop.getType()
    #db = dbtoolkit.amcatDB(use_app=True)
    #u = TestUser(db, 2)
    #print u.roles
    #del u.language
    
    #print repr(u.language)
    unittest.main()
