import json
import os
from unittest.mock import MagicMock, patch
from urllib.parse import urlsplit

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TransactionTestCase, override_settings

from blogs import mcp_publishing as publishing
from blogs.models import Blog, Post, Stylesheet


@override_settings(PERSONAL_CONTENT_DIR=None, SECRET_KEY='mcp-test-key')
@patch.dict(os.environ, {'SINGLE_BLOG': 'True', 'MAIN_SITE_HOSTS': 'testserver'})
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
        tools = {tool.name: tool for tool in async_to_sync(server.list_tools)()}
        self.assertEqual(set(tools), {
            'get_blog_info', 'list_posts', 'list_tags', 'get_post', 'get_preview_link',
            'create_post', 'update_post', 'set_post_status',
        })
        self.assertTrue(tools['list_posts'].annotations.readOnlyHint)
        self.assertTrue(tools['set_post_status'].annotations.destructiveHint)
        self.assertEqual(set(tools['set_post_status'].inputSchema['required']), {
            'uid', 'expected_modified', 'status',
        })

    @patch('mcp.server.fastmcp.FastMCP.run', autospec=True)
    def test_tools_access_database_from_async_context(self, run):
        call_command('publishing_mcp', skip_checks=True)
        server = run.call_args.args[0]

        async def exercise():
            draft = await server._tool_manager.call_tool('create_post', {
                'title': 'Async', 'slug': 'async', 'content': 'body', 'tags': ['优选'],
            })
            self.assertEqual((await server._tool_manager.call_tool('get_post', {'slug': 'async'}))['content'], 'body')
            self.assertEqual(len(await server._tool_manager.call_tool('list_posts', {'status': 'draft'})), 1)
            updated = await server._tool_manager.call_tool('update_post', {
                'uid': draft['uid'], 'expected_modified': draft['last_modified'], 'content': 'updated',
            })
            self.assertFalse(updated['published'])
            self.assertEqual(updated['tags'], ['优选'])
            published = await server._tool_manager.call_tool('set_post_status', {
                'uid': draft['uid'], 'expected_modified': updated['last_modified'], 'status': 'published',
            })
            self.assertTrue(published['published'])
            unpublished = await server._tool_manager.call_tool('set_post_status', {
                'uid': draft['uid'], 'expected_modified': published['last_modified'], 'status': 'draft',
            })
            self.assertFalse(unpublished['published'])

        async_to_sync(exercise)()

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

    def test_draft_is_hidden_from_public_views_and_can_be_republished(self):
        published = publishing.save_post('精选文章', 'featured', '正文', ['优选'], True)
        paths = ('/', '/blog/', '/rss/', '/sitemap.xml')
        for path in paths:
            self.assertContains(self.client.get(path), '/featured/')
        self.assertContains(self.client.get('/featured/'), '正文')

        draft = publishing.set_post_status(published['uid'], published['last_modified'], 'draft')
        self.assertFalse(draft['published'])
        self.assertIsNone(draft['url'])
        self.assertNotIn('content', draft)
        self.assertEqual(draft['published_date'], published['published_date'])
        self.assertEqual(draft['tags'], ['优选'])
        self.assertEqual(publishing.get_post(published['uid'])['content'], '正文')
        self.assertEqual(self.client.get('/featured/').status_code, 404)
        for path in paths:
            self.assertNotContains(self.client.get(path), '/featured/')

        preview = urlsplit(publishing.get_preview_link(published['uid'])['url'])
        self.assertContains(self.client.get(f'{preview.path}?{preview.query}'), '正文')
        with self.assertRaisesMessage(ValueError, 'changed since'):
            publishing.set_post_status(published['uid'], published['last_modified'], 'published')
        republished = publishing.set_post_status(published['uid'], draft['last_modified'], 'published')
        self.assertEqual(republished['published_date'], published['published_date'])
        self.assertContains(self.client.get('/featured/'), '正文')

    def test_search_combines_exact_tags_status_kind_and_pagination(self):
        selected = publishing.save_post('数据库', 'db/锁', '事务与锁', ['优选', '数据库'], True)
        # The web editor stores Unicode tags escaped; MCP stores them unescaped.
        other = Post.objects.create(blog=self.blog, title='事务', slug='other', content='事务',
                                    all_tags=json.dumps(['优选', '其他']))
        publishing.save_post('匹配正文', 'near', '事务与锁', ['优选文章'], True)
        draft = publishing.save_post('草稿', 'draft', '事务', ['优选'], False)
        page = publishing.save_post('关于', 'about', '事务', ['优选'], True, is_page=True)

        hits = publishing.list_posts(query='事务', status='published', include_tags=['优选'], limit=1)
        self.assertEqual([hit['uid'] for hit in hits], [other.uid])
        second = publishing.list_posts(query='事务', status='published', include_tags=['优选'], offset=1)
        self.assertEqual([hit['uid'] for hit in second], [selected['uid']])
        self.assertNotIn('content', second[0])
        filtered = publishing.list_posts(include_tags=['优选'], exclude_tags=['其他'], status='published')
        self.assertEqual([hit['uid'] for hit in filtered], [selected['uid']])
        self.assertEqual([item['uid'] for item in publishing.list_posts(status='draft')], [draft['uid']])
        self.assertEqual([item['uid'] for item in publishing.list_posts(kind='page')], [page['uid']])
        self.assertTrue(publishing.get_post(slug='/about/')['is_page'])
        self.assertEqual(publishing.list_tags()[0], {'tag': '优选', 'count': 2})
        self.assertEqual(publishing.list_tags(status='draft'), [{'tag': '优选', 'count': 1}])
        self.assertEqual(publishing.get_blog_info()['articles_url'], 'https://testserver/blog/')

    def test_partial_update_preserves_publication_and_validates_target(self):
        page = publishing.save_post('关于', 'about', '正文', ['说明'], True, is_page=True)
        with patch('blogs.mcp_publishing.render_diagrams') as render:
            revised = publishing.save_post(uid=page['uid'], expected_modified=page['last_modified'], tags=[])
        render.assert_not_called()
        self.assertTrue(revised['published'])
        self.assertTrue(revised['is_page'])
        self.assertEqual(revised['content'], '正文')
        self.assertEqual(revised['tags'], [])
        with self.assertRaisesMessage(ValueError, 'exactly one'):
            publishing.get_post(uid=page['uid'], slug='about')
        with self.assertRaisesMessage(ValueError, 'not found'):
            publishing.get_post(uid='missing')
        with self.assertRaisesMessage(ValueError, 'reserved'):
            publishing.save_post('保留地址', 'rss', '正文')
        with self.assertRaisesMessage(ValueError, 'non-negative'):
            publishing.list_posts(offset=-1)

    def test_requires_single_blog_and_rejects_duplicate_slug(self):
        publishing.save_post('One', 'same', 'body', [], False)
        with self.assertRaisesMessage(ValueError, 'already in use'):
            publishing.save_post('Two', 'same', 'body', [], False)
        with patch.dict(os.environ, {'SINGLE_BLOG': 'False'}):
            with self.assertRaisesMessage(ValueError, 'SINGLE_BLOG'):
                publishing.list_posts()

    @patch.dict(os.environ, {'PLANTUML_JAR': '/plantuml.jar', 'MAIN_SITE_HOSTS': 'example.com'})
    @patch('blogs.mcp_publishing.subprocess.run')
    def test_diagrams_render_and_upload_before_save(self, run):
        run.return_value = MagicMock(stdout=b'\x89PNG\r\n\x1a\nimage')
        result = publishing.save_post('Diagram', 'diagram', 'Before\n```plantuml\n@startuml\nA -> B\n@enduml\n```\nAfter', [], True)
        self.assertIn('![PlantUML diagram](https://example.com/media-files/', result['content'])
        self.assertNotIn('```plantuml', result['content'])
        self.assertIn('-DPLANTUML_SECURITY_PROFILE=SECURE', run.call_args.args[0])
        from blogs.models import StoredAsset
        self.assertEqual(bytes(StoredAsset.objects.get().data), run.return_value.stdout)

    @patch.dict(os.environ, {'PLANTUML_JAR': '/plantuml.jar', 'MAIN_SITE_HOSTS': 'example.com'})
    @patch('blogs.mcp_publishing.store_asset', side_effect=OSError('storage failed'))
    @patch('blogs.mcp_publishing.subprocess.run')
    def test_upload_failure_does_not_publish(self, run, store):
        run.return_value = MagicMock(stdout=b'\x89PNG\r\n\x1a\nimage')
        with self.assertRaises(OSError):
            publishing.save_post('Diagram', 'diagram', '```plantuml\n@startuml\n@enduml\n```', [], True)
        self.assertFalse(Post.objects.filter(slug='diagram').exists())
