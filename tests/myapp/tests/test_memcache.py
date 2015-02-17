from django.test import TestCase
from django.test.utils import override_settings
from django.utils.unittest import skipUnless
from django.core.cache.backends.memcached import BaseMemcachedCache

from calm_cache.backends.memcached import ZippedMCMixin, BinPyLibMCCache

try:
    import pylibmc as _
except ImportError:
    has_pylibmc = False
else:
    has_pylibmc = True


class FakeLibMC(object):
    """
    A mocking stub memcached library that is able to be used as library
    for BaseMemcachedCache
    """

    class Client(object):
        """
        Records all relevant functions' position and keyword arguments
        """

        def __init__(self, *args, **kwargs):
            self.init_args = args
            self.init_kwargs = kwargs

        def add(self, *args, **kwargs):
            self.add_args = args
            self.add_kwargs = kwargs

        def set(self, *args, **kwargs):
            self.set_args = args
            self.set_kwargs = kwargs

        def set_multi(self, *args, **kwargs):
            self.set_multi_args = args
            self.set_multi_kwargs = kwargs

        def delete(self, *args, **kwargs):
            self.delete_args = args
            self.delete_kwargs = kwargs


class FakeMemcachedCache(BaseMemcachedCache):
    """
    Stub Django cache library that is using `FakeLibMC` as its backend
    """

    def __init__(self, server, params):
        super(FakeMemcachedCache, self).__init__(server, params, FakeLibMC,
                                                 KeyError)


class FakeZipMemcachedCache(ZippedMCMixin, FakeMemcachedCache):
    pass


class MemcacheZipMixinTest(TestCase):

    def test_min_compress_length_kw(self):
        # Check if `min_compress_len` keyword argument is set in every
        # relevant function call
        params = {'OPTIONS': {'MIN_COMPRESS_LEN': 123}}
        cache = FakeZipMemcachedCache('localhost:11211', params)

        cache.add('key-1', 'value-1')
        self.assertEqual(cache._cache.add_kwargs['min_compress_len'], 123)

        cache.set('key-2', 'value-2')
        self.assertEqual(cache._cache.set_kwargs['min_compress_len'], 123)

        cache.set_many({'key-3': 'value-3'})
        self.assertEqual(cache._cache.set_multi_kwargs['min_compress_len'], 123)

    def test_min_compress_length_defaults(self):
        # Check if default min_compress_len is zero and constructor doesn't fail
        cache = FakeZipMemcachedCache('localhost:11211', {})

        cache.add('key-1', 'value-1')
        self.assertEqual(cache._cache.add_kwargs['min_compress_len'], 0)

        cache.set('key-2', 'value-2')
        self.assertEqual(cache._cache.set_kwargs['min_compress_len'], 0)

        cache.set_many({'key-3': 'value-3'})
        self.assertEqual(cache._cache.set_multi_kwargs['min_compress_len'], 0)

    def test_multiple_initialisations(self):
        # Make sure that second instance using the same config dictionary
        # does not get default/absent value because of .pop()'ing
        config = {'OPTIONS': {'MIN_COMPRESS_LEN': 65432}}
        _ = FakeZipMemcachedCache('localhost:11211', config)
        cache = FakeZipMemcachedCache('localhost:11211', config)
        self.assertEqual(cache.min_compress_len, 65432)

class BinPyLibMCCacheTest(TestCase):

    @skipUnless(has_pylibmc, "pylibmc is not present")
    def test_binary_flag_set(self):
        # Check if binary setting has propagated from backend options
        self.cache = BinPyLibMCCache('localhost:11211',
                                     {'OPTIONS': {'BINARY': True}})
        self.assertTrue(self.cache._cache.binary)

    @skipUnless(has_pylibmc, "pylibmc is not present")
    def test_binary_flag_defaults(self):
        # Check if binary setting is not set if 'BINARY' is not among params
        self.cache = BinPyLibMCCache('localhost:11211', {})
        self.assertFalse(self.cache._cache.binary)

    @skipUnless(has_pylibmc, "pylibmc is not present")
    def test_multiple_initialisations(self):
        # Make sure that second instance using the same config dictionary
        # does not get default/absent value because of .pop()'ing
        config = {'OPTIONS': {'BINARY': True}}
        _ = BinPyLibMCCache('localhost:11211', config)
        cache = BinPyLibMCCache('localhost:11211', config)
        self.assertTrue(cache.binary_proto)
