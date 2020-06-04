# Calm Cache for Django

`django-calm-cache` keeps your cache calm while your site is being hammered by
bucket loads of traffic.

this project is forked from [pitcrews:django-calm-cache](https://bitbucket.org/pitcrews/django-calm-cache/).  
Thanks for all the contributors.  
But the origin project can't be used in new verion of django.  
And it seems the author didn't update the package in pypi.  
So I forked and update the django3-calm-cache repository

## Key Features

 * [Mint caching](http://djangosnippets.org/snippets/155/) to avoid the
   [dog pile](http://en.wikipedia.org/wiki/Cache_stampede) effect
 * Timeout jitter to reduce the number of entries expiring simultaneously
 * Works alongside any other Django cache backend
 * `MemcachedCache` and `PyLibMCCache` Django backends are extended to support
   data compression provided by [python-memcached](ftp://ftp.tummy.com/pub/python-memcached/)
   and [pylibmc](http://sendapatch.se/projects/pylibmc/) respectively
 * `PyLibMCCache` is extended to support binary protocol
 * `cache_response` decorator that could be applied to any Django view and
   conditionally cache responses just like Django standard `CacheMiddleware`
   and `cache_page` do, but more configurable, explicit and extensible

## Installation

    :::shell
    pip3 install django3-calm-cache


### Cache Backends

Update the cache settings in your `settings.py`:

    :::python
    CACHES = {
        'default': {
            'BACKEND' : 'calm_cache.backends.CalmCache',
            'LOCATION': 'locmem-cache',
            'KEY_FUNCTION': 'calm_cache.contrib.sha1_key_func',
            'OPTIONS': {
                'MINT_PERIOD': '10', # Allow stale results for this many seconds. Default: 0 (Off)
                'GRACE_PERIOD': '120', # Serve stale value once during this period. Default: 0 (Off)
                'JITTER': '10', # Upper bound on the random jitter in seconds. Default: 0 (Off)
            },
        },
        'locmem-cache': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'foo',
        },
        'zipped-memcached': {
            'BACKEND': 'calm_cache.backends.MemcachedCache',
            'LOCATION': '127.0.0.1:11211',
            'OPTIONS': {
                'MIN_COMPRESS_LEN': 1024, # Compress values of this size or larger, bytes. Default: 0 (Disabled)
            },
        },
        'zipped-bin-pylibmc': {
            'BACKEND': 'calm_cache.backends.PyLibMCCache',
            'LOCATION': '127.0.0.1:11211',
            'OPTIONS': {
                'MIN_COMPRESS_LEN': 1024, # Compress values of this size or larger, bytes. Default: 0 (Disabled)
                'BINARY': True, # Enable binary protocol for this backend. Default: False (Disabled)
            },
        },
    }

Now relax knowing your site's caching won't fall over at the first sign of sustained traffic.

#### CalmCache Configuration


`LOCATION` parameter defines the name of another, "real", Django cache backend
which will be used to actually store values

`CalmCache` backend accepts the following options:

 * `MINT_PERIOD`: the time period that starts right after the user-supplied
   or default timeout (`TIMEOUT` setting) ends.
   First request during this period receives get() miss (`None` or default) and
   refreshes the value while all other requests are returning cached (stale)
   value until it is either updated or expired. Seconds. Default: `0`
 * `GRACE_PERIOD`: the time period starting after mint delay.
   During grace period stale value is returned only once and is removed after that.
   Seconds. Default: `0`
 * `JITTER`: defines the range for `[0 ... JITTER]` random value
   that is added to client supplied and "real" cache timeouts. Seconds. Default: `0`


#### CalmCache Guidelines

Actual stored key names are composed of `CalmCache.make_key()`
and underlying cache's `make_key()` methods' outputs, and therefore are stacked:

    real_cache_prefix:calm_cache_prefix:user_supplied_key


Minting is designed to cope with highly concurrent requests and good value
of `MINT_PERIOD` would be comparable to the stored object regeneration time.

Grace period starts after mint delay and first request that comes during this time
is satisfied with stale value. The value cached under the given key
is invalidated immediately and next requesting client will refresh and
store a new value. This technique improves hit ratio for infrequently accessed
data when occasional staleness is affordable.

Add random variability to the expiry of cache objects as they may be generated
at the same time, which mitigates expiry synchronisation

The maximum real cache TTL is caclulated as

    timeout + MINT_PERIOD + GRACE_PERIOD + JITTER


Setting `MINT_PERIOD`, `GRACE_PERIOD` or `JITTER` to `0` or not setting them
at all turns off relevant logic in the code.


#### CalmCache Limitations

 * `CalmCache` currently only supports cache methods `add`, `set`, `get`, `delete`,
   `has_key` and `clear`


### Response Cache

Example usage:

    :::python
    from calm_cache.decorators import cache_response

    @cache_response(15, key_prefix='my_view', codes=(200, 404))
    def my_view(request, slug=None):
        return HttpResponse()

`cache_response`'s constructor arguments, relevant Django settings and
defaults:

 * `cache_timeout`: integer, default TTL for cached entries. Required
 * `cache`: Django cache backend name. If not specified, default cache
   backend will be used
 * `key_prefix`: this string is always prepending resulting keys.
   Default: `''`. Django setting: `CCRC_KEY_PREFIX`
 * `methods`: a list/tuple with request methods that could be cached.
   Default: `('GET', )`. Django setting: `CCRC_CACHE_REQ_METHDODS`
 * `codes`: a list/tuple with cacheable response codes.
   Default: `(200, )`. Django setting: `CCRC_CACHE_RSP_CODES`
 * `nocache_req`: a dictionary with request headers as keys and
   regular expressions as values (strings or compiled), so that when request
   has a header with value matching the expression,
   the response is never cached. The headers should be put in WSGI format,
   i.e. `'HTTP_X_FORWARDED_FOR'`. Default: `{}`.
 * `nocache_rsp`: a list of response headers that prevents response
   from being cached. Default: `('Set-Cookie', 'Vary')`.
   Django setting: `CCRC_NOCACHE_RSP_HEADERS`
 * `anonymous_only`: boolean selecting whether only anonymous requests
   should be served from the cache/responses cached.
   Default: `True`. Django setting: `CCRC_ANONYMOUS_REQ_ONLY`
 * `cache_cookies`: boolean, if False, requests with cookies will
   not be cached, otherwise cookies are ignored. Default: `False`.
   Django setting: `CCRC_CACHE_REQ_COOKIES`
 * `excluded_cookies`: if `cache_cookies` is False, cookies found in
   this list are ignored (considered as not set).
   If `cache_cookies` is True, response will not be cached if
   one of cookies listed is found in the request. Default: `()`.
   Django setting: `CCRC_EXCLUDED_REQ_COOKIES`
 * `include_scheme`: boolean selecting whether request scheme (http
   or https) should be used for the key. Default: `True`.
   Django setting: `CCRC_KEY_SCHEME`
 * `include_host`: boolean selecting whether requested Host: should
   be used for the key. Default: `True`. Django setting: `CCRC_KEY_HOST`
 * `hitmiss_header`: a tuple with three elements: header name,
   value for cache hit and another for cache miss.
   If set to `None`, the header is never added
   Default: `('X-Cache', 'Hit', 'Miss')'`. Django setting: `CCRC_HITMISS_HEADER`
 * `key_function`: optional callable that should be used instead of
   built-in key function.
   Has to accept request as its only argument and return either
   a string with the key or `None` if the request should not be cached.


#### ResponseCache Features and Guidelines

 * Unlike `CacheMiddleware`, `cache_response` does not analyse `Cache-Control`
   header and does not change cache TTL. The header is cached along
   with the response just like any other header
 * Default settings for `cache_reponse` are chosen to be the safest, but in
   order to achieve better cache performance careful configuretion is required
 * By default, reponses with `Set-Cookie` and `Vary` headers are never cached,
   requests that have `Cookie` header are not cached either
 * Responses that have CSRF token(s) are never cached
 * Requests that have authenticated user associated with them are not cached
   by default
 * URL and Hostname are used to build the cache key, which could be a problem
   for certain caching engines due to their limitation to key characters and length.
   You are advised to use some hashing `KEY_FUNCTION` in your caching backend, like,
   for example, provided `calm_cache.contrib.sha1_key_func`


## Legals

License: BSD 3-clause

Copyright (c) 2014, Fairfax Media Limited
All rights reserved.
