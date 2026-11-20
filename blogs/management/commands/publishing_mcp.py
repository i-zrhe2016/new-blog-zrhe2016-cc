from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Run the personal-blog MCP server over stdio (use through Tailscale SSH).'

    def handle(self, *args, **options):
        from asgiref.sync import sync_to_async
        from mcp.server.fastmcp import FastMCP
        from blogs import mcp_publishing

        try:
            mcp_publishing.personal_blog()
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        server = FastMCP('Bear Blog publishing')

        @server.tool()
        async def list_posts() -> list[dict]:
            """List up to 200 recent articles and drafts."""
            return await sync_to_async(mcp_publishing.list_posts, thread_sensitive=True)()

        @server.tool()
        async def get_post(uid: str) -> dict:
            """Read an article, including its content and revision timestamp."""
            return await sync_to_async(mcp_publishing.get_post, thread_sensitive=True)(uid)

        @server.tool()
        async def create_post(title: str, slug: str, content: str, tags: list[str], published: bool = False) -> dict:
            """Create an article; defaults to a draft. PlantUML fenced blocks become PNG images."""
            return await sync_to_async(mcp_publishing.save_post, thread_sensitive=True)(title, slug, content, tags, published)

        @server.tool()
        async def update_post(uid: str, expected_modified: str, title: str, slug: str, content: str,
                              tags: list[str], published: bool = False) -> dict:
            """Replace an article's fields. Supply the last_modified value from get_post."""
            return await sync_to_async(mcp_publishing.save_post, thread_sensitive=True)(
                title, slug, content, tags, published, uid, expected_modified)

        server.run(transport='stdio')
