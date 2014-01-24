"Calm cache backend"

import time
import random

from django.core.cache import get_cache
from django.core.cache.backends.base import BaseCache
from django.core.cache.backends.memcached import (BaseMemcachedCache,
                                                  MemcachedCache, PyLibMCCache)
from django.utils.functional import cached_property
from django.conf import settings


class CalmCache(BaseCache):
    """
    Keep your traffic calm by protecting your cache with the CalmCacheBackend

    Supports mint caching and jitter on timeouts

    Example configuration:

        CACHES = {
            'default': {
                'BACKEND' : 'calm_cache.CalmCache',
                'LOCATION': 'my_cache',
            },
            'my_cache': {
                'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
                'LOCATION': 'localhost:11211',
            }

        }
    """

    def __init__(self, real_cache, params):
        super(CalmCache, self).__init__(params)

        mint_delay = params.get('mint_delay', params.get('MINT_DELAY', 0))
        jitter_time = params.get('jitter_time', params.get('JITTER_TIME', 0))

        self.time_func = time.time
        self.rand_func = random.randint
        self.mint_delay = int(mint_delay)
        self.jitter_time = int(jitter_time)

        self.cache = get_cache(real_cache)

    @property
    def is_minted(self):
        return self.mint_delay > 0

    @property
    def has_jitter(self):
        return self.jitter_time > 0

    def jitter(self):
        if not self.has_jitter:
            return 0
        return self.rand_func(0, self.jitter_time)

    def _time(self):
        return self.time_func()

    def _pack_value(self, value, timeout, refreshing=False):
        if not self.is_minted:
            return value
        return (value, self._time() + timeout + self.jitter(), refreshing)

    def _unpack_value(self, value):
        if value is None:
            return None
        if not self.is_minted:
            return (value, 0, True)
        return value

    def _get_real_timeout(self, timeout):
        return timeout + self.mint_delay + self.jitter()

    def add(self, key, value, timeout=None, version=None):
        cache_key = self.make_key(key, version=version)
        timeout = timeout or self.default_timeout
        value = self._pack_value(value, timeout)
        return self.cache.add(cache_key, value, timeout=self._get_real_timeout(timeout), version=version)

    def set(self, key, value, timeout=None, version=None, refreshing=False):
        cache_key = self.make_key(key, version=version)
        timeout = timeout or self.default_timeout
        value = self._pack_value(value, timeout, refreshing=refreshing)
        self.cache.set(cache_key, value, timeout=self._get_real_timeout(timeout), version=version)

    def get(self, key, default=None, version=None):
        cache_key = self.make_key(key, version=version)
        value = self.cache.get(cache_key, default=None, version=version)
        if value is None:
            return default
        value, refresh_time, refreshing = self._unpack_value(value)
        if (self._time() > refresh_time) and not refreshing:
            # Use user-supplied key here, so it will be transformed in set()
            self.set(key, value, timeout=self.mint_delay, version=version, refreshing=True)
            return None
        return value

    def delete(self, key, version=None):
        cache_key = self.make_key(key, version=version)
        self.cache.delete(cache_key, version=version)

    def has_key(self, key, version=None):
        cache_key = self.make_key(key, version=version)
        return self.cache.has_key(cache_key, version=version)

    def clear(self):
        self.cache.clear()


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
