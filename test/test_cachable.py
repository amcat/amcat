from amcat.test import amcattest
from amcat.db import dbtoolkit
from amcat.model import language, user, project
from amcat.tools.cachable.cachable import Cachable, Property, DBProperty,DBProperties, UnknownTypeException, ForeignKey
from amcat.tools.cachable.cacher import cache, cacheMultiple
import inspect

class TestDummy(Cachable):
    __idcolumn__ = "DUMMY"
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
    __labelprop__ = 'username'
    username, email, fullname, active = DBProperties(4)
    language = DBProperty(lambda:TestLanguage, getcolumn="languageid")
    roles = ForeignKey(TestRole, table="users_roles")


class Test3(Cachable):
    __idcolumn__ = ['testid', 'id2', 'id3']
    label = DBProperty()
    
class Test2(Cachable):
    __idcolumn__ = ['testid', 'id2']
    __labelprop__ = 'strval'
    strval = DBProperty()
    test3s = ForeignKey(Test3)
class TestChild(Cachable):
    __idcolumn__ = 'pk'
    label = DBProperty()
    test = DBProperty(lambda : Test)
class Test(Cachable):
    __idcolumn__ = 'testid'
    __labelprop__ = 'strval'
    strval, strval2, intval = DBProperties(3)
    testchildren = ForeignKey(TestChild)
    test2s = ForeignKey(Test2)
   
