# Calm Cache for Django

`django-calm-cache` keeps your cache calm while your site is being hammered by
bucket loads of traffic.

## Key Features

 * [Mint caching](http://djangosnippets.org/snippets/155/) to avoid the
   [dog pile](http://en.wikipedia.org/wiki/Cache_stampede) effect
 * Timeout jitter to reduce the number of entries expiring simultaneously
 * Works alongside any other Django cache backend
 * `MemcachedCache` and `PyLibMCCache` Django backends are extended to support
   data compression provided by [python-memcached](ftp://ftp.tummy.com/pub/python-memcached/)
   and [pylibmc](http://sendapatch.se/projects/pylibmc/) respectively
 * `PyLibMCCache` is extended to support binary protocol
 * `PageCacheDecorator` that could be applied to any Django view and
   conditionally cache responses just like Django standard `CacheMiddleware`
   and `cache_page` do, but more configurable, explicit and extensible

## Quick Start

First install the library:

    pip install hg+https://bitbucket.org/pitcrews/django-calm-cache/

### Cache backends

Update the cache settings in your `settings.py`:

    :::python
    CACHES = {
        'default': {
            'BACKEND' : 'calm_cache.backends.CalmCache',
            'LOCATION': 'locmem-cache',
            'MINT_DELAY': '10', # Allow stale results for this many seconds. Default: 0 (Off)
            'JITTER_TIME': '10', # Upper bound on the random jitter in seconds. Default: 0 (Off)
        },
        'locmem-cache': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'foo',
        },
        'zipped-memcached': {
            'BACKEND': 'calm_cache.backends.MemcachedCache',
            'LOCATION': '127.0.0.1:11211',
            'MIN_COMPRESS_LEN': 1024, # Compress values of this size or larger, bytes
        },
        'zipped-bin-pylibmc': {
            'BACKEND': 'calm_cache.backends.PyLibMCCache',
            'LOCATION': '127.0.0.1:11211',
            'MIN_COMPRESS_LEN': 1024, # Compress values larger than this size, bytes
            'BINARY': True, # Enable binary protocol for this backend
        },
    }

Now relax knowing your site's caching won't fall over at the first sign of sustained traffic.

### Page Cache

Example usage:

    :::python
    from calm_cache.decorated import PageCacheDecorator

    @PageCacheDecorator(15, key_prefix='my_view', codes=(200, 404)):
    def my_view(request, slug=None):
        return HttpResponse()

`PageCacheDecorator`'s constructor arguments:

 * `cache_timeout`: integer, default TTL for cached entries. Required
 * `cache`: Django cache backend name. If not specified, default cache
   backend will be used
 * `key_prefix`: this sting is always prepending resulting keys
 * `methods`: a list/tuple with request methods that could be cached.
   Default: `('GET', )`
 * `codes`: a list/tuple with cacheable response codes. Default: `(200, )`
 * `anonymous_only`: boolean selecting whether only anonmous requests
   should be served from the cache/responses cached. Default: `True`
 * `consider_scheme`: boolean selecting whether request scheme (http
   or https) should be used for the key. Default: `True`
 * `consider_host`: boolean selecting whether requested Host: should
   be used for the key. Default: `True`
 * `key_function`: optional callable that should be used instead of
   built-in key function.
   Has to accept request as its only argument and return either
   a string with the key or `None` if the request should not be cached.

## Known Limitations

 * `CalmCache` currently only supports cache methods `add`, `set`, `get`, `delete`,
   `has_key` and `clear`
 * Unlike `CacheMiddleware`, `PageCacheDecorator` does not respect `Vary:`
   header returned from the view
 * `PageCacheDecorator` does not respect `Cache-Control:` and `Pragma:` headers
   in requests
 * `PageCacheDecorator` does not check `Set-Cookie:` header in responses and
   neither removes it before caching nor skips caching at all. Please be warned

## Legals

License: BSD 3-clause

Copyright (c) 2014, Fairfax Media Limited
All rights reserved.
