"""Import the Astro blog's Markdown into the personal Bear Blog installation.

Run extraction with system Python and import with the app's Python, both in
isolated mode. The downloaded source directory is treated only as data.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys


def extract(source, output):
    import yaml

    from urllib.request import Request, urlopen

    source = Path(source)
    assets = Path(output).parent / 'migration-assets' / 'diagrams' / 'plantuml'
    assets.mkdir(parents=True, exist_ok=True)
    posts = []
    for path in sorted((source / 'src/content/posts').glob('*.md')):
        parts = path.read_text(encoding='utf-8').split('---', 2)
        if len(parts) != 3 or parts[0].strip():
            raise ValueError(f'Invalid front matter: {path.name}')
        metadata = yaml.safe_load(parts[1])
        body = parts[2].lstrip('\n')

        def diagram(match):
            text = match.group(2).replace('\r\n', '\n').replace('\r', '\n').strip() + '\n'
            digest = hashlib.sha256(('1.2026.8\n' + text).encode()).hexdigest()
            name = '-'.join(digest[i:i + 8] for i in range(0, 64, 8)) + '.svg'
            if not (source / 'public/diagrams/plantuml' / name).is_file():
                request = Request('https://blog.zrhe2016.cc/diagrams/plantuml/' + name, headers={'User-Agent': 'curl/8.0'})
                with urlopen(request, timeout=30) as response:
                    image = response.read(5_000_001)
                if len(image) > 5_000_000 or b'<svg' not in image:
                    raise ValueError(f'Invalid diagram: {name}')
                (assets / name).write_bytes(image)
            alt = match.group(1).strip() or 'PlantUML diagram'
            return f'![{alt}](/static/migrated/diagrams/plantuml/{name})'

        body = re.sub(r'^```plantuml([^\n]*)\n(.*?)^```\s*$', diagram, body, flags=re.MULTILINE | re.DOTALL)
        body = body.replace('/images/bearblog/', '/static/migrated/images/bearblog/')
        date = metadata['pubDatetime']
        posts.append({
            'slug': path.stem,
            'title': str(metadata['title']),
            'description': str(metadata.get('description') or ''),
            'date': date.isoformat() if isinstance(date, (datetime.date, datetime.datetime)) else str(date),
            'draft': bool(metadata.get('draft', False)),
            'tags': metadata.get('tags') or [],
            'content': body,
        })
    about = (source / 'src/content/pages/about.md').read_text(encoding='utf-8').split('---', 2)[2].lstrip('\n')
    Path(output).write_text(json.dumps({'posts': posts, 'about': about}, ensure_ascii=False), encoding='utf-8')
    print(f'Prepared {len(posts)} posts; {sum(p["draft"] for p in posts)} drafts')


def load(data_file):
    sys.path.insert(0, '/app')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.deployment_settings')
    import django
    django.setup()
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from django.utils.dateparse import parse_datetime
    from django.utils.timezone import make_aware, is_naive
    from blogs.models import Blog, Post

    data = json.loads(Path(data_file).read_text(encoding='utf-8'))
    with transaction.atomic():
        if Blog.objects.exists() or get_user_model().objects.exists():
            raise RuntimeError('Database is not empty; refusing to overwrite existing content or users')
        owner = get_user_model().objects.create_user(username='zrhe2016', email='zrhe2016@gmail.com', password=None)
        blog = Blog.objects.create(user=owner, title='zrhe2016', subdomain='personal', content='', lang='zh-CN', meta_description='只写有意思的。技术、工具与日常记录。', nav='[首页](/) [文章](/blog/) [关于](/about/)')
        for item in data['posts']:
            published = parse_datetime(item['date'])
            if published is None:
                raise ValueError(f'Invalid publication date: {item["slug"]}')
            if is_naive(published):
                published = make_aware(published, datetime.timezone.utc)
            Post.objects.create(blog=blog, title=item['title'], slug=item['slug'], alias='posts/' + item['slug'], content=item['content'], published_date=published, first_published_at=published if not item['draft'] else None, publish=not item['draft'], meta_description=item['description'][:200], all_tags=json.dumps(item['tags'], ensure_ascii=False), discoverable=False)
        Post.objects.create(blog=blog, title='关于我', slug='about', content=data['about'], is_page=True, discoverable=False)
        blog.update_all_tags()
        blog.save(update_fields=['all_tags'])
    print(f'Imported {len(data["posts"])} posts and the about page; owner password is unset')


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == 'extract':
        extract(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 3 and sys.argv[1] == 'load':
        load(sys.argv[2])
    else:
        raise SystemExit('Usage: migrate_blog_content.py extract SOURCE OUTPUT | load JSON')
