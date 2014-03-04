"Calm cache backend"

import time
import random

from django.core.cache import get_cache
from django.core.cache.backends.base import BaseCache


class CalmCache(BaseCache):
    """
    Keep your traffic calm by protecting your cache with the CalmCacheBackend

    Supports mint caching and jitter on timeouts

    Example configuration:

        CACHES = {
            'default': {
                'BACKEND' : 'calm_cache.backends.CalmCache',
                'LOCATION': 'my_cache',
                'OPTIONS': {
                    'MINT_PERIOD': 10,
                    'GRACE_PERIOD': 120,
                    'JITTER': 10,
                }
            },
            'my_cache': {
                'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
                'LOCATION': 'localhost:11211',
            }

        }
    """

    def __init__(self, real_cache, params):
        super(CalmCache, self).__init__(params)

        options = params.get('OPTIONS', {})
        self.mint_period = int(options.get('MINT_PERIOD', 0))
        self.grace_period = int(options.get('GRACE_PERIOD', 0))
        self.jitter = int(options.get('JITTER', 0))

        self.time_func = time.time
        self.rand_func = random.randint

        self.cache = get_cache(real_cache)

    @property
    def packing_enabled(self):
        return self.mint_period > 0 or self.grace_period > 0

    @property
    def has_jitter(self):
        return self.jitter > 0

    def get_jitter(self):
        if not self.has_jitter:
            return 0
        return self.rand_func(0, self.jitter)

    def _time(self):
        return self.time_func()

    def _pack_value(self, value, timeout, refreshing=False):
        if not self.packing_enabled:
            return value
        return (value, self._time() + timeout + self.get_jitter(), refreshing)

    def _unpack_value(self, value):
        if value is None:
            return None
        if not self.packing_enabled:
            return (value, 0, True)
        return value

    def _get_real_timeout(self, timeout):
        return timeout + self.mint_period + self.grace_period + self.get_jitter()

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
        now = self._time()
        if now > (refresh_time + self.mint_period):
            # We are beyond minting period, remove the object and return stale
            self.cache.delete(cache_key)
            return value
        if (now > refresh_time) and not refreshing:
            # We are in the mint period, allow serving stale while revalidating
            # Use user-supplied key here, so it will be transformed in set()
            self.set(key, value, timeout=self.mint_period, version=version, refreshing=True)
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
