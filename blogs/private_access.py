"""Separate the public site from a trusted, tailnet-only application process."""
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse, HttpResponseForbidden


class PersonalBlogAccessMiddleware:
    def __init__(self, get_response):
        from django.conf import settings
        self.get_response = get_response
        self.mode = settings.PERSONAL_BLOG_ACCESS

    def __call__(self, request):
        if self.mode == 'public':
            # Ignore even pre-existing authenticated sessions on the public process.
            request.user = AnonymousUser()
            if request.path_info.strip('/').split('/', 1)[0] in {'admin', 'accounts', 'signup'}:
                return HttpResponseForbidden('Private access only')
        elif self.mode == 'tailnet':
            from blogs.models import Blog
            blogs = list(Blog.objects.select_related('user').all()[:2])
            if len(blogs) != 1 or not blogs[0].user.is_active:
                return HttpResponse('Private access is not configured', status=503)
            request.user = blogs[0].user
            request.tailnet_private_access = True
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if self.mode != 'public':
            return None
        # The wrapped views retain their original module via functools.wraps.
        # Include management actions outside /dashboard/, such as blog deletion.
        if (view_func.__module__ in {'blogs.views.dashboard', 'blogs.views.studio',
                                    'blogs.views.media'} or
            (view_func.__module__ == 'blogs.views.analytics' and view_func.__name__ == 'analytics') or
            (view_func.__module__ == 'blogs.views.emailer' and view_func.__name__ == 'email_list')):
            return HttpResponseForbidden('Private access only')
        return None
