import time
from uuid import uuid4

from django.test import TestCase
from django.test.client import RequestFactory
from django.utils.unittest import skipUnless
from django.utils.http import http_date
from django.http import HttpResponse
from django.contrib.auth.models import User, AnonymousUser
from django.template import Template, RequestContext
from django.template.response import TemplateResponse

from django.core.cache import get_cache

from calm_cache.decorators import ResponseCache

try:
    from django.http import StreamingHttpResponse
except ImportError:
    StreamingHttpResponse = None


def randomView(request, last_modified=None, headers=None):
    """
    Returns random UUID in response body and, optionaly,
    sets Last-Modified and other arbitrary headers
    """
    response = HttpResponse(str(uuid4()))
    if last_modified is not None:
        response['Last-Modified'] = http_date(last_modified)
    if headers:
        for h, v in headers.items():
            response[h] = v

    return response

def randomTemplateView(request):
    t = Template("%s" % uuid4())
    return TemplateResponse(request, t)

def csrfView(request):
    t = Template("%s: {{ csrf_token }}" % uuid4())
    return HttpResponse(t.render(RequestContext(request)))

def csrfTemplateView(request):
    t = Template("%s: {{ csrf_token }}" % uuid4())
    return TemplateResponse(request, t)


rsp_cache = ResponseCache(0.3, cache='testcache')


class ResponseCacheTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        get_cache('testcache').clear()

    def random_get(self):
        return self.factory.get('/%s' % uuid4())

    def test_default_key_function(self):
        cache = ResponseCache(1, key_prefix='p')
        # Plain test with all defaults
        self.assertEqual(cache.key_func(self.factory.get('/url1/?k1=v1')),
                         'p#GET#http#testserver#/url1/?k1=v1')
        # Different method
        self.assertEqual(cache.key_func(self.factory.head('/url2/?k2=v2')),
                         'p#HEAD#http#testserver#/url2/?k2=v2')
        # Try HTTPS (hacky)
        request = self.factory.get('/url3/?k3=v3')
        request.is_secure = lambda: True
        self.assertEqual(cache.key_func(request),
                'p#GET#https#testserver:80#/url3/?k3=v3')
        # Try different Host: + normalisation
        request = self.factory.get('/url4/?k4=v4', HTTP_HOST='FooBar')
        self.assertEqual(cache.key_func(request),
                'p#GET#http#foobar#/url4/?k4=v4')

    def test_default_key_function_parts_omission(self):
        request = self.factory.get('/url10/?k10=v10')
        # Empty prefix
        self.assertEqual(ResponseCache(1).key_func(request),
                '#GET#http#testserver#/url10/?k10=v10')
        # Do not consider scheme
        self.assertEqual(
            ResponseCache(1, key_prefix='p', include_scheme=False).key_func(request),
            'p#GET##testserver#/url10/?k10=v10')
        # Do not consider host
        self.assertEqual(
            ResponseCache(1, key_prefix='p', include_host=False).key_func(request),
            'p#GET#http##/url10/?k10=v10')

    def test_user_supplied_key_function(self):
        # Test dumb user supplied key function
        cache = ResponseCache(1, key_func=lambda r: "KeyValue")
        request = self.factory.get('/')
        self.assertEqual(cache.key_func(request), 'KeyValue')

    def test_should_fetch(self):
        # test default behavious: GETs only
        cache = ResponseCache(1)
        self.assertTrue(cache.should_fetch(self.factory.get('/')))
        self.assertFalse(cache.should_fetch(self.factory.head('/')))
        # Allow HEAD too
        cache = ResponseCache(1, methods=('GET', 'HEAD'))
        self.assertTrue(cache.should_fetch(self.factory.head('/')))
        # Check authenticated requests (shouldn't cache by default)
        request = self.factory.get('/')
        request.user = User.objects.create_user('u1', 'u1@u1.com', 'u1')
        self.assertFalse(cache.should_fetch(request))
        # This instance should ignore authenticated user
        self.assertTrue(
            ResponseCache(1, anonymous_only=False).should_fetch(request))
        # Anonymous' responses should be cached
        request.user = AnonymousUser()
        self.assertTrue(cache.should_fetch(request))

    def test_should_store(self):
        cache = ResponseCache(1)
        # Check normal response (200)
        self.assertTrue(cache.should_store(self.factory.get('/'),
                                           HttpResponse()))
        # Check some non-200 response codes
        for code in (201, 404, 403, 500, 502, 503, 301, 302):
            self.assertFalse(cache.should_store(self.factory.get('/'),
                             HttpResponse(status=code)))

    @skipUnless(StreamingHttpResponse, "Too old for StreamingHttpResponse?")
    def test_should_store_streaming(self):
        cache = ResponseCache(1)
        # StreamingHttpResponse is never cached
        self.assertFalse(cache.should_store(self.factory.get('/'),
                         StreamingHttpResponse()))

    def test_caching_decorator(self):
        decorated_view = rsp_cache(randomView)
        # Confirm that the same URL is cached and returns the same content
        request = self.random_get()
        rsp1 = decorated_view(request)
        time.sleep(0.1)
        # This should be still cached
        rsp2 = decorated_view(request)
        time.sleep(0.3)
        # But this will expire and be refreshed
        rsp3 = decorated_view(request)
        self.assertEqual(rsp1.content, rsp2.content)
        self.assertNotEqual(rsp1.content, rsp3.content)

    def test_caching_template_response(self):
        # Perform the same tests for SimpleTemplateResponse
        decorated_view = rsp_cache(randomTemplateView)
        request = self.random_get()
        rsp1 = decorated_view(request)
        # Shouldn't be rendered yet
        self.assertFalse(hasattr(rsp1, 'content'))
        rsp1.render()
        time.sleep(0.1)
        rsp2 = decorated_view(request)
        # Should be already rendered because fetched from the cache
        self.assertTrue(hasattr(rsp2, 'content'))
        time.sleep(0.3)
        rsp3 = decorated_view(request)
        # Shouldn't be rendered yet again
        self.assertFalse(hasattr(rsp3, 'content'))
        rsp3.render()
        # Compare content
        self.assertEqual(rsp1.content, rsp2.content)
        self.assertNotEqual(rsp1.content, rsp3.content)

    def test_caching_decorator_different_urls(self):
        decorated_view = rsp_cache(randomView)
        # Different URLs are cached under different keys
        request1 = self.random_get()
        request2 = self.random_get()
        self.assertNotEqual(decorated_view(request1).content,
                            decorated_view(request2).content)

    def test_uncacheable_requests(self):
        # Test authenticated requests (shouldn't cache)
        decorated_view = rsp_cache(randomView)
        request = self.factory.get('/')
        request.user = User.objects.create_user('u1', 'u1@u1.com', 'u1')
        self.assertNotEqual(decorated_view(request).content,
                            decorated_view(request).content)

        # Test HEADs (should not cache)
        request = self.factory.head('/')
        self.assertNotEqual(decorated_view(request).content,
                            decorated_view(request).content)

    def test_last_modified_default(self):
        decorated_view = rsp_cache(randomView)
        # Last-Modified has to be set to "now"
        request = self.random_get()
        rsp = decorated_view(request)
        self.assertEqual(rsp.get('Last-Modified'), http_date())

    def test_last_modified_from_response(self):
        decorated_view = rsp_cache(randomView)
        # Last-Modified has to be set to whatever was in the original response
        request = self.random_get()
        rsp = decorated_view(request, 123456)
        self.assertEqual(rsp.get('Last-Modified'), http_date(123456))

    def test_cache_arbitrary_header(self):
        decorated_view = rsp_cache(randomView)
        # Response setting some unknown header gets cached
        request = self.random_get()
        rsp1 = decorated_view(request, headers={'h1': 'v1'})
        rsp2 = decorated_view(request, headers={'h2': 'v2'})
        self.assertEqual(rsp1.content, rsp2.content)
        # First request had been cached with its headers
        self.assertEqual(rsp2['h1'], 'v1')
        self.assertFalse(rsp2.has_header('h2'))

    def test_not_caching_set_cookie(self):
        decorated_view = rsp_cache(randomView)
        # First request with Set-Cookie is not cached
        request = self.random_get()
        rsp1 = decorated_view(request, headers={'Set-Cookie': 'foobar'})
        rsp2 = decorated_view(request)
        self.assertNotEqual(rsp1.content, rsp2.content)
        self.assertTrue(rsp1.has_header('Set-Cookie'))
        self.assertFalse(rsp2.has_header('Set-Cookie'))

    def test_not_caching_vary(self):
        decorated_view = rsp_cache(randomView)
        # First request with Set-Cookie is not cached
        request = self.random_get()
        rsp1 = decorated_view(request, headers={'Vary': '*'})
        rsp2 = decorated_view(request)
        self.assertNotEqual(rsp1.content, rsp2.content)
        self.assertTrue(rsp1.has_header('Vary'))
        self.assertFalse(rsp2.has_header('Vary'))

    def test_not_caching_configured_rsp_hdr(self):
        decorated_view = ResponseCache(
            0.3, cache='testcache', nocache_rsp=('Hdr1',))(randomView)
        # First request with Set-Cookie is not cached
        request = self.random_get()
        rsp1 = decorated_view(request, headers={'Hdr1': 'val1'})
        rsp2 = decorated_view(request)
        self.assertNotEqual(rsp1.content, rsp2.content)
        self.assertTrue(rsp1.has_header('Hdr1'))
        self.assertFalse(rsp2.has_header('Hdr1'))

    def test_not_caching_csrf_response(self):
        decorated_view = rsp_cache(csrfView)
        url = "/%s" % uuid4()
        # Responses that have CSRF token used should not be cached
        request1 = self.factory.get(url)
        request2 = self.factory.get(url)
        rsp1 = decorated_view(request1)
        rsp2 = decorated_view(request2)
        self.assertNotEqual(rsp1.content, rsp2.content)

    def test_not_caching_csrf_template_response(self):
        decorated_view = rsp_cache(csrfTemplateView)
        url = "/%s" % uuid4()
        # Responses that have CSRF token used should not be cached
        request1 = self.factory.get(url)
        request2 = self.factory.get(url)
        rsp1 = decorated_view(request1)
        rsp1.render()
        rsp2 = decorated_view(request2)
        rsp2.render()
        self.assertNotEqual(rsp1.content, rsp2.content)

    def test_not_caching_req_cookies(self):
        decorated_view = rsp_cache(randomView)
        # By default, requests with cookies aren't cached
        request = self.random_get()
        request.COOKIES['c1'] = 'v1'
        rsp1 = decorated_view(request)
        rsp2 = decorated_view(request)
        self.assertNotEqual(rsp1.content, rsp2.content)

    def test_whitelisted_req_cookies(self):
        cache = ResponseCache(0.3, cache='testcache', excluded_cookies=('c1',))
        decorated_view = cache(randomView)
        # This cookie does not prevent request from being cached
        request = self.random_get()
        request.COOKIES['c1'] = 'v1'
        rsp1 = decorated_view(request)
        rsp2 = decorated_view(request)
        self.assertEqual(rsp1.content, rsp2.content)

    def test_caching_req_cookies(self):
        cache = ResponseCache(0.3, cache='testcache', cache_cookies=True)
        decorated_view = cache(randomView)
        # This request should be cached with any cookie set
        request = self.random_get()
        request.COOKIES['c1'] = 'v1'
        rsp1 = decorated_view(request)
        rsp2 = decorated_view(request)
        self.assertEqual(rsp1.content, rsp2.content)

    def test_blacklisted_req_cookies(self):
        cache = ResponseCache(0.3, cache='testcache', cache_cookies=True,
                              excluded_cookies=('c1',))
        decorated_view = cache(randomView)
        # This cookie prevents this request from being cached,
        # though generally cookies are allowed
        request = self.random_get()
        request.COOKIES['c1'] = 'v1'
        rsp1 = decorated_view(request)
        rsp2 = decorated_view(request)
        self.assertNotEqual(rsp1.content, rsp2.content)

    def test_hitmiss_header(self):
        decorated_view = rsp_cache(randomView)
        request = self.random_get()
        rsp1 = decorated_view(request)
        rsp2 = decorated_view(request)
        self.assertEqual(rsp1['X-Cache'], 'Miss')
        self.assertEqual(rsp2['X-Cache'], 'Hit')

    def test_custom_hitmiss_header(self):
        cache = ResponseCache(0.3, cache='testcache',
                              hitmiss_header=('h', '+', '-'))
        decorated_view = cache(randomView)
        request = self.random_get()
        rsp1 = decorated_view(request)
        rsp2 = decorated_view(request)
        self.assertFalse(rsp1.has_header('X-Cache'))
        self.assertFalse(rsp2.has_header('X-Cache'))
        self.assertEqual(rsp1['h'], '-')
        self.assertEqual(rsp2['h'], '+')

    def test_absent_hitmiss_header(self):
        cache = ResponseCache(0.3, cache='testcache', hitmiss_header=None)
        decorated_view = cache(randomView)
        request = self.random_get()
        rsp1 = decorated_view(request)
        rsp2 = decorated_view(request)
        self.assertFalse(rsp1.has_header('X-Cache'))
        self.assertFalse(rsp2.has_header('X-Cache'))

    def test_django_settings(self):
        with self.settings(CCRC_KEY_PREFIX='foobar'):
            self.assertEqual(ResponseCache(1).key_prefix, 'foobar')
        with self.settings(CCRC_CACHE_REQ_COOKIES=True):
            self.assertTrue(ResponseCache(1).cache_cookies)
        with self.settings(CCRC_EXCLUDED_REQ_COOKIES=('c1', 'c2')):
            self.assertEqual(ResponseCache(1).excluded_cookies, ('c1', 'c2'))
        with self.settings(CCRC_CACHE_REQ_METHDODS=('POST',)):
            self.assertEqual(ResponseCache(1).methods, ('POST',))
        with self.settings(CCRC_CACHE_RSP_CODES=(999,)):
            self.assertEqual(ResponseCache(1).codes, (999,))
        with self.settings(CCRC_NOCACHE_RSP_HEADERS=('H1',)):
            self.assertEqual(ResponseCache(1).nocache_rsp, ('H1',))
        with self.settings(CCRC_ANONYMOUS_REQ_ONLY=False):
            self.assertFalse(ResponseCache(1).anonymous_only)
        with self.settings(CCRC_KEY_SCHEME=False):
            self.assertFalse(ResponseCache(1).include_scheme)
        with self.settings(CCRC_HITMISS_HEADER=('h', '1', '2')):
            self.assertEqual(ResponseCache(1).hitmiss_header, ('h', '1', '2'))
        with self.settings(CCRC_KEY_HOST=False):
            self.assertFalse(ResponseCache(1).include_host)

    def test_wrapper_special_properties(self):
        # The wrapper should keep original function's special attributes
        decorated_view = rsp_cache(randomView)
        self.assertEqual(decorated_view.__doc__, randomView.__doc__)
        self.assertEqual(decorated_view.__module__, randomView.__module__)
        self.assertEqual(decorated_view.__name__, randomView.__name__)
