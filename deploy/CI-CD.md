# CI/CD

GitHub Actions runs Django and content-sync tests for pull requests and pushes to `master`. After the tests pass, a push to `master` builds and deploys the application to the existing `/opt/bearblog` server through Tailscale SSH. A manual run on `master` is also available in Actions. Production deployments are serialized, and an outdated commit is refused before deployment.

## Configuration

The repository needs these GitHub Actions secrets:

- `TAILSCALE_OAUTH_CLIENT_ID`: Tailscale OAuth client ID.
- `TAILSCALE_OAUTH_SECRET`: corresponding OAuth client secret, with the device authorization needed by the Tailscale GitHub Action.

The workflow uses `tag:ci` for the temporary runner node by default. Define the repository variable `TAILSCALE_CI_TAG` if the OAuth client is authorized for a different tag. The tailnet policy must allow that tag to register nodes and use Tailscale SSH as `root` to the target server. Configure this narrowly for the deployment host and check that the SSH policy does not require interactive approval. Set `TAILSCALE_DEPLOY_HOST` if the server's Tailscale name is not `deploy`.

The GitHub `production` environment can be configured with protection rules if deployment approval is desired. Pull requests never receive deployment credentials or run on the deployment server.

## What deployment changes

The server must retain its existing `/opt/bearblog/compose.yaml`, `Dockerfile`, production settings, Cloudflare middleware, and `.env`. The script builds a revision-specific image using those production files and the Git commit, creates a consistent SQLite backup in `/opt/bearblog/backups`, runs migrations and `collectstatic`, and recreates the service. Database, exported content, and static files remain in their existing volumes. A generated `compose.override.yaml` records the active image; deployment refuses to overwrite one it does not manage. Release directories, images, and backups are retained and require periodic maintenance.

The workflow checks that the container is running and that the public home page responds. This does not test every page or guarantee that a later container failure is detected. A failed migration or deployment must be investigated before retrying; reverting application code does not undo database migrations. Backups are sensitive because they contain account data and must remain private.

**Git content is not automatically imported into the database.** The server remains authoritative for online editing; deploying code does not apply Markdown edits, deletions, or blog settings from `content/`. Follow `CONTENT.md` for an intentional import after backing up and coordinating online editing. This prevents a stale Git snapshot from overwriting newer posts.

OAuth credentials and any rotated replacements belong only in GitHub Actions secrets. Anyone who knows an OAuth secret may be able to create tagged tailnet devices within its grants; revoke exposed credentials and update the GitHub secret when rotating them.
