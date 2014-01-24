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


class ZipMemcachedCache(ZippedMCMixin, MemcachedCache):
    pass


class ZipPyLibMCCache(ZippedMCMixin, PyLibMCCache):
    pass
