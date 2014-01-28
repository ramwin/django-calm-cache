
from django.test import TestCase
from django.utils.unittest import skipUnless
from django.core.cache.backends.memcached import BaseMemcachedCache

from calm_cache.backends.memcached import ZippedMCMixin, BinPyLibMCCache

try:
    import pylibmc as _
except:
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

    def setUp(self):
        params = {'MIN_COMPRESS_LEN': 123}
        self.cache = FakeZipMemcachedCache('localhost:11211', params)

    def test_min_compress_length_kw(self):
        # Check if `min_compress_len` keyword argument is set in every
        # relevant function call
        self.cache.add('key-1', 'value-1')
        self.assertEqual(self.cache._cache.add_kwargs['min_compress_len'], 123)

        self.cache.set('key-2', 'value-2')
        self.assertEqual(self.cache._cache.set_kwargs['min_compress_len'], 123)

        self.cache.set_many({'key-3': 'value-3'})
        self.assertEqual(
            self.cache._cache.set_multi_kwargs['min_compress_len'], 123)


class BinPyLibMCCacheTest(TestCase):

    def setUp(self):
        params = {'BINARY': True}
        self.cache = BinPyLibMCCache('localhost:11211', params)

    @skipUnless(has_pylibmc, "pylibmc is not present")
    def test_binary_flag_set(self):
        # Check if binary setting has propagated from backend options
        self.assertTrue(self.cache._cache.binary)
