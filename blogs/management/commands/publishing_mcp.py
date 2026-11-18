from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Run the personal-blog MCP server over stdio (use through Tailscale SSH).'

    def handle(self, *args, **options):
        from mcp.server.fastmcp import FastMCP
        from blogs import mcp_publishing

        try:
            mcp_publishing.personal_blog()
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        server = FastMCP('Bear Blog publishing')

        @server.tool()
        def list_posts() -> list[dict]:
            """List up to 200 recent articles and drafts."""
            return mcp_publishing.list_posts()

        @server.tool()
        def get_post(uid: str) -> dict:
            """Read an article, including its content and revision timestamp."""
            return mcp_publishing.get_post(uid)

        @server.tool()
        def create_post(title: str, slug: str, content: str, tags: list[str], published: bool = False) -> dict:
            """Create an article; defaults to a draft. PlantUML fenced blocks become PNG images."""
            return mcp_publishing.save_post(title, slug, content, tags, published)

        @server.tool()
        def update_post(uid: str, expected_modified: str, title: str, slug: str, content: str,
                        tags: list[str], published: bool = False) -> dict:
            """Replace an article's fields. Supply the last_modified value from get_post."""
            return mcp_publishing.save_post(title, slug, content, tags, published, uid, expected_modified)

        server.run(transport='stdio')
