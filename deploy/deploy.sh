#!/usr/bin/env bash
# Run on the existing deployment host, with an extracted git archive in release/app.
set -euo pipefail

release=${1:?release directory required}
revision=${2:?commit SHA required}
root=/opt/bearblog
[[ "$release" == "$root"/releases/* && "$revision" =~ ^[0-9a-f]{40}$ ]]

# Serialize manual and automated deployments on the server.
exec 9>"$root/.deploy.lock"
flock -x 9

cd "$root"
if [[ -e compose.override.yaml ]] && ! grep -q '^# Managed by bearblog CI/CD$' compose.override.yaml; then
    printf '%s\n' 'Existing compose.override.yaml is not managed by this deployment; aborting' >&2
    exit 1
fi
cp Dockerfile deployment_settings.py deployment_context.py "$release/"
mkdir -p "$release/cloudflare-worker"
cp cloudflare-worker/origin_middleware.py "$release/cloudflare-worker/"
image="bearblog-ci:$revision"
docker build -t "$image" "$release"

# Compose resolves paths relative to the first compose file, preserving all volumes.
override="$release/compose.deploy.yaml"
cat > "$override" <<YAML
# Managed by bearblog CI/CD
services:
  bearblog:
    image: $image
    environment:
      PERSONAL_BLOG_ACCESS: public
  bearblog-private:
    image: $image
    restart: unless-stopped
    env_file: /opt/bearblog/.env
    environment:
      PERSONAL_BLOG_ACCESS: tailnet
    volumes:
      - /opt/bearblog/data:/data
      - /opt/bearblog/staticfiles:/app/staticfiles
      - /opt/bearblog/content:/app/content
    ports:
      - "127.0.0.1:19444:8000"
YAML
compose=(docker compose -f "$root/compose.yaml" -f "$override")

# SQLite's backup API makes a consistent snapshot even while the site is running.
mkdir -p "$root/backups"
python3 - "$root/data/dev.db" "$root/backups/pre-deploy-${revision}-$(date -u +%Y%m%dT%H%M%SZ).db" <<'PY'
import sqlite3
import sys
from pathlib import Path

source, destination = map(Path, sys.argv[1:])
if not source.is_file():
    raise SystemExit(f'Database not found: {source}')
with sqlite3.connect(f'file:{source}?mode=ro', uri=True) as db, sqlite3.connect(destination) as backup:
    db.backup(backup)
PY

# Require R2 configuration before replacing the running local backup service.
if [[ ! -s "$root/backup-r2.env" ]] || ! python3 -c 'import boto3'; then
    printf '%s\n' 'R2 backup credentials or boto3 are missing; see CONTENT.md' >&2
    exit 1
fi

# Install the daily backup before changing the running application. Keep all
# existing backups; operators can copy them off-host and manage retention.
install -m 0755 "$release/app/deploy/backup_database.py" "$root/backup_database.py"
install -m 0644 "$release/app/deploy/bearblog-backup.service" /etc/systemd/system/bearblog-backup.service
install -m 0644 "$release/app/deploy/bearblog-backup.timer" /etc/systemd/system/bearblog-backup.timer
systemctl daemon-reload
systemctl enable --now bearblog-backup.timer
systemctl start bearblog-backup.service
if systemctl list-unit-files --no-legend 'bearblog-content-export.timer' | grep -q '^bearblog-content-export.timer'; then
    systemctl disable --now bearblog-content-export.timer
fi

# These commands use the new image and existing persistent data, without importing
# repository content over the database or deleting online edits.
"${compose[@]}" run --rm --no-deps --entrypoint python bearblog manage.py migrate --noinput
"${compose[@]}" run --rm --no-deps --entrypoint python bearblog manage.py collectstatic --noinput
"${compose[@]}" run --rm --no-deps --entrypoint python bearblog manage.py check

# Keep the image override so future ordinary compose operations use this release.
cp "$override" "$root/compose.override.yaml.tmp"
mv -f "$root/compose.override.yaml.tmp" "$root/compose.override.yaml"
docker compose up -d --no-build bearblog bearblog-private
for service in bearblog bearblog-private; do
    if [[ -z "$(docker compose ps --status running -q "$service")" ]]; then
        printf 'Deployment failed: %s container is not running\n' "$service" >&2
        exit 1
    fi
done
printf 'Deployed %s\n' "$revision"