class TestCachable(amcattest.AmcatTestCase):

    def setUp(self):
        super(TestCachable, self).setUp()
        self.createTestTables()
        self.strtype = unicode if self.db.dbType == "psycopg2" else str

    def createTestTables(self):
        t = self.db.createTable("test", [("testid", "serial", "primary key"), ("strval", "varchar(255)", "not null"),
                                         ("strval2","varchar(255)","not null", "default 'test'"), ("intval", "int", "null")], temporary=True)
        t2 = self.db.createTable("test2", [("testid","int"), ("id2", "int"), ("strval", "varchar(255)")], primarykey = ["testid","id2"],temporary=True)
        tc = self.db.createTable("testchild",[("pk","serial","primary key"), ("testid", "int","not null"), ("label", "varchar(255)", "default 'bla'")],temporary=True)
        t3 = self.db.createTable("test3", [("testid","int"), ("id2", "int"), ("id3", "int"), ("label", "varchar(255)")], primarykey = ["testid","id2", "id3"],temporary=True)
        Test.__table__ = t
        Test2.__table__ = t2
        TestChild.__table__ = tc
        Test3.__table__ = t3


    def testType(self):
        TestDummy.prop._observedType=None
        TestDummy.prop2._observedType=None
        d = TestDummy(self.db, -1)
        d.prop = 1
        d.prop2 = "bla"
        # test observed from explicit get
        dummy = d.prop
        self.assertEqual(TestDummy.prop.getType(), int) 
        self.assertRaises(UnknownTypeException, TestDummy.prop2.getType) 
        # test observed from cache on object
        self.assertEqual(d.getType(TestDummy.prop2), str) 

        
    def testGet(self):
        t = Test.create(self.db, strval="x")
        t2 = TestChild.create(self.db, testid=t.id)
        b = t2.test
        self.assertEqual(t, t2.test)
        
    def testCreate(self):
        "test using object as property to create"
        t = Test.create(self.db, strval="bla")
        t2 = TestChild.create(self.db, test=t)
        self.assertEqual(t, t2.test)
        t2 = TestChild.create(self.db, test=t.id)
        self.assertEqual(t, t2.test)


    def testCacheMultiple(self):
        obj = project.Project(self.db, 282)
        props = ["name", "insertUser"]
        val = [getattr(obj, prop) for prop in props]
        obj.uncache()
        cacheMultiple([obj], *props)
        #disable db to make sure that we have values cached
        with self.db.disabled():
            val2= [getattr(obj, prop) for prop in props]
            for v, v2 in zip(val, val2):
                self.assertEqual(v, v2)
                
    def testMulticolFK(self):
        """Test whether retrieving and caching works for multicol foreign keys"""
        t2 = Test2.create(self.db, (1,2), strval="test1")
        child1 = Test3.create(self.db, (1, 2, 3))
        child2 = Test3.create(self.db, (1, 2, 4))
        self.assertEqual(set(t2.test3s), set([child1, child2]))

        t2.uncache()
        cache(t2, "test3s")
        with self.db.disabled():
            self.assertEqual(set(t2.test3s), set([child1, child2]))
        
    def testCacheFK(self):
        """Test wheter caching works on foreignkey properties"""
        t = Test.create(self.db, strval="test1")
        child1 = Test.testchildren.addNewChild(self.db, t)
        child2 = Test.testchildren.addNewChild(self.db, t)
        t.uncache()
        with self.db.disabled():
            self.assertRaises(Exception, lambda : t.testchildren)
        t.uncache()
        cache(t, "testchildren")
        with self.db.disabled():
            children = set(t.testchildren)
            self.assertEqual(children, set([child1, child2]))

    def testFKParentCached(self):
        """Test whether the parent property of an FK child is set automatically"""
        t = Test.create(self.db, strval="test1")
        child = Test.testchildren.addNewChild(self.db, t)
        children =  list(t.testchildren) # force cache
        child.uncache()
        with self.db.disabled():
            # child is uncached, so getting test should raise exception
            self.assertRaises(Exception, lambda : child.test)
            child2 = list(t.testchildren)[0]
            # test should be cached from foreign key
            t2 = child.test
            self.assertEqual(t, t2)

            
        

    def testAdd(self):
        #import amcatlogging; amcatlogging.debugModule("dbtoolkit","amcatmemcache")
        for i, (props, strval, strval2, intval) in enumerate([
                (dict(strval="bla bla"), "bla bla", "test", None),
                (dict(strval="bla bla", intval=15), "bla bla", "test", 15),
                (dict(), dbtoolkit.SQLException, None, None), # exception ruins transaction, so leave at end
                ]):
            with self.db.transaction():
                if inspect.isclass(strval) and issubclass(strval, Exception):
                    self.assertRaises(strval, Test.create, self.db, **props)
                else:
                    t = Test.create(self.db, **props)
                    try:
                        self.assertEqual(t.id, i+1)
                        self.assertEqual(t.strval, strval)
                        self.assertEqual(t.strval2, strval2)
                        self.assertEqual(t.intval, intval)
                    finally:
                        t.uncache()
              
        

    def xtestGetReget(self):
        # getting a property, its cached value, and setting it and regetting it
        # shoule always give the same result
        from amcat.model import project
        obj = project.Project(self.db, 242)
        prop = "name"
        for obj, prop in [
            (project.Project(self.db, 242), "name"),
            (project.Project(self.db, 242), "insertUser"),
            (project.Project(self.db, 242), "insertdate"),
            (project.Project(self.db, 242), "articles"),
            ]:
            try:
                orig = getattr(obj, prop)
                if getattr(orig, '__iter__', False):
                    orig = list(orig)
                obj.uncache()
                uncached = getattr(obj, prop)
                cached = getattr(obj, prop)
                obj.uncache()
                setattr(obj, prop, orig)
                forced = getattr(obj, prop)
                for var in "uncached", "cached", "forced":
                    val = locals()[var]
                    if getattr(val, '__iter__', False):
                        val = list(val)
                    self.assertEqual(orig, val, "Original value %r unequal to %s value %r" % (orig, var, val))
            finally:
                obj.uncache() # to make sure we don't muck things up

    def testForeignKey(self):
        #import amcatlogging; amcatlogging.debugModule("dbtoolkit","amcatmemcache")


        self.assertEqual(TestUser.roles.getType(), TestRole)
        self.assertTrue(TestUser.roles.getCardinality())
        self.assertFalse(TestUser.language.getCardinality())
        self.assertFalse(TestDummy.prop.getCardinality())

        u = TestUser(self.db, 2)
        self.assertTrue(set(u.roles))
        self.assertTrue(TestRole(self.db, 1) in set(u.roles))
        
        u = TestUser(self.db, 5)
        self.assertFalse(set(u.roles))
        
        roles = list(TestRole.all(self.db))
        self.assertTrue(roles)
        self.assertTrue(roles[0].label)

        t = Test.create(self.db, strval="test1")
        t.uncache()
        t2 = TestChild.create(self.db, test=t.id)
        t3 = TestChild.create(self.db, test=t.id)
        self.assertEqual(list(t.testchildren), [t2, t3])
        
    
    def testTypedDBProperty(self):
        TestUser.language.observedType=None
        self.assertEqual(TestUser.language.getType(), TestLanguage)
        u = TestUser(self.db, 2)
        self.assertEqual(type(u.language), TestLanguage)
        self.assertEqual(u.language.label, 'nl')        
        u = TestUser(self.db, 5)
        self.assertEqual(u.language.id, 1)
        
    def testDBType(self):
        # test get from db
        TestUser.username._observedType=None
        TestUser.active._observedType=None
        u = TestUser(self.db, 2)
        del u.username
        del u.active
        self.assertRaises(UnknownTypeException, TestUser.username.getType)
        self.assertEqual(u.getType(TestUser.username), self.strtype)
        self.assertEqual(TestUser.username.getType(), self.strtype)

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
        self.assertRaises(Exception, getattr, u2, 'prop')  # abstract

    def xtestNonProperty(self):
        # Skip this test since we want to use __slots__
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
        

    def testUpdate(self):
        #import amcatlogging; amcatlogging.DEBUG_MODULES.add("amcatmemcache")
        db = dbtoolkit.amcatDB()
        u = user.User(db, 43)
        for name in ('test_123', 'test_456'):
            u.update(db, username=name)
            self.assertEqual(u.username, name)
            del u.username
            self.assertEqual(u.username, name)
        for lang in (1,2):
            l = language.Language(db, lang)
            u.update(db, language=l.id)
            self.assertEqual(u.language, l)
            del u.language
            self.assertEqual(u.language.id, l.id)
            l = language.Language(db, lang+3)
            u.update(db, language=l)
            self.assertEqual(u.language, l)
            del u.language
            self.assertEqual(u.language.id, l.id)
        db.rollback()
        
    def testDelete(self):
        #import amcatlogging; amcatlogging.debugModule("dbtoolkit","amcatmemcache")
        
        t = Test.create(self.db, strval="x")
        self.assertEqual(self.db.getValue("select count(*) from %s" % Test.__table__), 1)
        t.delete(self.db)
        self.assertEqual(self.db.getValue("select count(*) from %s" % Test.__table__), 0)

        self.assertEqual(self.db.getValue("select count(*) from %s" % Test2.__table__), 0)
        t = Test2.create(self.db, idvalues=(1,2))
        self.assertEqual(self.db.getValue("select count(*) from %s" % Test2.__table__), 1)
        t.delete(self.db)
        self.assertEqual(self.db.getValue("select count(*) from %s" % Test2.__table__), 0)

    def testAddFK(self):
        t = Test.create(self.db, strval="test1")
        t.uncache()
        t1 = Test.testchildren.addNewChild(self.db, t)
        t2 = Test.testchildren.addNewChild(self.db, t)
        self.assertEqual(len(list(t.testchildren)), 2)
        self.assertEqual(list(t.testchildren), [t1, t2])
        for c in t1, t2:
            Test.testchildren.removeChild(self.db, t, c)
        self.assertEqual(len(list(t.testchildren)), 0)
        self.assertEqual(list(t.testchildren), [])
        
    def skip_testFindGet(self):
        self.assertEqual(len(TestUser.find(self.db, userid=1)), 1)
        
        t = TestUser(self.db, 1)
        self.assertEqual(t, TestUser.get(self.db, userid=1))        
        
        
if __name__ == '__main__':
    #import amcatlogging; amcatlogging.debugModule("cachable2", "amcatmemcache")
    #t = TestAmcatMemcache('testDelete')
    #t.setUp()
    #t.testAddFK()
    amcattest.main()
