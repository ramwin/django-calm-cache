import hashlib

from django.test import TestCase
from django.core.cache import cache, get_cache

from calm_cache.contrib import sha1_key_func


class KeyFuncTest(TestCase):

    def setUp(self):
        self._key_func = cache.key_func

    def tearDown(self):
        cache.key_func = self._key_func

    def test_sha1_key_func(self):
        # Resulting key should contain hashed part
        key = sha1_key_func('original key value', 'prefix', 'v1')
        self.assertEqual(key,
                         'prefix:v1:905d4140b8d64409c84b8c442d26707be9f95df2')
        # Stored key should be less that memcached max length of 250b
        key = sha1_key_func('z'*1024, 'prefix', 'v1')
        self.assertLess(len(key), 250)

    def test_sha1_key_func_utf8(self):
        # Resulting key should contain hashed part
        # It's the word "Russian" in, well, Russian
        key = sha1_key_func(
            b'\xd1\x80\xd1\x83\xd1\x81\xd1\x81\xd0\xba\xd0\xb8\xd0\xb9',
            'prefix', 'v1')
        self.assertEqual(key,
                         'prefix:v1:10c8e649725ee2829541600cf8528d91306c5aaa')
        # Stored key should be less that memcached max length of 250b
        key = sha1_key_func('z'*1024, 'prefix', 'v1')
        self.assertLess(len(key), 250)

    def test_sha1_key_func_unicode(self):
        # Resulting key should contain hashed part
        # It's the word "Russian" in, well, Russian
        key = sha1_key_func(
            u'\u0440\u0443\u0441\u0441\u043a\u0438\u0439',
            'prefix', 'v1')
        self.assertEqual(key,
                         'prefix:v1:10c8e649725ee2829541600cf8528d91306c5aaa')
        # Stored key should be less that memcached max length of 250b
        key = sha1_key_func('z'*1024, 'prefix', 'v1')
        self.assertLess(len(key), 250)

    def test_sha1_key_func_cache(self):
        plain_key = b'test-key-10'
        hashed_key = hashlib.sha1(plain_key).hexdigest()
        # Store with pre-hashed key, replace
        # key function and fetch with plain key
        cache.set(hashed_key, 'test-value-10', timeout=60)
        cache.key_func = sha1_key_func
        self.assertEqual(cache.get(plain_key), 'test-value-10')
