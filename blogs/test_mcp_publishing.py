import os
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TransactionTestCase, override_settings

from blogs import mcp_publishing as publishing
from blogs.models import Blog, Post, Stylesheet


@override_settings(PERSONAL_CONTENT_DIR=None)
@patch.dict(os.environ, {'SINGLE_BLOG': 'True'})
class PublishingTests(TransactionTestCase):
    def setUp(self):
        Stylesheet.objects.create(identifier='default', css='body {}')
        owner = get_user_model().objects.create_user(username='mcp-test')
        self.blog = Blog.objects.create(user=owner, title='Blog', subdomain='personal')

    @patch('mcp.server.fastmcp.FastMCP.run', autospec=True)
    def test_command_registers_stdio_tools(self, run):
        call_command('publishing_mcp', skip_checks=True)
        server = run.call_args.args[0]
        self.assertEqual(run.call_args.kwargs['transport'], 'stdio')
        self.assertEqual(set(server._tool_manager._tools), {'list_posts', 'get_post', 'create_post', 'update_post'})

    def test_create_draft_then_publish_and_reject_stale_revision(self):
        draft = publishing.save_post('标题', 'hello', '正文', ['技术'], False)
        self.assertFalse(draft['published'])
        self.assertIsNone(Post.objects.get(uid=draft['uid']).published_date)
        updated = publishing.save_post('标题', 'hello', '新正文', ['技术'], True,
                                       draft['uid'], draft['last_modified'])
        self.assertTrue(updated['published'])
        self.assertIsNotNone(Post.objects.get(uid=draft['uid']).published_date)
        with self.assertRaisesMessage(ValueError, 'changed since'):
            publishing.save_post('标题', 'hello', '旧正文', [], True, draft['uid'], draft['last_modified'])
        self.assertEqual(publishing.get_post(draft['uid'])['content'], '新正文')

    def test_requires_single_blog_and_rejects_duplicate_slug(self):
        publishing.save_post('One', 'same', 'body', [], False)
        with self.assertRaisesMessage(ValueError, 'already in use'):
            publishing.save_post('Two', 'same', 'body', [], False)
        with patch.dict(os.environ, {'SINGLE_BLOG': 'False'}):
            with self.assertRaisesMessage(ValueError, 'SINGLE_BLOG'):
                publishing.list_posts()

    @patch.dict(os.environ, {'PLANTUML_JAR': '/plantuml.jar', 'OBJECT_STORAGE_BUCKET': 'bucket',
                             'OBJECT_STORAGE_PUBLIC_URL': 'https://images.example'})
    @patch('blogs.mcp_publishing.boto3.session.Session')
    @patch('blogs.mcp_publishing.subprocess.run')
    def test_diagrams_render_and_upload_before_save(self, run, session):
        run.return_value = MagicMock(stdout=b'\x89PNG\r\n\x1a\nimage')
        result = publishing.save_post('Diagram', 'diagram', 'Before\n```plantuml\n@startuml\nA -> B\n@enduml\n```\nAfter', [], True)
        self.assertIn('![PlantUML diagram](https://images.example/personal/plantuml/', result['content'])
        self.assertNotIn('```plantuml', result['content'])
        self.assertIn('-DPLANTUML_SECURITY_PROFILE=SECURE', run.call_args.args[0])
        session.return_value.client.return_value.put_object.assert_called_once()

    @patch.dict(os.environ, {'PLANTUML_JAR': '/plantuml.jar', 'OBJECT_STORAGE_BUCKET': 'bucket',
                             'OBJECT_STORAGE_PUBLIC_URL': 'https://images.example'})
    @patch('blogs.mcp_publishing.boto3.session.Session')
    @patch('blogs.mcp_publishing.subprocess.run')
    def test_upload_failure_does_not_publish(self, run, session):
        run.return_value = MagicMock(stdout=b'\x89PNG\r\n\x1a\nimage')
        session.return_value.client.return_value.put_object.side_effect = OSError('upload failed')
        with self.assertRaises(OSError):
            publishing.save_post('Diagram', 'diagram', '```plantuml\n@startuml\n@enduml\n```', [], True)
        self.assertFalse(Post.objects.filter(slug='diagram').exists())
