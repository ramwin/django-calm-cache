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

## Quick Start

First install the library:

    pip install hg+https://bitbucket.org/pitcrews/django-calm-cache/


Next update the cache settings in your `settings.py`:

    :::python
    CACHES = {
        'default': {
            'BACKEND' : 'calm_cache.CalmCache',
            'LOCATION': 'locmem-cache',
            'MINT_DELAY': '10', # Allow stale results for this many seconds. Default: 0 (Off)
            'JITTER_TIME': '10', # Upper bound on the random jitter in seconds. Default: 0 (Off)
        },
        'locmem-cache': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'foo',
        },
        'zipped-memcached': {
            'BACKEND': 'calm_cache.backends.ZipMemcachedCache',
            'LOCATION': '127.0.0.1:11211',
            'MIN_COMPRESS_LEN': 1024,
        },
        'zipped-bin-pylibmc': {
            'BACKEND': 'calm_cache.backends.ZipPyLibMCCache',
            'LOCATION': '127.0.0.1:11211',
            'MIN_COMPRESS_LEN': 1024,
            'BINARY': True,
        },
    }

Now relax knowing your site's caching won't fall over at the first sign of sustained traffic.

## Known Limitations

 * Currently only supports cache methods `add`, `set`, `get`, `delete`,
   `has_key` and `clear`

## Legals

License: BSD 3-clause

Copyright (c) 2013, Fairfax Media Limited
All rights reserved.

