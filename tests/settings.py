DEBUG = True
SECRET_KEY = 'toosecrettoremember'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

ALLOWED_HOSTS = ["foobar"]

ROOT_URLCONF = ''
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'myapp',
    # 'your.app.goes.here',
)

SITE_ID = 1

CACHES = {
    'default': {
        'BACKEND': 'calm_cache.backends.CalmCache',
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
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
                'django.template.context_processors.media',
            ],
        },
    },
]
