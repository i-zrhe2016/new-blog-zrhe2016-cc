"""Publishing operations used by the private, stdio-only MCP server."""
from collections import Counter
import hashlib
import json
import os
import re
import subprocess
from typing import Literal
from urllib.parse import quote, urlencode

from django.db import transaction
from django.db.models import Q
from django.urls import resolve
from django.utils import timezone

from blogs.helpers import filter_posts_by_tags
from blogs.models import Blog, Post
from blogs.stored_assets import store_asset

DIAGRAM = re.compile(r'^```plantuml[^\n]*\r?\n(.*?)^```[ \t]*$', re.MULTILINE | re.DOTALL | re.IGNORECASE)
SLUG = re.compile(r'^[\w-]+(?:/[\w-]+)*$', re.UNICODE)


def personal_blog():
    if os.getenv('SINGLE_BLOG') != 'True':
        raise ValueError('MCP publishing requires SINGLE_BLOG=True.')
    blogs = list(Blog.objects.all()[:2])
    if len(blogs) != 1:
        raise ValueError('MCP publishing requires exactly one blog.')
    return blogs[0]


def render_diagrams(content, blog):
    def render(match):
        source = match.group(1).strip()
        if len(source) > 100000:
            raise ValueError('PlantUML diagram exceeds 100000 characters.')
        jar = os.getenv('PLANTUML_JAR')
        if not jar:
            raise ValueError('PLANTUML_JAR must point to a local PlantUML jar.')
        try:
            result = subprocess.run(
                ['java', '-DPLANTUML_SECURITY_PROFILE=SECURE', '-jar', jar, '-charset', 'UTF-8', '-tpng', '-pipe'],
                input=source.encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=30, check=True,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError('PlantUML rendering failed; verify the diagram and local Java/PlantUML installation.') from exc
        if not result.stdout.startswith(b'\x89PNG\r\n\x1a\n') or len(result.stdout) > 10 * 1024 * 1024:
            raise ValueError('PlantUML did not produce a valid PNG within the size limit.')
        digest = hashlib.sha256(result.stdout).hexdigest()
        url = store_asset(result.stdout, 'image/png', f'{digest}.png', blog)
        return f'![PlantUML diagram]({url})'

    output = DIAGRAM.sub(render, content)
    if re.search(r'^```plantuml\b', output, re.MULTILINE | re.IGNORECASE):
        raise ValueError('Unclosed PlantUML code block.')
    return output


PostStatus = Literal['all', 'draft', 'published']
PostKind = Literal['all', 'article', 'page']


def site_url(blog, path=''):
    return f'{blog.useful_domain}/{quote(path.strip("/"))}/' if path else f'{blog.useful_domain}/'


def describe(post, include_content=False):
    result = {
        'uid': post.uid, 'title': post.title, 'slug': post.slug, 'published': post.publish,
        'tags': json.loads(post.all_tags), 'last_modified': post.last_modified.isoformat(),
        'is_page': post.is_page, 'discoverable': post.discoverable,
        'published_date': post.published_date.isoformat() if post.published_date else None,
        'url': site_url(post.blog, post.slug) if post.publish else None,
    }
    if include_content:
        result['content'] = post.content
    return result


def get_blog_info():
    blog = personal_blog()
    return {
        'title': blog.title, 'lang': blog.lang, 'home_url': site_url(blog),
        'articles_url': site_url(blog, blog.blog_path or 'blog'),
        'feed_url': site_url(blog, blog.rss_alias or 'rss'),
        'navigation': blog.nav, 'post_template': blog.post_template,
    }


def select_posts(blog, status, kind):
    if status not in ('all', 'draft', 'published') or kind not in ('all', 'article', 'page'):
        raise ValueError('Unknown post status or kind.')
    posts = blog.posts.all()
    if status != 'all':
        posts = posts.filter(publish=(status == 'published'))
    if kind != 'all':
        posts = posts.filter(is_page=(kind == 'page'))
    return posts


def validate_pagination(limit, offset):
    if not 1 <= limit <= 200 or offset < 0:
        raise ValueError('limit must be 1–200 and offset must be non-negative.')


def clean_tags(tags):
    if len(tags) > 100 or any(not isinstance(tag, str) or len(tag) > 100 for tag in tags):
        raise ValueError('Tags must be strings of at most 100 characters (maximum 100 tags).')
    return list(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))


