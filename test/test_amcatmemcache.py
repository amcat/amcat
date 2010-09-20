import unittest, amcatmemcache, inspect

class Test: pass

TEST_DATA = ((Test, "headline", 1, "dit is een headline"),
             (Test, "headline", (1,2,3), "dit is een andere headline"),
             (Test, "batches", (1,2,3), [(1, 0.4, "batch1"), (2, 0.2, "batch2")])
             )
             

class TestAmcatMemcache(unittest.TestCase):

    def testSetGet(self):
        for klass, prop, key, data in TEST_DATA:
            amcatmemcache.put(klass, prop, key, data)
            v = amcatmemcache.get(klass, prop, key)
            self.assertEqual(v, data)

    def testPropertyStore(self):
        for klass, prop, key, data in TEST_DATA:
            amcatmemcache.put(klass, prop, key, data)            
            a = amcatmemcache.CachablePropertyStore(klass, prop)
            v2 = a.get(key)
            self.assertEqual(v2, data)

            data2 = ["other", data]
            a.set(key, data2)
            v3 = a.get(key)
            self.assertEqual(v3, data2)

    def testDelete(self):
        for klass, prop, key, data in TEST_DATA:
            a = amcatmemcache.CachablePropertyStore(klass, prop)
            a.set(key, data)            
            self.assertEqual(a.get(key), data)
            a.delete(key)
            self.assertRaises(amcatmemcache.UnknownKeyException, a.get, key)
        

if __name__ == '__main__':
    unittest.main()
