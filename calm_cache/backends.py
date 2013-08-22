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
        timeout = timeout or self.default_timeout
        value = self._pack_value(value, timeout)
        return self.cache.add(key, value, timeout=self._get_real_timeout(timeout), version=version)

    def set(self, key, value, timeout=None, version=None, refreshing=False):
        timeout = timeout or self.default_timeout
        value = self._pack_value(value, timeout, refreshing=refreshing)
        self.cache.set(key, value, timeout=self._get_real_timeout(timeout), version=version)

    def get(self, key, default=None, version=None):
        value = self.cache.get(key, default=None, version=version)
        if value is None:
            return default
        value, refresh_time, refreshing = self._unpack_value(value)
        if (self._time() > refresh_time) and not refreshing:
            self.set(key, value, timeout=self.mint_delay, version=version, refreshing=True)
            return None
        return value

    def delete(self, key, version=None):
        self.cache.delete(key, version=version)

    def has_key(self, key, version=None):
        return self.cache.has_key(key, version=version)

    def clear(self):
        self.cache.clear()
