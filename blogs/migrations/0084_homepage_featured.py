from django.db import migrations, models


HOMEPAGE_FEATURED_SLUGS = (
    'mihomo-tailscale-magicdns-conflict',
    'magpie-deepseek-4-1-claude-code',
    'dynamic-cpu-for-build-image',
    'nacos-mysql-8044',
    'dd',
    'helm-install-prometheus-stack',
    'install-asciima-and-set-alias',
    'k9s',
    'k8s-new',
    'phash',
    'barkpy',
    'podman',
    'codexvps',
    'ttydshellweb',
    'nginxcf-worker-blog',
)


def mark_homepage_articles(apps, schema_editor):
    Blog = apps.get_model('blogs', 'Blog')
    Post = apps.get_model('blogs', 'Post')
    database = schema_editor.connection.alias
    blog = Blog.objects.using(database).filter(subdomain='personal').first()
    if not blog:
        return

    eligible = Post.objects.using(database).filter(
        blog_id=blog.pk,
        slug__in=HOMEPAGE_FEATURED_SLUGS,
        publish=True,
        is_page=False,
    )
    found = set(eligible.values_list('slug', flat=True))
    missing = set(HOMEPAGE_FEATURED_SLUGS) - found
    if missing:
        raise RuntimeError(
            'Homepage articles are missing or unpublished: ' + ', '.join(sorted(missing))
        )
    eligible.update(homepage_featured=True)


def unmark_homepage_articles(apps, schema_editor):
    Blog = apps.get_model('blogs', 'Blog')
    Post = apps.get_model('blogs', 'Post')
    database = schema_editor.connection.alias
    blog = Blog.objects.using(database).filter(subdomain='personal').first()
    if not blog:
        return
    Post.objects.using(database).filter(
        blog_id=blog.pk,
        slug__in=HOMEPAGE_FEATURED_SLUGS,
        homepage_featured=True,
    ).update(homepage_featured=False)


class Migration(migrations.Migration):
    dependencies = [
        ('blogs', '0083_storedasset'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='homepage_featured',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.RunPython(mark_homepage_articles, unmark_homepage_articles),
    ]
