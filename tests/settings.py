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
        'BACKEND' : 'calm_cache.CalmCache',
        'LOCATION': 'testcache',
        'MINT_DELAY': '10',
        'JITTER_TIME': '10',
    },
    'testcache': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'we-are-all-individuals',
    }
}
