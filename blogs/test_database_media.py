import io
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, TestCase, override_settings

from blogs.models import Blog, Media, Post, StoredAsset, Stylesheet
from blogs.views.media import delete_selected_media, upload_files


@override_settings(PERSONAL_CONTENT_DIR=None, PERSONAL_BLOG_ACCESS='public', SECRET_KEY='test-key',
                   MIDDLEWARE=settings.MIDDLEWARE + ['blogs.private_access.PersonalBlogAccessMiddleware'])
@patch.dict(os.environ, {'SINGLE_BLOG': 'True', 'MAIN_SITE_HOSTS': 'example.com'})
class DatabaseMediaTests(TestCase):
    def setUp(self):
        Stylesheet.objects.create(identifier='default', css='body {}')
        self.user = get_user_model().objects.create_user(username='owner')
        self.blog = Blog.objects.create(user=self.user, title='Blog', subdomain='personal')

    def test_upload_and_public_read(self):
        image = SimpleUploadedFile('drawing.gif', b'GIF89a test', content_type='image/gif')
        url, = upload_files(self.blog, [image])
        self.assertTrue(Media.objects.filter(blog=self.blog, url=url).exists())
        response = self.client.get(urlsplit(url).path, HTTP_HOST='example.com')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'GIF89a test')
        self.assertEqual(response['Content-Type'], 'image/gif')
        self.assertIn('sandbox', response['Content-Security-Policy'])

    def test_delete_database_media_without_object_storage(self):
        url, = upload_files(self.blog, [SimpleUploadedFile('drawing.gif', b'GIF89a', content_type='image/gif')])
        request = RequestFactory().post('/', {'selected_media': [url]})
        request.user = self.user
        with patch.dict(os.environ, {'OBJECT_STORAGE_BUCKET': '', 'OBJECT_STORAGE_PUBLIC_URL': ''}):
            response = delete_selected_media(request, self.blog.subdomain)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Media.objects.exists())
        self.assertFalse(StoredAsset.objects.exists())

    @patch.dict(os.environ, {'OBJECT_STORAGE_BUCKET': 'bucket', 'OBJECT_STORAGE_PUBLIC_URL': 'https://images.example'})
    @patch('blogs.management.commands.import_media_to_database.boto3.session.Session')
    def test_import_local_and_remote_assets_and_repeat(self, session):
        url = 'https://images.example/personal/plantuml/chart.png'
        post = Post.objects.create(blog=self.blog, uid='post', title='Post', slug='post', content=f'![chart]({url})')
        Media.objects.create(blog=self.blog, url=url)
        client = session.return_value.client.return_value
        client.get_object.return_value = {'Body': io.BytesIO(b'PNG data'), 'ContentType': 'image/png'}
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'images').mkdir()
            (root / 'images' / 'old.png').write_bytes(b'old image')
            call_command('import_media_to_database', assets=directory, objects=True, verbosity=0)
            post.refresh_from_db()
            media = Media.objects.get()
            self.assertIn(media.url, post.content)
            self.assertEqual(bytes(StoredAsset.objects.get(path=urlsplit(media.url).path).data), b'PNG data')
            response = self.client.get('/static/migrated/images/old.png', HTTP_HOST='example.com')
            self.assertEqual(response.content, b'old image')
            call_command('import_media_to_database', assets=directory, objects=True, verbosity=0)
            self.assertEqual(StoredAsset.objects.count(), 2)
            self.assertEqual(client.get_object.call_count, 1)

    @patch.dict(os.environ, {'OBJECT_STORAGE_BUCKET': 'bucket', 'OBJECT_STORAGE_PUBLIC_URL': 'https://images.example'})
    @patch('blogs.management.commands.import_media_to_database.boto3.session.Session')
    def test_failed_import_rolls_back_local_assets_and_references(self, session):
        url = 'https://images.example/personal/old.png'
        Media.objects.create(blog=self.blog, url=url)
        session.return_value.client.return_value.get_object.side_effect = OSError('unavailable')
        with TemporaryDirectory() as directory:
            Path(directory, 'old.png').write_bytes(b'old')
            with self.assertRaises(CommandError):
                call_command('import_media_to_database', assets=directory, objects=True, verbosity=0)
        self.assertFalse(StoredAsset.objects.exists())
        self.assertEqual(Media.objects.get().url, url)
