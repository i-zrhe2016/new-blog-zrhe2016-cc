"""Import legacy local assets and optionally migrate configured object storage URLs."""
import mimetypes
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from blogs.models import Blog, Media, Post, StoredAsset
from blogs.stored_assets import store_asset
from blogs.views.media import get_storage_config


class Command(BaseCommand):
    help = 'Import local migrated assets and optionally configured object storage into the database.'

    def add_arguments(self, parser):
        parser.add_argument('--assets', help='Legacy assets directory (default: PERSONAL_CONTENT_DIR/assets)')
        parser.add_argument('--objects', action='store_true', help='Download and replace configured object storage URLs')

    @transaction.atomic
    def handle(self, *args, **options):
        root = Path(options['assets']) if options['assets'] else (Path(settings.PERSONAL_CONTENT_DIR) / 'assets' if settings.PERSONAL_CONTENT_DIR else None)
        if root is None or not root.is_dir():
            raise CommandError('Legacy assets directory does not exist; supply --assets.')
        count = 0
        for file in root.rglob('*'):
            if file.is_symlink():
                raise CommandError(f'Symlinks are not supported: {file}')
            if file.is_file():
                path = '/static/migrated/' + file.relative_to(root).as_posix()
                data = file.read_bytes()
                existing = StoredAsset.objects.filter(path=path).first()
                if existing and bytes(existing.data) != data:
                    raise CommandError(f'Existing database asset differs: {path}')
                if not existing:
                    StoredAsset.objects.create(path=path, data=data, content_type=mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
                    count += 1
        self.stdout.write(f'Imported {count} local assets.')
        if not options['objects']:
            return
        config = get_storage_config()
        if not config['bucket'] or not config['public_url']:
            raise CommandError('OBJECT_STORAGE_BUCKET and OBJECT_STORAGE_PUBLIC_URL are required.')
        prefix = config['public_url'] + '/'
        client = boto3.session.Session().client('s3', endpoint_url=config['endpoint_url'], region_name=config['region'], aws_access_key_id=config['access_key_id'], aws_secret_access_key=config['secret_access_key'])
        pattern = re.compile(re.escape(prefix) + r'[^\s\)\]<>"\']+')
        total = 0
        for blog in Blog.objects.all():
            fields = ('content', 'nav', 'meta_image', 'favicon', 'header_directive', 'footer_directive', 'custom_styles', 'post_template')
            post_fields = ('content', 'meta_image')
            posts = list(blog.posts.all())
            media = list(blog.media.all())
            urls = {m.url for m in media if m.url.startswith(prefix)}
            for obj, names in [(blog, fields)] + [(post, post_fields) for post in posts]:
                for name in names:
                    urls.update(pattern.findall(getattr(obj, name) or ''))
            replacements = {}
            for url in sorted(urls):
                key = unquote(urlsplit(url).path[len(urlsplit(prefix).path):])
                if not key.startswith(blog.subdomain + '/'):
                    raise CommandError(f'Object does not belong to blog {blog.subdomain}: {url}')
                try:
                    result = client.get_object(Bucket=config['bucket'], Key=key)
                    data = result['Body'].read()
                except Exception as exc:
                    raise CommandError(f'Could not download {url}: {exc}') from exc
                filename = Path(key).name
                replacements[url] = store_asset(data, result.get('ContentType') or mimetypes.guess_type(filename)[0], filename, blog)
                total += 1
            # Longer URLs first so one filename cannot partially replace another.
            for obj, names in [(blog, fields)] + [(post, post_fields) for post in posts] + [(m, ('url',)) for m in media]:
                updates = {}
                for name in names:
                    value = getattr(obj, name)
                    if not value:
                        continue
                    for old in sorted(replacements, key=len, reverse=True):
                        value = value.replace(old, replacements[old])
                    if value != getattr(obj, name):
                        updates[name] = value
                if updates:
                    type(obj).objects.filter(pk=obj.pk).update(**updates)
        self.stdout.write(f'Imported {total} object storage files and updated their references.')
