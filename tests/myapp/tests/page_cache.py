import random

from django.test import TestCase
from django.test.client import RequestFactory
from django.utils.unittest import skipUnless
from django.http import HttpResponse
from django.contrib.auth.models import User

from calm_cache.decorators import PageCacheDecorator

random.seed()

try:
    from django.http import StreamingHttpResponse
except ImportError:
    StreamingHttpResponse = None

def randomView(request):
    return HttpResponse(str(random.randint(0,1e6)))

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

    def test_should_store(self):
        cache = PageCacheDecorator(1)

        # Check normal response (200)
        self.assertTrue(cache.should_store(HttpResponse()))

        # Check some non-200 response codes
        for code in (201, 404, 403, 500, 502, 503, 301, 302):
            self.assertFalse(cache.should_store(HttpResponse(status=code)))

    @skipUnless(StreamingHttpResponse, "No StreamingHttpResponse in this Djnago")
    def test_should_store_streaming(self):
        cache = PageCacheDecorator(1)
        self.assertFalse(cache.should_store(StreamingHttpResponse()))

    def test_caching_decorator(self):
        request1 = self.factory.get('/')
        request2 = self.factory.get('/about/')
        decorator = PageCacheDecorator(1)
        decorated_view = decorator(randomView)

        # Confirm that the same URL is cached and returns the same result
        r11 = decorated_view(request1)
        r12 = decorated_view(request1)
        self.assertEqual(r11.content, r12.content)

        # Different URL returns different result
        r2 = decorated_view(request2)
        self.assertNotEqual(r2.content, r12.content)
