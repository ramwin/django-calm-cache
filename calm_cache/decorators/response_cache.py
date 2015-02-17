from functools import wraps
import re

from django.core.cache import get_cache, DEFAULT_CACHE_ALIAS
from django.utils.http import http_date
from django.template.response import SimpleTemplateResponse
from django.conf import settings


class ResponseCache(object):
    """
    A decorator that conditionally caches decorated view's response in
    selected Django cache backend.

    Example configuration:

        from calm_cache.decorators import cache_response

        @cache_response(15, key_prefix='my_view', codes=(200, 404))
        def my_view(request, slug):
            ...
            return HttpResponse()
    """

    # Defaults
    cache = getattr(settings, 'CCRC_CACHE', DEFAULT_CACHE_ALIAS)
    anonymous_only = getattr(settings, 'CCRC_ANONYMOUS_REQ_ONLY', True)
    cache_cookies = getattr(settings, 'CCRC_CACHE_REQ_COOKIES', False)
    excluded_cookies = getattr(settings, 'CCRC_EXCLUDED_REQ_COOKIES', ())
    methods = getattr(settings, 'CCRC_CACHE_REQ_METHDODS', ('GET', ))
    codes = getattr(settings, 'CCRC_CACHE_RSP_CODES', (200, ))
    nocache_req = getattr(settings, 'CCRC_NOCACHE_REQ_HEADERS', {})
    nocache_rsp = getattr(settings, 'CCRC_NOCACHE_RSP_HEADERS',
                          ('Set-Cookie', 'Vary'))
    key_prefix = getattr(settings, 'CCRC_KEY_PREFIX', '')
    include_scheme = getattr(settings, 'CCRC_KEY_SCHEME', True)
    include_host = getattr(settings, 'CCRC_KEY_HOST', True)
    hitmiss_header = getattr(settings, 'CCRC_HITMISS_HEADER',
                             ('X-Cache', 'Hit', 'Miss'))

    def __init__(self, cache_timeout, **kwargs):
        """
        Args:

            `cache_timeout`: integer, default TTL for cached entries. Required
            `cache`: Django cache backend name. If not specified, default cache
                backend will be used
            `key_prefix`: this string is always prepending resulting keys.
                Default: `''`. Django setting: `CCRC_KEY_PREFIX`
            `methods`: a list/tuple with request methods that could be cached.
                Default: `('GET', )`. Django setting: `CCRC_CACHE_REQ_METHDODS`
            `codes`: a list/tuple with cacheable response codes.
                Default: `(200, )`. Django setting: `CCRC_CACHE_RSP_CODES`
            `nocache_req`: a dictionary with request headers as keys and
                regular expressions as values (strings or compiled),
                so that when request has a header with value matching
                the expression, the response is never cached. The headers
                should be put in WSGI format, i.e. 'HTTP_X_FORWARDED_FOR'.
                Default: {}
            `nocache_rsp`: a list of response headers that prevents response
                from being cached. Default: ('Set-Cookie', 'Vary').
                Django setting: `CCRC_NOCACHE_RSP_HEADERS`
            `anonymous_only`: boolean selecting whether only anonymous requests
                should be served from the cache/responses cached.
                Default: `True`. Django setting: `CCRC_ANONYMOUS_REQ_ONLY`
            `cache_cookies`: boolean, if False, requests with cookies will
                not be cached, otherwise cookies are ignored. Default: `False`.
                Django setting: `CCRC_CACHE_REQ_COOKIES`
            `excluded_cookies`: if `cache_cookies` is False, cookies found in
                this list are ignored (considered as not set).
                If `cache_cookies` is True, response will not be cached if
                one of cookies listed is found in the request. Default: `()`.
                Django setting: `CCRC_EXCLUDED_REQ_COOKIES`
            `include_scheme`: boolean selecting whether request scheme (http
                or https) should be used for the key. Default: `True`.
                Django setting: `CCRC_KEY_SCHEME`
            `include_host`: boolean selecting whether requested Host: should
                be used for the key. Default: `True`.
                Django setting: `CCRC_KEY_HOST`
            `hitmiss_header`: a tuple with three elements: header name,
                value for cache hit and another for cache miss.
                If set to `None`, the header is never added
                Default: `('X-Cache', 'Hit', 'Miss')'`.
                Django setting: `CCRC_HITMISS_HEADER`
            `key_function`: optional callable that should be used instead of
                built-in key function.
                Has to accept request as its only argument and return either
                a string with the key or `None` if the request
                should not be cached.
        """
        self.cache_timeout = cache_timeout
        self.cache = get_cache(kwargs.get('cache', self.cache))
        self.key_func = kwargs.get('key_func', self._key_func)
        options = ('anonymous_only', 'cache_cookies', 'excluded_cookies',
                   'methods', 'codes', 'nocache_req', 'nocache_rsp',
                   'key_prefix', 'include_scheme', 'include_host',
                   'hitmiss_header')
        for option in options:
            setattr(self, option, kwargs.get(option, getattr(self, option)))

    def __call__(self, view):
        self.wrapped = view
        # Update __name__, __doc__ and __module__
        # It's impossible to change these attributes for a method, hence this
        # function
        @wraps(view)
        def _wrapper(request, *args, **kwargs):
            return self.wrapper(request, *args, **kwargs)
        return _wrapper

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
        for header, regex in self.nocache_req.items():
            if header in request.META and  re.search(regex,
                                                     request.META[header]):
                return False
        if self.anonymous_only:
            if hasattr(request, 'user') and not request.user.is_anonymous():
                return False
        if not self.cache_cookies:
            for cookie in request.COOKIES:
                if cookie not in self.excluded_cookies:
                    return False
        else:
            for cookie in request.COOKIES:
                if cookie in self.excluded_cookies:
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

    def update_response(self, response, hit):
        """
        Updates response with a header indicating if cache was hit or missed
        """
        if self.hitmiss_header is None:
            return
        hitmiss_header, hit_value, miss_value = self.hitmiss_header
        response[hitmiss_header] = hit_value if hit else miss_value

    def store(self, cache_key, request, response):
        """
        Conditionally saves response to the cache
        """
        if not self.should_store(request, response):
            return
        # Set Last-Modified to the response, if it's not set already:
        if not response.has_header('Last-Modified'):
            response['Last-Modified'] = http_date()
        # Set cache: hit header so it's always served from cache
        self.update_response(response, hit=True)
        self.cache.set(cache_key, response, self.cache_timeout)
        # Add cache miss header before serving first time after missed and stored
        self.update_response(response, hit=False)

    def wrapper(self, request, *args, **kwargs):
        """
        Wraps decorated view, conditionally performing response caching.
        """
        cache_key = self.key_func(request)
        if cache_key is None or not self.should_fetch(request):
            # Return immediately
            return self.wrapped(request, *args, **kwargs)
        # Fetch from cache and return if found
        cached_response = self.cache.get(cache_key)
        if cached_response is not None:
            return cached_response

        # Execute the view
        response = self.wrapped(request, *args, **kwargs)

        # Check if this is TemplateResponse and it's not rendered yet
        if isinstance(response, SimpleTemplateResponse) and not response.is_rendered:
            # SimpleTemplateResponse and TemplateResponse are different
            # Should store reponses after they are rendered
            response.add_post_render_callback(
                lambda r: self.store(cache_key, request, r)
            )
        else:
            # Store the response straight away
            self.store(cache_key, request, response)
        return response


cache_response = ResponseCache
