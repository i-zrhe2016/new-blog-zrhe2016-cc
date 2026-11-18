import hmac
import os

from django.http import HttpResponseForbidden


class OriginPathMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        prefix = '/bear-origin'
        path = request.path_info
        if path == prefix or path.startswith(prefix + '/'):
            expected = os.environ.get('BLOG_ORIGIN_TOKEN', '')
            supplied = request.headers.get('X-Blog-Origin-Token', '')
            if not expected or not hmac.compare_digest(supplied, expected):
                return HttpResponseForbidden('Forbidden')
            request.META['HTTP_X_FORWARDED_HOST'] = 'blog.zrhe2016.workers.dev'
            request.META['HTTP_X_FORWARDED_PROTO'] = 'https'
            request.path_info = path[len(prefix):] or '/'
            request.path = request.path_info
        return self.get_response(request)
