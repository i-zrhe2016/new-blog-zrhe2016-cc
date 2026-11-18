import json
from pathlib import Path
import re

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from blogs.content_store import BLOG_FIELDS, POST_FIELDS, suspend_exports
from blogs.models import Blog, Post


class Command(BaseCommand):
    help = 'Restore versioned content, or explicitly apply file edits to an existing blog.'

    def add_arguments(self, parser):
        parser.add_argument('directory')
        parser.add_argument('--owner', required=True, help='Existing Django username')
        parser.add_argument('--update', action='store_true', help='Apply files to an existing blog')
        parser.add_argument('--delete-missing', action='store_true', help='With --update, delete posts absent from the manifest')

    def handle(self, *args, **options):
        root = Path(options['directory'])
        try:
            if options['delete_missing'] and not options['update']:
                raise ValueError('--delete-missing requires --update')
            meta = json.loads((root / 'blog.json').read_text(encoding='utf-8'))
            manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
            if not isinstance(meta, dict) or set(meta) != set(BLOG_FIELDS):
                raise ValueError('Invalid blog metadata')
            if not isinstance(manifest, list) or any(not isinstance(name, str) for name in manifest):
                raise ValueError('Invalid manifest')
            if len(manifest) != len(set(manifest)):
                raise ValueError('Duplicate manifest entry')
            entries = []
            for name in manifest:
                if not re.fullmatch(r'[A-Za-z0-9_-]+\.md', name):
                    raise ValueError('Invalid content filename')
                text = (root / 'posts' / name).read_text(encoding='utf-8')
                parts = text.split('\n---\n', 1)
                if len(parts) != 2 or not parts[0].startswith('---\n'):
                    raise ValueError(f'Invalid article format: {name}')
                data = json.loads(parts[0][4:])
                if not isinstance(data, dict) or set(data) != set(POST_FIELDS) or data['uid'] + '.md' != name:
                    raise ValueError(f'Invalid article metadata: {name}')
                tags = json.loads(data['all_tags'])
                if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
                    raise ValueError(f'Invalid tags: {name}')
                # Convert ISO timestamps, retaining full microsecond precision.
                data = {key: Post._meta.get_field(key).to_python(value) for key, value in data.items()}
                entries.append((data, parts[1]))
            meta = {key: Blog._meta.get_field(key).to_python(value) for key, value in meta.items()}
            owner = get_user_model().objects.get(username=options['owner'])
            # Do not export back over the input files while restoring them.
            with suspend_exports(), transaction.atomic():
                blogs = list(Blog.objects.select_for_update().all()[:2])
                if len(blogs) > 1 or (blogs and blogs[0].user_id != owner.pk):
                    raise ValueError('Restore requires one blog belonging to the specified owner')
                if blogs and blogs[0].posts.exists() and not options['update']:
                    raise ValueError('Blog has existing posts; use --update to apply file edits')
                dates = {key: meta[key] for key in ('created_date', 'last_modified')}
                if blogs:
                    blog = blogs[0]
                    for key, value in meta.items():
                        setattr(blog, key, value)
                    blog.save()
                else:
                    blog = Blog.objects.create(user=owner, **meta)
                uids = []
                for data, body in entries:
                    data = dict(data, content=body, content_length=len(body))
                    uid = data['uid']
                    uids.append(uid)
                    existing = list(blog.posts.filter(uid=uid)[:2])
                    if len(existing) > 1:
                        raise ValueError(f'Duplicate database post UID: {uid}')
                    if existing:
                        Post.objects.filter(pk=existing[0].pk).update(**data)
                    else:
                        # bulk_create avoids slug/date normalization in Post.save.
                        post = Post(blog=blog, **data)
                        Post.objects.bulk_create([post])
                        Post.objects.filter(pk=post.pk).update(last_modified=data['last_modified'])
                if options['delete_missing']:
                    blog.posts.exclude(uid__in=uids).delete()
                blog.save()  # Rebuild derived tags and last_posted.
                Blog.objects.filter(pk=blog.pk).update(**dates)
        except (OSError, ValueError, KeyError, TypeError, get_user_model().DoesNotExist) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f'Restored {len(entries)} articles and pages')
