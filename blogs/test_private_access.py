from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.http import HttpResponse

from blogs.models import Blog, Stylesheet
from blogs.private_access import PersonalBlogAccessMiddleware


class PersonalBlogAccessTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        Stylesheet.objects.create(identifier='default', css='body {}')
        self.owner = get_user_model().objects.create_user(username='owner')
        self.blog = Blog.objects.create(user=self.owner, title='Blog', subdomain='personal')

    def call(self, mode, path, user=None, **headers):
        with override_settings(PERSONAL_BLOG_ACCESS=mode):
            middleware = PersonalBlogAccessMiddleware(lambda request: HttpResponse(str(request.user)))
            request = self.factory.get(path, **headers)
            request.user = user or self.owner
            return middleware(request)

    def test_public_rejects_authentication_and_discards_existing_session(self):
        for path in ['/accounts/login/', '/admin/', '/signup/']:
            self.assertEqual(self.call('public', path).status_code, 403)
        response = self.call('public', '/dashboard/', HTTP_X_FORWARDED_HOST='private:9443')
        self.assertEqual(response.content, b'AnonymousUser')

    @override_settings(PERSONAL_BLOG_ACCESS='public', MIDDLEWARE=[
        *settings.MIDDLEWARE[:settings.MIDDLEWARE.index('django.contrib.auth.middleware.AuthenticationMiddleware') + 1],
        'blogs.private_access.PersonalBlogAccessMiddleware',
        *settings.MIDDLEWARE[settings.MIDDLEWARE.index('django.contrib.auth.middleware.AuthenticationMiddleware') + 1:],
    ])
    @patch.dict('os.environ', {'MAIN_SITE_HOSTS': 'testserver'})
    def test_public_denies_management_even_with_authenticated_session(self):
        self.client.force_login(self.owner)
        for path in ['/dashboard/', '/personal/dashboard/posts/', '/personal/delete/',
                     '/personal/remove-domain/', '/accounts/login/', '/admin/']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)
                self.assertEqual(self.client.post(path).status_code, 403)

    @override_settings(PERSONAL_BLOG_ACCESS='tailnet', MIDDLEWARE=[
        *settings.MIDDLEWARE[:settings.MIDDLEWARE.index('django.contrib.auth.middleware.AuthenticationMiddleware') + 1],
        'blogs.private_access.PersonalBlogAccessMiddleware',
        *settings.MIDDLEWARE[settings.MIDDLEWARE.index('django.contrib.auth.middleware.AuthenticationMiddleware') + 1:],
    ])
    @patch.dict('os.environ', {'MAIN_SITE_HOSTS': 'testserver'})
    def test_private_dashboard_works_without_session_and_keeps_csrf(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get('/personal/dashboard/').status_code, 200)
        self.assertEqual(client.post('/personal/delete/').status_code, 403)

    def test_public_admin_entry_cannot_be_enabled_by_identity_headers(self):
        for path in ('/admin', '/admin/'):
            response = self.call('public', path, HTTP_X_FORWARDED_HOST='blog.zrhe2016.cc',
                                 HTTP_X_FORWARDED_FOR='100.99.72.112',
                                 HTTP_TAILSCALE_USER_LOGIN='owner@example.com')
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.call('public', '/admin/login/').status_code, 403)

    def test_tailnet_uses_existing_blog_owner(self):
        response = self.call('tailnet', '/dashboard/')
        self.assertEqual(response.content, b'owner')

    def test_tailnet_fails_closed_for_multiple_blogs_or_inactive_owner(self):
        Blog.objects.create(user=self.owner, title='Another', subdomain='another')
        self.assertEqual(self.call('tailnet', '/dashboard/').status_code, 503)
        Blog.objects.filter(subdomain='another').delete()
        self.owner.is_active = False
        self.owner.save()
        self.assertEqual(self.call('tailnet', '/dashboard/').status_code, 503)
