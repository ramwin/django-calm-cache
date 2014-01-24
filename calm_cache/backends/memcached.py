from django.core.cache.backends.memcached import (BaseMemcachedCache,
                                                  MemcachedCache, PyLibMCCache)
from django.utils.functional import cached_property
from django.conf import settings


def set_compress_len(func, min_compress_len):
    """
    This is a decorator for `memcache.Client` and `pylibmc.Clients`
    methods that support `min_compress_len` argument
    """
    def wrapped(*args, **kwargs):
        kwargs['min_compress_len'] = min_compress_len
        return func(*args, **kwargs)
    return wrapped


class ZippedMCMixin(object):
    """
    Mixin class for `MemcachedCache` or `PyLibMCCache` adding support for
    compression that is available in both `memcache` and `pylibmc`.

    Minimal size of the object that will be compressed (bytes) is set either as
    `MIN_COMPRESS_LEN` option amond backend options or as Django setting
    `MEMCACHE_MIN_COMPRESS_LEN`.
    """

    def __init__(self, server, params):
        self.min_compress_len = params.pop(
            'MIN_COMPRESS_LEN',
            getattr(settings, 'MEMCACHE_MIN_COMPRESS_LEN', 0))
        super(ZippedMCMixin, self).__init__(server, params)

    @cached_property
    def _cache(self):
        cache = super(ZippedMCMixin, self)._cache
        # Decorate methods so that min_compress_len is always added
        cache.add = set_compress_len(cache.add, self.min_compress_len)
        cache.set = set_compress_len(cache.set, self.min_compress_len)
        cache.set_multi = set_compress_len(cache.set_multi,
                                           self.min_compress_len)
        return cache


class BinPyLibMCCache(PyLibMCCache):
    """
    Extend standard `PyLibMCCache` to support binary protocol.

    It can be enabled either by setting `BINARY: True` among backend
    options or globally as Django setting `MEMCACHE_BINARY = True`
    """

    def __init__(self, server, params):
        self.binary_proto = params.pop(
            'BINARY', getattr(settings, 'MEMCACHE_BINARY', False))
        super(BinPyLibMCCache, self).__init__(server, params)


    # Shamelessly copied from django.cache.backends.PyLibMCCache
    @cached_property
    def _cache(self):
        client = self._lib.Client(self._servers, binary=self.binary_proto)
        if self._options:
            client.behaviors = self._options

        return client


class ZipMemcachedCache(ZippedMCMixin, MemcachedCache):
    """
    An extension of standard `django.cache.backends.MemcachedCache`
    supporting optional compression of stored values

    Example configuration:

        CACHES = {
            'default': {
                'BACKEND': 'calm_cache.backends.ZipMemcachedCache',
                'LOCATION': '127.0.0.1:11211',
                'MIN_COMPRESS_LEN': 1024,
            },
        }
    """
    pass


class ZipPyLibMCCache(ZippedMCMixin, BinPyLibMCCache):
    """
    An extension of standard `django.cache.backends.PyLibMCCache`
    supporting optional compression of stored values and optional binary
    memcached protocol

    Example configuration:

        CACHES = {
            'default': {
                'BACKEND': 'calm_cache.backends.ZipPyLibMCCache',
                'LOCATION': '127.0.0.1:11211',
                'MIN_COMPRESS_LEN': 1024,
                'BINARY': True,
            },
        }
    """
    pass
