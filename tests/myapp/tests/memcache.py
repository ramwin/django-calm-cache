from django.test import TestCase
from django.core.cache.backends.memcached import BaseMemcachedCache

from calm_cache.backends.memcached import ZippedMCMixin



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
        options = {'MIN_COMPRESS_LEN': 123}
        self.cache = FakeZipMemcachedCache('localhost:11211', options)

    def test_min_compress_length_kw(self):
        self.cache.add('key-1', 'value-1')
        self.assertEqual(self.cache._cache.add_kwargs['min_compress_len'], 123)

        self.cache.set('key-2', 'value-2')
        self.assertEqual(self.cache._cache.set_kwargs['min_compress_len'], 123)

        self.cache.set_many({'key-3': 'value-3'})
        self.assertEqual(
            self.cache._cache.set_multi_kwargs['min_compress_len'], 123)
