#!/usr/bin/env bash
# Application-consistent backup for the Petoskey Pit Speckle review server.
# Backs up the two stores that reference each other (Postgres metadata + MinIO
# blobs) plus the critical config (Caddy internal-CA, compose, .env).
# Run from cron/systemd-timer. See docs/proxmox_speckle.md "Storage & backups".
set -euo pipefail
cd /srv/speckle
set -a; . /srv/speckle/.env; set +a
TS=$(date +%Y%m%d-%H%M%S)
DEST="/srv/speckle/backups/$TS"
mkdir -p "$DEST"
NET="speckle-server_default"

# 1. Postgres logical dump (consistent custom-format snapshot)
docker compose exec -T postgres pg_dump -U speckle -Fc speckle > "$DEST/speckle.dump"

# 2. MinIO object store mirror (geometry blobs + previews) via a transient mc
docker run --rm --network "$NET" -v "$DEST:/backup" \
  -e "MC_HOST_local=http://${S3_ACCESS_KEY}:${S3_SECRET_KEY}@minio:9000" \
  minio/mc mirror --overwrite --remove local/speckle-server /backup/minio >/dev/null

# 3. Config: Caddy internal-CA (avoid re-issuing certs), compose, env
tar czf "$DEST/config.tgz" Caddyfile docker-compose.yml .env caddy-data/caddy/pki 2>/dev/null || true

# retention: keep 14 days
find /srv/speckle/backups -maxdepth 1 -type d -mtime +14 -exec rm -rf {} +

echo "backup OK -> $DEST"
du -sh "$DEST" 2>/dev/null || true
