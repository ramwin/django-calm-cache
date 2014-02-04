from django.core.cache import get_cache, DEFAULT_CACHE_ALIAS
from django.utils.cache import get_max_age, patch_response_headers


class PageCacheDecorator(object):

    def __init__(self, cache_timeout, **kwargs):
        self.cache_timeout = cache_timeout
        self.cache = get_cache(kwargs.get('cache', DEFAULT_CACHE_ALIAS))
        self.key_prefix = kwargs.get('key_prefix', '')
        self.methods = kwargs.get('methods', ('GET', ))
        self.codes = kwargs.get('codes', (200, ))
        self.consider_scheme = ('consider_scheme', True)
        self.consider_host = ('consider_host', True)
        self.anonymous_only = ('anonymous_only', True)
        self.key_func = kwargs.get('key_func', None) or self._key_func

    def __call__(self, view):
        self.wrapped = view
        return self.wrapper

    def _key_func(self, request):
        if self.consider_scheme:
            scheme = 'https' if request.is_secure() else 'http'
        else:
            scheme = ''
        host = request.get_host().lower().strip() if self.consider_host else ''
        key_components = (
            self.key_prefix, request.method, scheme, host,
            request.get_full_path()
        )
        return '#'.join(key_components)

    def should_fetch(self, request):
        if not request.method in self.methods:
            return False
        if self.anonymous_only:
            if hasattr(request, 'user') and not request.user.is_anonymous():
                return False
        return True

    def should_store(self, request, response):
        if getattr(response, 'streaming', False):
            return False
        if not response.status_code in self.codes:
            return False
        return True

    def wrapper(self, request, *args, **kwargs):
        cache_key = self.key_func(request)
        if not self.should_fetch(request) or cache_key is None:
            return self.wrapped(request, *args, **kwargs)
        cached_response = self.cache.get(cache_key)
        if cached_response is not None:
            return cached_response

        response = self.wrapped(request, *args, **kwargs)
        if not self.should_store(request, response):
            return response

        timeout = get_max_age(response)
        if timeout is None:
            timeout = self.cache_timeout
        patch_response_headers(response, timeout)

        if timeout:
            if hasattr(response, 'render') and callable(response.render):
                response.add_post_render_callback(
                    lambda r: self.cache.set(cache_key, response, timeout)
                )
            else:
                self.cache.set(cache_key, response, timeout)
        return response
