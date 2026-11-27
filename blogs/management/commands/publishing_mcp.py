from typing import Literal

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Run the personal-blog MCP server over stdio (use through Tailscale SSH).'

    def handle(self, *args, **options):
        from asgiref.sync import sync_to_async
        from mcp.server.fastmcp import FastMCP
        from mcp.types import ToolAnnotations
        from blogs import mcp_publishing as publishing
        from blogs.mcp_publishing import PostKind, PostStatus

        try:
            publishing.personal_blog()
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        server = FastMCP('Bear Blog publishing')
        read_only = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
        edit = ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False)

        @server.tool(annotations=read_only)
        async def get_blog_info() -> dict:
            """Read the blog's configured URLs, navigation, language and writing template."""
            return await sync_to_async(publishing.get_blog_info)()

        @server.tool(annotations=read_only)
        async def list_posts(query: str = '', status: PostStatus = 'all', kind: PostKind = 'article',
                             include_tags: list[str] | None = None, exclude_tags: list[str] | None = None,
                             limit: int = 200, offset: int = 0) -> list[dict]:
            """List by newest edit, optionally searching title, slug or Markdown. Require all include_tags
            and exclude any exclude_tags (exact matches). Use include_tags=['优选'] with status='published'
            to find articles tagged for the personal blog homepage. limit: 1–200; offset: 0-based."""
            return await sync_to_async(publishing.list_posts)(
                query, status, kind, include_tags or (), exclude_tags or (), limit, offset)

        @server.tool(annotations=read_only)
        async def list_tags(status: PostStatus = 'published', limit: int = 100, offset: int = 0) -> list[dict]:
            """List article tags and counts for the selected publication status, most-used first."""
            return await sync_to_async(publishing.list_tags)(status, limit, offset)

        @server.tool(annotations=read_only)
        async def get_post(uid: str = '', slug: str = '') -> dict:
            """Read an article or page, including its Markdown and revision. Supply exactly one of uid or slug."""
            return await sync_to_async(publishing.get_post)(uid, slug)

        @server.tool(annotations=read_only)
        async def get_preview_link(uid: str) -> dict:
            """Get a link for a requested preview. For a draft, anyone with the link can read it; don't share it publicly."""
            return await sync_to_async(publishing.get_preview_link)(uid)

        @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
        async def create_post(title: str, slug: str, content: str, tags: list[str] | None = None,
                              published: bool = False, is_page: bool = False) -> dict:
            """Create an article or standalone page. Defaults to a draft. PlantUML fenced blocks become PNG images."""
            return await sync_to_async(publishing.save_post)(title, slug, content, tags, published, is_page=is_page)

        @server.tool(annotations=edit)
        async def update_post(uid: str, expected_modified: str, title: str | None = None,
                              slug: str | None = None, content: str | None = None,
                              tags: list[str] | None = None, published: bool | None = None) -> dict:
            """Edit only supplied fields; omit unchanged fields, including published. An empty tags list clears
            tags. Supply the last_modified value from get_post. To change only visibility, use set_post_status."""
            return await sync_to_async(publishing.save_post)(title, slug, content, tags, published, uid, expected_modified)

        @server.tool(annotations=edit)
        async def set_post_status(uid: str, expected_modified: str, status: Literal['draft', 'published']) -> dict:
            """Hide a published article or page by setting status='draft', or publish it with status='published'.
            Keeps the slug, content, tags and previous publication date. Supply last_modified from get_post."""
            return await sync_to_async(publishing.set_post_status)(uid, expected_modified, status)

        server.run(transport='stdio')
