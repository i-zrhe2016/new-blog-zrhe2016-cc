"""Database-backed public assets, including preserved migrated URLs."""
import uuid
from pathlib import PurePosixPath

from django.utils.text import slugify

from django.http import Http404, HttpResponse

from blogs.models import StoredAsset


def store_asset(data, content_type, filename, blog):
    name = PurePosixPath(filename)
    stem = slugify(name.stem)[:100] or 'file'
    suffix = ''.join(c for c in name.suffix.lower() if c.isascii() and (c.isalnum() or c == '.'))[:20]
    path = f'/media-files/{uuid.uuid4().hex}/{stem}{suffix}'
    StoredAsset.objects.create(blog=blog, path=path, content_type=content_type or 'application/octet-stream', data=data)
    return f'{blog.useful_domain}{path}'


def asset_response(path):
    asset = StoredAsset.objects.filter(path=path).first()
    if asset is None:
        return None
    response = HttpResponse(bytes(asset.data), content_type=asset.content_type)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    response['Cache-Control'] = 'public, max-age=86400'
    return response


def serve_asset(request, asset_id, filename):
    response = asset_response(request.path_info)
    if response is None:
        raise Http404
    return response


class MigratedAssetMiddleware:
    """Check the database before WhiteNoise serves legacy static copies."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info.startswith('/static/migrated/'):
            response = asset_response(request.path_info)
            if response is not None:
                return response
        return self.get_response(request)
