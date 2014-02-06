import random
import time

from django.test import TestCase
from django.test.client import RequestFactory
from django.utils.unittest import skipUnless
from django.utils.http import http_date
from django.http import HttpResponse
from django.contrib.auth.models import User, AnonymousUser
from django.template import Template
from django.template.response import SimpleTemplateResponse
from django.core.cache import get_cache

from calm_cache.decorators import PageCacheDecorator

random.seed()

try:
    from django.http import StreamingHttpResponse
except ImportError:
    StreamingHttpResponse = None


def randomView(request, last_modified=None):
    response = HttpResponse(str(random.randint(0,1e6)))
    if last_modified is not None:
        response['Last-Modified'] = http_date(last_modified)
    return response


def templateRandomView(request):
    t = Template("%s" % random.randint(0, 1e6))
    return SimpleTemplateResponse(t)

page_cache = PageCacheDecorator(0.3, cache='testcache')

class PageCacheTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        get_cache('testcache').clear()

    def test_default_key_function(self):
        cache = PageCacheDecorator(1, key_prefix='p')
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
        self.assertEqual(PageCacheDecorator(1).key_func(request),
                '#GET#http#testserver#/url10/?k10=v10')
        # Do not consider scheme
        self.assertEqual(
            PageCacheDecorator(1, key_prefix='p', include_scheme=False).key_func(request),
            'p#GET##testserver#/url10/?k10=v10')
        # Do not consider host
        self.assertEqual(
            PageCacheDecorator(1, key_prefix='p', include_host=False).key_func(request),
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
        decorated_view = page_cache(randomView)
        # Confirm that the same URL is cached and returns the same content
        # And cache-related headers
        request = self.factory.get('/%i' % random.randint(1,1e6))
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
        decorated_view = page_cache(templateRandomView)
        request = self.factory.get('/%i' % random.randint(1,1e6))
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
        decorated_view = page_cache(randomView)
        # Different URLs are cached under different keys
        request1 = self.factory.get('/%i' % random.randint(1,1e6))
        request2 = self.factory.get('/%i' % random.randint(1,1e6))
        self.assertNotEqual(decorated_view(request1).content,
                            decorated_view(request2).content)

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

    def test_last_modified_default(self):
        decorated_view = page_cache(randomView)
        # Last-Modified has to be set to "now"
        request = self.factory.get('/%i' % random.randint(1,1e6))
        rsp = decorated_view(request)
        self.assertEqual(rsp.get('Last-Modified'), http_date())

    def test_last_modified_from_response(self):
        decorated_view = page_cache(randomView)
        # Last-Modified has to be set to whatever was in the original response
        request = self.factory.get('/%i' % random.randint(1,1e6))
        rsp = decorated_view(request, 123456)
        self.assertEqual(rsp.get('Last-Modified'), http_date(123456))
