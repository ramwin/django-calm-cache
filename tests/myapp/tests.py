"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import hashlib

from django.test import TestCase
from django.core.cache import cache, get_cache

from calm_cache.contrib import sha1_key_func

testcache = get_cache('testcache')

class CalmCacheTest(TestCase):

    def setUp(self):
        self._time_func = cache.time_func
        self._rand_func = cache.rand_func
        cache.time_func = lambda: 1
        cache.rand_func = lambda x,y: 2

    def tearDown(self):
        cache.time_func = self._time_func
        cache.rand_func = self._rand_func

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
        # travel forward in time
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


class KeyFuncTest(TestCase):

    def setUp(self):
        self._key_func = testcache.key_func

    def tearDown(self):
        testcache.key_func = self._key_func

    def test_sha1_key_func(self):
        # Resulting key should contain hashed part
        key = sha1_key_func('original key value', 'prefix', 'v1')
        self.assertEqual(key,
                         'prefix:v1:905d4140b8d64409c84b8c442d26707be9f95df2')
        # Stored key should be less that memcached max length of 250b
        key = sha1_key_func('z'*1024, 'prefix', 'v1')
        self.assertLess(len(key), 250)

    def test_sha1_key_func_cache(self):
        plain_key = 'test-key-10'
        hashed_key = hashlib.sha1(plain_key).hexdigest()
        # Store with pre-hashed key, replace
        # key function and fetch with plain key
        testcache.set(hashed_key, 'test-value-10', timeout=60)
        testcache.key_func = sha1_key_func
        self.assertEqual(testcache.get(plain_key), 'test-value-10')
