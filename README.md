# Calm Cache for Django

`django-calm-cache` stops the thundering herds and keeps everything running
nice and smooth.

It gives you mint caching and jittering on your timeouts so that you never have
a bunch of expiring keys bring your site to a crawl.


## Quick Start

Install the library:

    pip install hg+https://bitbucket.org/pitcrews/django-calm-cache/


Update the cache settings:

    CACHES = {
        'default': {
            'BACKEND' : 'calm_cache.CalmCache',
            'LOCATION': 'locmem-cache',
            'MINT_DELAY': '10',
            'JITTER_TIME': '10',
        },
        'locmem-cache': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'foo',
        }
    }


