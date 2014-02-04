import random
import time

from django.test import TestCase
from django.test.client import RequestFactory
from django.utils.unittest import skipUnless
from django.http import HttpResponse
from django.contrib.auth.models import User, AnonymousUser
from django.template import Template
from django.template.response import SimpleTemplateResponse

from calm_cache.decorators import PageCacheDecorator

random.seed()

try:
    from django.http import StreamingHttpResponse
except ImportError:
    StreamingHttpResponse = None


def randomView(request, cache_seconds=None):
    response = HttpResponse(str(random.randint(0,1e6)))
    if cache_seconds is not None:
        response['Cache-Control'] = "max-age=%i" % cache_seconds
    return response


def templateRandomView(request):
    t = Template("%s" % random.randing(0, 1e6))
    return SimpleTemplateResponse(t)


class PageCacheTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_default_key_function(self):
        cache = PageCacheDecorator(1, key_prefix='p')
        # Plain test wil all defaults
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
        self.assertEqual(PageCacheDecorator(1).key_func(request),
                '#GET#http#testserver#/url10/?k10=v10')
        # Do not consider scheme
        self.assertEqual(
            PageCacheDecorator(1, key_prefix='p', consider_scheme=False).key_func(request),
            'p#GET##testserver#/url10/?k10=v10')
        # Do not consider host
        self.assertEqual(
            PageCacheDecorator(1, key_prefix='p', consider_host=False).key_func(request),
            'p#GET#http##/url10/?k10=v10')

    def test_user_supplied_key_function(self):
        # Test dumb user supplied key function
        cache = PageCacheDecorator(1, key_func=lambda r: "KeyValue")
        request = self.factory.get('/')
        self.assertEqual(cache.key_func(request), 'KeyValue')

    def test_should_fetch(self):
        # test default behavious: GETs only
        cache = PageCacheDecorator(1)
        self.assertTrue(cache.should_fetch(self.factory.get('/')))
        self.assertFalse(cache.should_fetch(self.factory.head('/')))
        # Allow HEAD too
        cache = PageCacheDecorator(1, methods=('GET', 'HEAD'))
        self.assertTrue(cache.should_fetch(self.factory.head('/')))
        # Check authenticated requests (shouldn't cache by default)
        request = self.factory.get('/')
        request.user = User.objects.create_user('u1', 'u1@u1.com', 'u1')
        self.assertFalse(cache.should_fetch(request))
        # This instance should ignore authenticated user
        self.assertTrue(
            PageCacheDecorator(1, anonymous_only=False).should_fetch(request))
        # Anonymous' responses should be cached
        request.user = AnonymousUser()
        self.assertTrue(cache.should_fetch(request))

    def test_should_store(self):
        cache = PageCacheDecorator(1)
        # Check normal response (200)
        self.assertTrue(cache.should_store(HttpResponse()))
        # Check some non-200 response codes
        for code in (201, 404, 403, 500, 502, 503, 301, 302):
            self.assertFalse(cache.should_store(HttpResponse(status=code)))

    @skipUnless(StreamingHttpResponse, "Too old for StreamingHttpResponse?")
    def test_should_store_streaming(self):
        cache = PageCacheDecorator(1)
        # StreamingHttpResponse is never cached
        self.assertFalse(cache.should_store(StreamingHttpResponse()))

    def test_caching_decorator(self):
        decorator = PageCacheDecorator(3)
        decorated_view = decorator(randomView)
        # Confirm that the same URL is cached and returns the same content
        # And cache-related headers
        request1 = self.factory.get('/')
        rsp1 = decorated_view(request1)
        time.sleep(1.1)
        rsp2 = decorated_view(request1)
        self.assertEqual(rsp1.content, rsp2.content)
        self.assertEqual(rsp1.get('Cache-Control'), 'max-age=3')
        for header in ('Last-Modified', 'Expires', 'Cache-Control'):
            self.assertEqual(rsp1.get(header), rsp2.get(header))

        # Different URLs are cached under different keys
        request2 = self.factory.get('/?r=2')
        self.assertNotEqual(rsp1.content, decorated_view(request2).content)

    def test_caching_template_response(self):
        # Perform the same tests for SimpleTemplateResponse
        decorator = PageCacheDecorator(3)
        decorated_view = decorator(templateRandomView)
        request1 = self.factory.get('/')
        rsp1 = decorated_view(request1)
        time.sleep(1.1)
        rsp2 = decorated_view(request1)
        self.assertEqual(rsp1.content, rsp2.content)
        self.assertEqual(rsp1.get('Cache-Control'), 'max-age=3')
        for header in ('Last-Modified', 'Expires', 'Cache-Control'):
            self.assertEqual(rsp1.get(header), rsp2.get(header))
        request2 = self.factory.get('/?r=2')
        self.assertNotEqual(rsp1.content, decorated_view(request2).content)

    def test_uncacheable_requests(self):
        # Test authenticated requests (shouldn't cache)
        decorator = PageCacheDecorator(3)
        decorated_view = decorator(randomView)
        request = self.factory.get('/')
        request.user = User.objects.create_user('u1', 'u1@u1.com', 'u1')
        self.assertNotEqual(decorated_view(request).content,
                            decorated_view(request).content)

        # Test HEADs (should not cache)
        request = self.factory.head('/')
        self.assertNotEqual(decorated_view(request).content,
                            decorated_view(request).content)

    def test_cache_control(self):
        decorator = PageCacheDecorator(3600)
        decorated_view = decorator(randomView)
        request = self.factory.get('/?t1')
        # Set max-age to 0 (i.e. "no cache")
        self.assertNotEqual(decorated_view(request, 0).content,
                            decorated_view(request, 0).content)
        # Check if Cache-Control could be controlled from the view
        request = self.factory.get('/?t2')
        # First uncached response is controlled by the view's Cache-Contol:
        self.assertEqual(decorated_view(request, 10).get('Cache-Control'),
                'max-age=10')
        # And check if Cache-Control value is cached from the previous request
        self.assertEqual(decorated_view(request, 3).get('Cache-Control'),
                'max-age=10')
