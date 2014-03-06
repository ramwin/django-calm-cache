DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

ROOT_URLCONF = ''
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'myapp',
    ##'your.app.goes.here',
)

SITE_ID  = 1
TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.request",
)

CACHES = {
    'default': {
        'BACKEND' : 'calm_cache.backends.CalmCache',
        'LOCATION': 'testcache',
        'OPTIONS': {
            'MINT_PERIOD': '10',
            'GRACE_PERIOD': '60',
            'JITTER': '10',
        },
    },
    'testcache': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'we-are-all-individuals',
    }
}
