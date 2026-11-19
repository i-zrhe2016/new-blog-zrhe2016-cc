"""Versionable snapshots of personal blog content, excluding account secrets."""
import contextlib
import datetime
import json
import os
from contextvars import ContextVar
from pathlib import Path
import re
import tempfile

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction

class ContentJSONEncoder(DjangoJSONEncoder):
    def default(self, value):
        if isinstance(value, (datetime.datetime, datetime.date)):
            return value.isoformat()
        return super().default(value)


exports_suspended = ContextVar('content_exports_suspended', default=False)


@contextlib.contextmanager
def suspend_exports():
    token = exports_suspended.set(True)
    try:
        yield
    finally:
        exports_suspended.reset(token)


BLOG_FIELDS = ('created_date', 'last_modified', 'title', 'subdomain', 'domain', 'nav', 'content', 'meta_description',
               'meta_image', 'lang', 'meta_tag', 'blog_path', 'header_directive',
               'footer_directive', 'custom_styles', 'overwrite_styles', 'favicon',
               'date_format', 'analytics_active', 'post_template', 'robots_txt',
               'rss_alias', 'codemirror_enabled')
POST_FIELDS = ('uid', 'title', 'slug', 'alias', 'published_date', 'all_tags',
               'publish', 'discoverable', 'is_page', 'canonical_url',
               'meta_description', 'meta_image', 'lang', 'class_name',
               'first_published_at', 'last_modified')


def store_path():
    value = getattr(settings, 'PERSONAL_CONTENT_DIR', None)
    return Path(value) if value else None


@contextlib.contextmanager
def _lock(root):
    root.mkdir(parents=True, exist_ok=True)
    with open(root / '.content.lock', 'a+b') as lock:
        if os.name == 'nt':
            import msvcrt
            lock.seek(0)
            if not lock.read(1):
                lock.write(b'0')
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding='utf-8') == text:
        return
    fd, name = tempfile.mkstemp(prefix='.content-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def export_content(root=None):
    from blogs.models import Blog

    root = Path(root) if root else store_path()
    if root is None:
        raise ValueError('PERSONAL_CONTENT_DIR is not configured')
    with _lock(root):
        # Read the blog and its posts from one consistent database snapshot.
        with transaction.atomic():
            blogs = list(Blog.objects.order_by('pk')[:2])
            if len(blogs) != 1:
                raise ValueError('Content export requires exactly one blog')
            blog = blogs[0]
            blog_data = {f: getattr(blog, f) for f in BLOG_FIELDS}
            posts = list(blog.posts.order_by('uid').values(*POST_FIELDS, 'content'))
        documents = {}
        for post in posts:
            if not re.fullmatch(r'[A-Za-z0-9_-]+', post['uid']):
                raise ValueError('Post UID cannot be represented safely as a filename')
            filename = post['uid'] + '.md'
            if filename in documents:
                raise ValueError('Duplicate post UID')
            metadata = {field: post[field] for field in POST_FIELDS}
            documents[filename] = '---\n' + json.dumps(metadata, cls=ContentJSONEncoder, ensure_ascii=False, indent=2) + '\n---\n' + post['content']
        posts_dir = root / 'posts'
        posts_dir.mkdir(exist_ok=True)
        manifest = root / 'manifest.json'
        previous = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else []
        if not isinstance(previous, list) or any(not isinstance(name, str) for name in previous):
            raise ValueError('Invalid previous content manifest')
        _write(root / 'blog.json', json.dumps(blog_data, cls=ContentJSONEncoder, ensure_ascii=False, indent=2) + '\n')
        for filename, text in documents.items():
            _write(posts_dir / filename, text)
        # Publish the new manifest before removing obsolete files. A failed
        # manifest write must not invalidate the previously published manifest.
        _write(manifest, json.dumps(sorted(documents), ensure_ascii=False, indent=2) + '\n')
        for name in previous:
            if name not in documents and re.fullmatch(r'[A-Za-z0-9_-]+\.md', name):
                (posts_dir / name).unlink(missing_ok=True)
        return len(documents)


def schedule_export(sender, **kwargs):
    root = store_path()
    if root and getattr(settings, 'PERSONAL_CONTENT_AUTO_EXPORT', False) and not exports_suspended.get():
        def export_if_blog_exists():
            from blogs.models import Blog
            if Blog.objects.exists():
                export_content(root)
        # The database commit has already succeeded. Log export failures and
        # let the scheduled reconciliation command retry without failing saves.
        transaction.on_commit(export_if_blog_exists, robust=True)
