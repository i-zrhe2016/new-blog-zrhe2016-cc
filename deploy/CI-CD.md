# CI/CD

GitHub Actions runs Django and content-sync tests for pull requests and pushes to `master`. After the tests pass, a push to `master` builds and deploys the application to the existing `/opt/bearblog` server through Tailscale SSH. A manual run on `master` is also available in Actions. Production deployments are serialized, and an outdated commit is refused before deployment.

## Configuration

The repository needs these GitHub Actions secrets:

- `TAILSCALE_OAUTH_CLIENT_ID`: Tailscale OAuth client ID.
- `TAILSCALE_OAUTH_SECRET`: corresponding OAuth client secret, with the device authorization needed by the Tailscale GitHub Action.

The workflow uses `tag:ci` for the temporary runner node by default. Define the repository variable `TAILSCALE_CI_TAG` if the OAuth client is authorized for a different tag. The tailnet policy must allow that tag to register nodes and use Tailscale SSH as `root` to the target server. Configure this narrowly for the deployment host and check that the SSH policy does not require interactive approval. Set `TAILSCALE_DEPLOY_HOST` if the server's Tailscale name is not `deploy`.

The GitHub `production` environment can be configured with protection rules if deployment approval is desired. Pull requests never receive deployment credentials or run on the deployment server.

## Private dashboard

The managed Compose override runs two copies of the application: `bearblog` in public mode on loopback port 19443, and `bearblog-private` in tailnet mode on loopback port 19444. Both use the same database and content. The private process automatically uses the sole active blog owner; it refuses access if there is not exactly one blog or the owner is inactive. The public process rejects dashboard and account routes even when a browser has an old authenticated session.

After the first deployment of this configuration, point the existing **tailnet-only** Tailscale Serve listener on port 9443 to `http://127.0.0.1:19444`. Keep the public Funnel origin on port 19443 and never expose port 19444 through Funnel or another public proxy. Check the tailnet ACLs/grants: anyone allowed to reach the private listener can manage the blog without a password. The private dashboard is at `https://deploy.taile2c45c.ts.net:9443/dashboard/`.

Verify both listeners and an actual dashboard edit before considering the change complete; a successful container start does not verify the Tailscale routing. Keep CSRF protection enabled. If Serve is reset or changed, recheck that the private listener remains tailnet-only.

## Manual rollout on 2026-11-19

The private dashboard was deployed from the tested working tree without creating a Git commit. The running image is `bearblog-private:private-access-5J3KNiB4`, built on the previous production image `bearblog-ci:284a962be6fbff76872bbd074e7139bfe4077763` with only the access middleware, settings, dashboard template, and access tests overlaid. The original settings and template matched their Git baselines before replacement.

The root-only release directory `/opt/bearblog/releases/private-access-5J3KNiB4` retains the previous Compose override (`compose.before.yaml`), SQLite backup (`database.before.db`), and Tailscale routing snapshots (`serve.before.json`, `serve.after.json`). Only the tailnet-only 9443 upstream changed, from loopback 19443 to 19444. Existing public Funnel and other Serve listeners were preserved.

Verification covered the live browser dashboard, posts/editor pages, creation and removal of an unpublished temporary draft, and rejection of a cross-site write. Public dashboard/account/action routes returned 403. The public custom-domain `/admin/` is also protected by an existing Cloudflare Access redirect; the origin and workers.dev admin route returned 403. The public home page remained accessible.

These repository changes must be included in subsequent CI releases to retain this behavior. A deployment from an older commit can restore the previous access logic.

## What deployment changes

The server must retain its existing `/opt/bearblog/compose.yaml`, `Dockerfile`, production settings, Cloudflare middleware, and `.env`. The script builds a revision-specific image using those production files and the Git commit, creates a consistent SQLite backup in `/opt/bearblog/backups`, installs a daily backup timer for the database and migrated assets, runs migrations and `collectstatic`, and recreates the service. The initial backup must succeed before migrations. Database, content assets, and static files remain in their existing volumes. A generated `compose.override.yaml` records the active image; deployment refuses to overwrite one it does not manage. Release directories, images, and backups are retained and require periodic maintenance. See `CONTENT.md` for restoration, off-host copies, and external storage limitations.

The workflow checks that the container is running and that the public home page responds. This does not test every page or guarantee that a later container failure is detected. A failed migration or deployment must be investigated before retrying; reverting application code does not undo database migrations. Backups are sensitive because they contain account data and must remain private.

**Git content is not automatically imported into the database.** The server remains authoritative for online editing. Article content is no longer tracked in Git; follow `CONTENT.md` for backup and restoration.

OAuth credentials and any rotated replacements belong only in GitHub Actions secrets. Anyone who knows an OAuth secret may be able to create tagged tailnet devices within its grants; revoke exposed credentials and update the GitHub secret when rotating them.
