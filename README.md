# Calm Cache for Django

`django-calm-cache` keeps your cache calm while your site is being hammered by
bucket loads of traffic.

## Key Features

 * [Mint caching](http://djangosnippets.org/snippets/155/) to avoid the
   [dog pile](http://en.wikipedia.org/wiki/Cache_stampede) effect
 * Timeout jitter to reduce the number of entries expiring simultaneously
 * Works alongside any other Django cache backend.

## Quick Start

Install the library:

    pip install hg+https://bitbucket.org/pitcrews/django-calm-cache/


Update the cache settings:

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
        }
    }


## Known Limitations

 * Currently only supports cache methods `add`, `set`, `get`, `delete`,
   `has_key` and `clear`

