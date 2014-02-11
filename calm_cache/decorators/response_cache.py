from django.core.cache import get_cache, DEFAULT_CACHE_ALIAS
from django.utils.http import http_date
from django.conf import settings


class ResponseCache(object):
    """
    A decorator that conditionally caches decorated view's response in
    selected Django cache backend.

    Example configuration:

        from calm_cache.decorators import ResponseCache

        @ResponseCache(15, key_prefix='my_view', codes=(200, 404))
        def my_view(request, slug):
            ...
            return HttpResponse()
    """

    # Defaults
    ANONYMOUS_REQ_ONLY = True
    CACHE_REQ_COOKIES = False
    EXCLUDE_REQ_COOKIES = ()
    CACHE_REQ_METHDODS = ('GET', )
    CACHE_RSP_CODES = (200, )
    NOCACHE_RSP_HEADERS = ('Set-Cookie', 'Vary')
    KEY_PREFIX = ''
    KEY_SCHEME = True
    KEY_HOST = True

    def __init__(self, cache_timeout, **kwargs):
        """
        Args:

            `cache_timeout`: integer, default TTL for cached entries. Required
            `cache`: Django cache backend name. If not specified, default cache
                backend will be used
            `key_prefix`: this string is always prepending resulting keys
            `methods`: a list/tuple with request methods that could be cached.
                Default: `('GET', )`
            `codes`: a list/tuple with cacheable response codes.
                Default: `(200, )`
            `nocache_rsp`: a list of response headers that prevents response
                from being cached. Default: ('Set-Cookie', 'Vary')
            `anonymous_only`: boolean selecting whether only anonymous requests
                should be served from the cache/responses cached.
                Default: `True`
            `include_scheme`: boolean selecting whether request scheme (http
                or https) should be used for the key. Default: `True`
            `include_host`: boolean selecting whether requested Host: should
                be used for the key. Default: `True`
            `key_function`: optional callable that should be used instead of
                built-in key function.
                Has to accept request as its only argument and return either
                a string with the key or `None` if the request
                should not be cached.
        """
        self.cache_timeout = cache_timeout
        self.cache = get_cache(kwargs.get('cache', DEFAULT_CACHE_ALIAS))
        self.key_prefix = kwargs.get(
            'key_prefix', getattr(settings, 'CCRC_KEY_PREFIX', self.KEY_PREFIX))
        self.methods = kwargs.get(
            'methods', getattr(settings, 'CCRC_CACHE_REQ_METHDODS',
                               self.CACHE_REQ_METHDODS))
        self.codes = kwargs.get(
            'codes', getattr(settings, 'CCRC_CACHE_RSP_CODES',
                             self.CACHE_RSP_CODES))
        self.nocache_rsp = kwargs.get(
            'nocache_rsp', getattr(settings, 'CCRC_NOCACHE_RSP_HEADERS',
                                   self.NOCACHE_RSP_HEADERS))
        self.anonymous_only = kwargs.get(
            'anonymous_only', getattr(settings, 'CCRC_ANONYMOUS_REQ_ONLY',
                                      self.ANONYMOUS_REQ_ONLY))
        self.cache_cookies = kwargs.get(
            'cache_cookies', getattr(settings, 'CCRC_CACHE_REQ_COOKIES',
                                     self.CACHE_REQ_COOKIES))
        self.exclude_cookies = kwargs.get(
            'exclude_cookies', getattr(settings, 'CCRC_EXCLUDE_REQ_COOKIES',
                                      self.EXCLUDE_REQ_COOKIES))
        self.include_scheme = kwargs.get(
            'include_scheme', getattr(settings, 'CCRC_KEY_SCHEME',
                                      self.KEY_SCHEME))
        self.include_host = kwargs.get(
            'include_host', getattr(settings, 'CCRC_KEY_HOST', self.KEY_HOST))
        self.key_func = kwargs.get('key_func', None) or self._key_func

    def __call__(self, view):
        self.wrapped = view
        return self.wrapper

    def _key_func(self, request):
        """
        Default key function.

        Generated key is composed of parts of the request and never hashed
        that could be a problem for certain backends under certain
        circumstances. Use `calm_cache.contrib.sha1_key_func` key function
        in your caching backed to ensure that keys always fit backend's
        requirements.

        Returns `None` if the request should not be cached
        """
        if self.include_scheme:
            scheme = 'https' if request.is_secure() else 'http'
        else:
            scheme = ''
        # Normalise Host: if we are going to use it
        host = request.get_host().lower() if self.include_host else ''
        key_components = (
            self.key_prefix, request.method, scheme, host,
            request.get_full_path()
        )
        return '#'.join(key_components)

    def should_fetch(self, request):
        """
        Returns `True` if this request should be tried against the cache.
        In the opposite case, it returns `False` and wrapped view is executed
        and returned immediately, skipping any further processing.
        """
        if not request.method in self.methods:
            return False
        if self.anonymous_only:
            if hasattr(request, 'user') and not request.user.is_anonymous():
                return False
        if not self.cache_cookies:
            for cookie in request.COOKIES:
                if cookie not in self.exclude_cookies:
                    return False
        else:
            for cookie in request.COOKIES:
                if cookie in self.exclude_cookies:
                    return False
        return True

    def should_store(self, request, response):
        """
        Returns `True` if this response could be cached, `False` otherwise.
        """
        if getattr(response, 'streaming', False):
            return False
        if not response.status_code in self.codes:
            return False
        for header in self.nocache_rsp:
            if response.has_header(header):
                return False
        # Indicates that CSRF token was accessed in templates at least once
        # WARNING: Does not work for SimpleTemplateResponse !
        if request.META.get('CSRF_COOKIE_USED', False):
            return False
        return True

    def store(self, cache_key, request, response):
        """
        Conditionally saves response to the cache
        """
        if not self.should_store(request, response):
            return
        # Set Last-Modified to the response, if it's not set already:
        if not response.has_header('Last-Modified'):
            response['Last-Modified'] = http_date()
        self.cache.set(cache_key, response, self.cache_timeout)

    def wrapper(self, request, *args, **kwargs):
        """
        Wraps decorated view, conditionally performing response caching.
        """
        cache_key = self.key_func(request)
        if not self.should_fetch(request) or cache_key is None:
            # Return immediately
            return self.wrapped(request, *args, **kwargs)
        # Fetch from cache and return if found
        cached_response = self.cache.get(cache_key)
        if cached_response is not None:
            return cached_response

        # Execute the view
        response = self.wrapped(request, *args, **kwargs)

        # Based on django.middleware.cache.UpdateCacheMiddleware
        if hasattr(response, 'render') and callable(response.render):
            # SimpleTemplateResponse and TemplateResponse are different
            # Should store reponses after they are rendered
            response.add_post_render_callback(
                lambda r: self.store(cache_key, request, r)
            )
        else:
            # Store the response straight away
            self.store(cache_key, request, response)
        return response
