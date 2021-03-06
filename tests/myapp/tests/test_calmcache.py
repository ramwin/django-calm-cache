"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.test import TestCase
from django.core.cache import cache, caches

testcache = caches['testcache']

class CalmCacheTest(TestCase):

    def setUp(self):
        self._time_func = cache.time_func
        self._rand_func = cache.rand_func
        cache.time_func = lambda: 1
        cache.rand_func = lambda x,y: 2

    def tearDown(self):
        cache.time_func = self._time_func
        cache.rand_func = self._rand_func
        cache.clear()
        testcache.clear()

    def test_set(self):
        cache.set('test-key-1', 'test-value-1', timeout=60)
        r = testcache.get(cache.make_key('test-key-1'))
        self.assertEqual(r, ('test-value-1', 63, False))

    def test_get(self):
        cache.set('test-key-2', 'test-value-2', timeout=60)
        r = cache.get('test-key-2')
        self.assertEqual(r, 'test-value-2')

    def test_get_nonexist(self):
        r = cache.get('non-existant-key')
        self.assertIsNone(r)

    def test_add_nonexist(self):
        r = cache.add('test-key-3', 'test-value-3', timeout=60)
        self.assertTrue(r)
        r = cache.get('test-key-3')
        self.assertEqual(r, 'test-value-3')

    def test_add_preexist(self):
        cache.set('test-key-5', 'test-value-5', timeout=60)
        r = cache.add('test-key-5', 'test-value-5a', timeout=60)
        self.assertFalse(r)
        r = cache.get('test-key-5')
        self.assertEqual(r, 'test-value-5')

    def test_mint_unfresh(self):
        cache.set('test-key-4', 'test-value-4', timeout=60)
        # make sure the key actually exists
        r = cache.get('test-key-4')
        self.assertEqual(r, 'test-value-4')
        # travel forward in time: timeout + jitter + d, where d < mint_period
        cache.time_func = lambda: 65
        # key should miss
        r = cache.get('test-key-4')
        self.assertIsNone(r)
        # key should get because we're now refreshing
        r = cache.get('test-key-4')
        self.assertEqual(r, 'test-value-4')
        # introspect the inner cache to make sure
        r = testcache.get(cache.make_key('test-key-4'))
        self.assertEqual(r, ('test-value-4', 77, True))

    def test_grace_unfresh(self):
        cache.set('test-key-6', 'test-value-6', timeout=60)
        # travel forward in time: timeout + jitter + mint_period + d,
        # where d < grace_period
        cache.time_func = lambda: 75
        # key should return stale value
        r = cache.get('test-key-6')
        self.assertEqual(r, 'test-value-6')
        # Shuold miss because last fetch invalidated the key
        r = cache.get('test-key-6')
        self.assertIsNone(r)
        # make sure the value was removed from the underlying cache
        r = testcache.get(cache.make_key('test-key-6'))
        self.assertIsNone(r)
