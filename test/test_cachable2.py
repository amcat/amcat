import amcattest, dbtoolkit, user, language, inspect
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
    __labelprop__ = 'username'
    username, email, fullname, active = DBProperties(4)
    language = DBProperty(lambda : TestLanguage, getcolumn="languageid")
    roles = ForeignKey(TestRole, table="users_roles")

        
class Test(Cachable):
    __table__ = '#test'
    __idcolumn__ = 'id'
    strval, strval2, intval = DBProperties(3)
class Test2(Cachable):
    __table__ = '#test2'
    __idcolumn__ = ['id', 'id2']
    strval = DBProperty()
    
class TestAmcatMemcache(amcattest.AmcatTestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)
        self.createTestTables()

    def createTestTables(self):
        self.db.doQuery("create table #test (id int identity(1,1) primary key, strval varchar(255) not null, strval2 varchar(255) not null default 'test', intval int null)")
        self.db.doQuery("create table #test2 (id int, id2 int, strval varchar(255), primary key (id, id2))")

    def tearDown(self):
        self.db.rollback()
        
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
        
    def testAdd(self):
        #import amcatlogging; amcatlogging.DEBUG_MODULES.add("dbtoolkit")
        #amcatlogging.DEBUG_MODULES.add("amcatmemcache")
        for i, (props, strval, strval2, intval) in enumerate([
                (dict(), dbtoolkit.SQLException, None, None),
                (dict(strval="bla bla"), "bla bla", "test", None),
                (dict(strval="bla bla", intval=user.User(self.db, 15)), "bla bla", "test", user.User(self.db, 15)),
                ]):
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
        
    def testDelete(self):
        import amcatlogging; amcatlogging.DEBUG_MODULES.add("dbtoolkit")
        amcatlogging.DEBUG_MODULES.add("amcatmemcache")
        
        t = Test.create(self.db, strval="x")
        self.assertEqual(self.db.getValue("select count(*) from #test"), 1)
        t.delete(self.db)
        self.assertEqual(self.db.getValue("select count(*) from #test"), 0)

        self.assertEqual(self.db.getValue("select count(*) from #test2"), 0)
        t = Test2.create(self.db, idvalues=(1,2))
        self.assertEqual(self.db.getValue("select count(*) from #test2"), 1)
        t.delete(self.db)
        self.assertEqual(self.db.getValue("select count(*) from #test2"), 0)
        
if __name__ == '__main__':
    #TestAmcatMemcache().testAdd()
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
    amcattest.main()
