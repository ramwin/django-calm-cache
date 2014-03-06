from django.core.cache.backends.memcached import (
    BaseMemcachedCache,
    MemcachedCache as DjangoMemcachedCache,
    PyLibMCCache as DjangoPyLibMCCache)
from django.utils.functional import cached_property, curry
from django.conf import settings


class ZippedMCMixin(object):
    """
    Mixin class for `MemcachedCache` or `PyLibMCCache` adding support for
    compression that is available in both `memcache` and `pylibmc`.

    Minimal size of the object that will be compressed (bytes) is set either as
    `MIN_COMPRESS_LEN` among backend options or as Django setting
    `MEMCACHE_MIN_COMPRESS_LEN`.
    """

    min_compress_len = getattr(settings, 'MEMCACHE_MIN_COMPRESS_LEN', 0)

    def __init__(self, server, params):
        super(ZippedMCMixin, self).__init__(server, params)
        if self._options is not None:
            self._options = self._options.copy()
            self.min_compress_len = self._options.pop('MIN_COMPRESS_LEN',
                                                      self.min_compress_len)

    @cached_property
    def _cache(self):
        cache = super(ZippedMCMixin, self)._cache
        # Decorate methods so that min_compress_len is always added
        cache.add = curry(cache.add, min_compress_len=self.min_compress_len)
        cache.set = curry(cache.set, min_compress_len=self.min_compress_len)
        cache.set_multi = curry(
            cache.set_multi, min_compress_len=self.min_compress_len)
        return cache


class BinPyLibMCCache(DjangoPyLibMCCache):
    """
    Extend standard `PyLibMCCache` to support binary protocol.

    It can be enabled either by setting `BINARY: True` among backend
    options or globally as Django setting `MEMCACHE_BINARY = True`
    """

    binary_proto = getattr(settings, 'MEMCACHE_BINARY', False)

    def __init__(self, server, params):
        super(BinPyLibMCCache, self).__init__(server, params)
        if self._options is not None:
            self._options = self._options.copy()
            self.binary_proto = self._options.pop('BINARY', self.binary_proto)

    @cached_property
    def _cache(self):
        cache = self._lib.Client(self._servers, binary=self.binary_proto)
        if self._options is not None:
            cache.behaviors = self._options
        return cache


class MemcachedCache(ZippedMCMixin, DjangoMemcachedCache):
    """
    An extension of standard `django.cache.backends.MemcachedCache`
    supporting optional compression of stored values

    Example configuration:

        CACHES = {
            'default': {
                'BACKEND': 'calm_cache.backends.MemcachedCache',
                'LOCATION': '127.0.0.1:11211',
                'OPTIONS': {
                    'MIN_COMPRESS_LEN': 1024,
                },
            },
        }
    """
    pass


class PyLibMCCache(ZippedMCMixin, BinPyLibMCCache):
    """
    An extension of standard `django.cache.backends.PyLibMCCache`
    supporting optional compression of stored values and optional binary
    memcached protocol

    Example configuration:

        CACHES = {
            'default': {
                'BACKEND': 'calm_cache.backends.PyLibMCCache',
                'LOCATION': '127.0.0.1:11211',
                'OPTIONS': {
                    'MIN_COMPRESS_LEN': 1024,
                    'BINARY': True,
                },
            },
        }
    """
    pass