def list_posts(query='', status='all', kind='article', include_tags=(), exclude_tags=(), limit=200, offset=0):
    validate_pagination(limit, offset)
    query = query.strip()
    if len(query) > 200:
        raise ValueError('Search query exceeds 200 characters.')
    posts = select_posts(personal_blog(), status, kind).defer('content').order_by('-last_modified', '-pk')
    if query:
        posts = posts.filter(Q(title__icontains=query) | Q(slug__icontains=query) | Q(content__icontains=query))
    if include_tags or exclude_tags:
        posts = filter_posts_by_tags(posts, clean_tags(include_tags), clean_tags(exclude_tags))
    return [describe(post) for post in posts[offset:offset + limit]]


def list_tags(status='published', limit=100, offset=0):
    validate_pagination(limit, offset)
    counts = Counter()
    for tags in select_posts(personal_blog(), status, 'article').values_list('all_tags', flat=True).iterator():
        counts.update(set(json.loads(tags)))
    entries = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [{'tag': tag, 'count': count} for tag, count in entries[offset:offset + limit]]


def find_post(posts, uid='', slug=''):
    if bool(uid) == bool(slug):
        raise ValueError('Provide exactly one of uid or slug.')
    try:
        return posts.get(uid=uid) if uid else posts.get(slug__iexact=slug.strip().strip('/'))
    except Post.DoesNotExist as exc:
        raise ValueError('Article or page not found.') from exc
    except Post.MultipleObjectsReturned as exc:
        raise ValueError('More than one item matches; use a unique UID.') from exc


def get_post(uid='', slug=''):
    return describe(find_post(personal_blog().posts, uid, slug), True)


def get_preview_link(uid):
    post = find_post(personal_blog().posts, uid)
    url = site_url(post.blog, post.slug)
    if not post.publish:
        url += '?' + urlencode({'token': post.token})
    return {'uid': post.uid, 'url': url, 'published': post.publish}


def set_post_status(uid, expected_modified, status):
    if status not in ('draft', 'published'):
        raise ValueError('Status must be draft or published.')
    return save_post(uid=uid, expected_modified=expected_modified, published=(status == 'published'),
                     include_content=False)


def save_post(title=None, slug=None, content=None, tags=None, published=None, uid=None,
              expected_modified='', *, is_page=False, include_content=True):
    blog = personal_blog()
    if uid is not None and (not uid.strip() or not expected_modified):
        raise ValueError('Updating requires a UID and the last_modified value returned by get_post.')
    if uid is None and None in (title, slug, content):
        raise ValueError('Creating an article requires a title, slug and content.')
    if all(value is None for value in (title, slug, content, tags, published)):
        raise ValueError('Provide at least one field to update.')
    if title is not None:
        title = title.strip()
        if not 1 <= len(title) <= 200:
            raise ValueError('Title must contain 1–200 characters.')
    if slug is not None:
        slug = slug.strip().lower()
        if len(slug) > 200 or not SLUG.fullmatch(slug):
            raise ValueError('Slug must contain only letters, digits, hyphens, underscores and internal slashes.')
    if content is not None and len(content) > 1000000:
        raise ValueError('Content exceeds 1000000 characters.')
    if tags is not None:
        tags = clean_tags(tags)
    with transaction.atomic():
        if uid is not None:
            post = find_post(blog.posts.select_for_update(), uid)
            if post.last_modified.isoformat() != expected_modified:
                raise ValueError('Post changed since it was read; fetch it again before updating.')
        else:
            if blog.posts.count() >= 5000:
                raise ValueError('The blog has reached its 5000 post limit.')
            post = Post(blog=blog, publish=False, is_page=is_page)
        if slug is not None and slug != post.slug:
            if slug in {'blog', blog.blog_path.lower(), blog.rss_alias.lower()} or resolve(f'/{slug}/').view_name != 'post':
                raise ValueError('This slug is reserved for a site route.')
            if blog.posts.filter(Q(slug__iexact=slug) | Q(alias__iexact=slug)).exclude(pk=post.pk).exists():
                raise ValueError('This slug is already in use.')
            post.slug = slug
        if title is not None:
            post.title = title
        if content is not None:
            post.content = render_diagrams(content, blog)
        if tags is not None:
            post.all_tags = json.dumps(tags, ensure_ascii=False)
        if published is not None:
            post.publish = published
        post.last_modified = timezone.now()
        post.save()
    return describe(post, include_content)
