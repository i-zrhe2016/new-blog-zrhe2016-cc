import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from blogs.content_store import export_content
from blogs.models import Blog, Post, Stylesheet


class PersonalContentTests(TransactionTestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        settings = override_settings(PERSONAL_CONTENT_DIR=self.root, PERSONAL_CONTENT_AUTO_EXPORT=True)
        settings.enable()
        self.addCleanup(settings.disable)
        Stylesheet.objects.create(identifier='default', css='body { color: black; }')
        self.owner = get_user_model().objects.create_user(username='content-test')
        self.blog = Blog.objects.create(user=self.owner, title='My blog', subdomain='personal')

    def post(self, uid='example'):
        return Post.objects.create(blog=self.blog, uid=uid, title='中文文章', slug=uid,
                                   content='正文\n---\n代码和 Markdown\n', all_tags='["技术"]')

    def test_round_trip_preserves_files_dates_drafts_and_pages(self):
        post = self.post()
        self.post('draft')
        self.post('about')
        Post.objects.filter(uid='draft').update(publish=False, published_date=None, first_published_at=None)
        Post.objects.filter(uid='about').update(is_page=True)
        stamp = timezone.now().replace(microsecond=123456)
        Blog.objects.filter(pk=self.blog.pk).update(created_date=stamp, last_modified=stamp)
        Post.objects.filter(pk=post.pk).update(last_modified=stamp, first_published_at=stamp)
        export_content()
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file() and p.suffix in ('.md', '.json')}
        self.blog.delete()
        call_command('import_personal_content', str(self.root), owner=self.owner.username)
        export_content()
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file() and p.suffix in ('.md', '.json')}
        self.assertEqual(before, after)
        restored = Post.objects.get(uid='example')
        self.assertEqual(restored.content_length, len(restored.content))
        self.assertEqual(restored.last_modified, stamp)

    def test_save_delete_and_rollback_update_snapshot(self):
        post = self.post()
        path = self.root / 'posts/example.md'
        self.assertTrue(path.exists())
        post.content = 'edited'
        post.save()
        self.assertTrue(path.read_text(encoding='utf-8').endswith('edited'))
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.post('rolledback')
                raise RuntimeError('rollback')
        self.assertFalse((self.root / 'posts/rolledback.md').exists())
        post.delete()
        self.assertFalse(path.exists())
        self.assertEqual(json.loads((self.root / 'manifest.json').read_text()), [])

    def test_export_failure_does_not_undo_save_and_can_retry(self):
        with patch('blogs.content_store.export_content', side_effect=OSError('disk unavailable')):
            with self.assertLogs('django.db.backends.base', level='ERROR'):
                self.post()
        self.assertTrue(Post.objects.filter(uid='example').exists())
        export_content()
        self.assertTrue((self.root / 'posts/example.md').exists())

    def test_manifest_failure_keeps_old_referenced_files(self):
        self.post()
        # Simulate a bulk change and an export interrupted at manifest publish.
        Post.objects.filter(uid='example').update(uid='renamed')
        from blogs.content_store import _write
        def failing_write(path, text):
            if path.name == 'manifest.json':
                raise OSError('manifest unavailable')
            return _write(path, text)
        with patch('blogs.content_store._write', side_effect=failing_write):
            with self.assertRaises(OSError):
                export_content()
        for name in json.loads((self.root / 'manifest.json').read_text()):
            self.assertTrue((self.root / 'posts' / name).exists())
        export_content()
        self.assertFalse((self.root / 'posts/example.md').exists())

    def test_explicit_update_and_deletion(self):
        self.post()
        self.post('retained')
        with self.assertRaises(CommandError):
            call_command('import_personal_content', str(self.root), owner=self.owner.username)
        path = self.root / 'posts/example.md'
        text = path.read_text(encoding='utf-8')
        header, _ = text.split('\n---\n', 1)
        path.write_text(header + '\n---\nfile edit', encoding='utf-8')
        (self.root / 'manifest.json').write_text('["example.md"]')
        call_command('import_personal_content', str(self.root), owner=self.owner.username, update=True)
        self.assertEqual(Post.objects.get(uid='example').content, 'file edit')
        self.assertTrue(Post.objects.filter(uid='retained').exists())
        call_command('import_personal_content', str(self.root), owner=self.owner.username, update=True, delete_missing=True)
        self.assertFalse(Post.objects.filter(uid='retained').exists())
