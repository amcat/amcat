from __future__ import absolute_import
from __future__ import unicode_literals
from amcat.tools import amcattest
from amcat.tools.caching import cached, invalidates, cached_named, invalidates_named, reset, \
    set_cache, get_object, clear_cache, get_objects


class TestCaching(amcattest.AmCATTestCase):
    class TestClass(object):
        def __init__(self, x=1, y=2):
            self.changed = False
            self.x = x
            self.y = y

        @property
        @cached
        def xprop(self):
            """Cached property"""
            self.changed = True
            return self.x

        @invalidates
        def set_x(self, x):
            """Invalidating setter"""
            self.x = x
            return x

        @cached_named("y_cache")
        def get_y(self):
            """Func for testing named cache"""
            self.changed = True
            return self.y

        @invalidates_named("y_cache")
        def set_y(self, y):
            """Func for testing invalidate named cache"""
            self.y = y

    def test_cached(self):
        """Does caching work"""
        t = TestCaching.TestClass(x=4)
        self.assertEqual(t.xprop, 4)
        self.assertTrue(t.changed)
        t.changed = False
        self.assertEqual(t.xprop, 4)
        self.assertFalse(t.changed)
        t.x = 7  # manual change, does not invalidate cache
        self.assertEqual(t.xprop, 4)
        self.assertFalse(t.changed)

    def test_invalidate(self):
        """Does invalidate work properly"""
        t = TestCaching.TestClass(x=4)
        self.assertEqual(t.xprop, 4)
        t.changed = False
        x = t.set_x(12)
        self.assertEqual(x, 12, "Cached method does not return value")
        self.assertEqual(t.xprop, 12)
        self.assertTrue(t.changed)

    def test_reset(self):
        """Does manual reset work properly"""
        t = TestCaching.TestClass(x=4)
        self.assertEqual(t.xprop, 4)
        t.changed = False
        t.x = 17
        self.assertEqual(t.xprop, 4)
        self.assertFalse(t.changed)
        reset(t)
        self.assertEqual(t.xprop, 17)
        self.assertTrue(t.changed)

    def test_named(self):
        """Do named caches work?"""
        t = TestCaching.TestClass(x=4)
        y = t.get_y()

        # Setting the x prop should _not_ invalidate the cache for y
        t.changed = False
        t.set_x(17)
        self.assertEqual(y, t.get_y())
        self.assertFalse(t.changed)

        # Setting the y prop should _not_ invalidate the cache for x
        x = t.xprop
        t.changed = False
        t.set_y(1)
        self.assertEqual(x, t.xprop)
        self.assertFalse(t.changed)

        # ... but it should invalidate the cache for y
        self.assertEqual(t.get_y(), 1)
        self.assertTrue(t.changed)

        # ... and so should calling named reset
        t.changed = False
        t.y = 9
        reset(t, "y_cache")
        self.assertEqual(x, t.xprop)
        self.assertFalse(t.changed)
        self.assertEqual(t.get_y(), 9)
        self.assertTrue(t.changed)

    def test_set_cache(self):
        """Can we manually set the cache?"""
        t = TestCaching.TestClass(x=4, y=1)

        # Are set values used?
        set_cache(t, "xprop", 99)
        self.assertEqual(t.xprop, 99)
        self.assertFalse(t.changed)
        # Does reset bring back real value?
        reset(t)
        self.assertEqual(t.xprop, 4)
        self.assertTrue(t.changed)

        # Same for named prop
        t.changed = False
        set_cache(t, t.get_y.__name__, 7, "y_cache")
        self.assertEqual(t.get_y(), 7)
        self.assertFalse(t.changed)
        reset(t, "y_cache")
        self.assertEqual(t.get_y(), 1)
        self.assertTrue(t.changed)

    def test_object_cache(self):
        from amcat.models.project import Project

        pid = amcattest.create_test_project().id
        with self.checkMaxQueries(1, "Get project"):
            p = get_object(Project, pid)
        with self.checkMaxQueries(1, "Get cached project"):
            p2 = get_object(Project, pid)
        self.assertIs(p, p2)

        clear_cache(Project)
        with self.checkMaxQueries(1, "Get cleared project"):
            p3 = get_object(Project, pid)
        self.assertIsNot(p, p3)
        self.assertEqual(p, p3)

    def test_get_objects(self):
        from amcat.models.project import Project

        pids = [amcattest.create_test_project().id for _x in range(10)]

        with self.checkMaxQueries(1, "Get multiple projects"):
            ps = list(get_objects(Project, pids))

        with self.checkMaxQueries(0, "Get multiple cached projects"):
            ps = list(get_objects(Project, pids))

        with self.checkMaxQueries(0, "Get multiple cached projects one by one"):
            ps = [get_objects(Project, pid) for pid in pids]