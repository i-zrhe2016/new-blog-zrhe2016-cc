"""Publishing operations used by the private, stdio-only MCP server."""
import hashlib
import json
import os
import re
import subprocess

from django.db import transaction
from django.utils import timezone

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


def describe(post, include_content=False):
    result = {'uid': post.uid, 'title': post.title, 'slug': post.slug, 'published': post.publish,
              'tags': json.loads(post.all_tags), 'last_modified': post.last_modified.isoformat()}
    if include_content:
        result['content'] = post.content
    return result


def list_posts():
    blog = personal_blog()
    return [describe(post) for post in blog.posts.filter(is_page=False).order_by('-last_modified')[:200]]


def get_post(uid):
    return describe(Post.objects.get(blog=personal_blog(), uid=uid, is_page=False), True)


def save_post(title, slug, content, tags, published, uid='', expected_modified=''):
    blog = personal_blog()
    title, slug = title.strip(), slug.strip().lower()
    if not title or len(title) > 200:
        raise ValueError('Title must contain 1–200 characters.')
    if not slug or len(slug) > 200 or not SLUG.fullmatch(slug):
        raise ValueError('Slug must contain only letters, digits, hyphens, underscores and internal slashes.')
    if len(content) > 1000000:
        raise ValueError('Content exceeds 1000000 characters.')
    if len(tags) > 100 or any(not isinstance(tag, str) or len(tag) > 100 for tag in tags):
        raise ValueError('Tags must be strings of at most 100 characters (maximum 100 tags).')
    if uid and not expected_modified:
        raise ValueError('Updating requires the last_modified value returned by get_post.')
    with transaction.atomic():
        content = render_diagrams(content, blog)
        if uid:
            post = Post.objects.get(blog=blog, uid=uid, is_page=False)
            if post.last_modified.isoformat() != expected_modified:
                raise ValueError('Post changed since it was read; fetch it again before updating.')
        else:
            if blog.posts.count() >= 5000:
                raise ValueError('The blog has reached its 5000 post limit.')
            post = Post(blog=blog)
        if Post.objects.filter(blog=blog, slug__iexact=slug).exclude(pk=post.pk).exists():
            raise ValueError('This slug is already in use.')
        post.title, post.slug, post.content = title, slug, content
        post.all_tags = json.dumps(list(dict.fromkeys(tag.strip() for tag in tags if tag.strip())), ensure_ascii=False)
        post.publish = published
        post.last_modified = timezone.now()
        post.save()
    return describe(post, True)
