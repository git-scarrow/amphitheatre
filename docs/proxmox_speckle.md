# Self-hosted Speckle Server on Proxmox — deployment plan

A practical Docker Compose deployment for a **private** Speckle Server that acts
as the **review surface** for the Petoskey Pit civic-bowl bridge. Speckle is for
review, comparison, and collaboration only — the Python/QGIS repo remains the
**only acceptance authority** (see `README.md` → "Speckle review boundary").

> Scope: a small single-host instance for a handful of reviewers on a private
> network. Not an internet-facing multi-tenant deployment. Keep it on the LAN /
> VPN; nothing here should be exposed to the public internet.

Versions below track the upstream `docker-compose.yml` (Speckle Server v3 /
Frontend-2) as of 2026-06. Pin to specific image digests in production rather
than `:latest`.

---

## 1. Host: LXC vs VM

Run Docker inside a **VM**, not an unprivileged LXC. Docker-in-LXC works but
needs nesting/keyctl tweaks and fights AppArmor; a VM is the supported,
low-surprise path and isolates the container runtime from the PVE host.

| Resource | Minimum | Comfortable |
|---|---|---|
| vCPU | 4 | 6–8 |
| RAM | 8 GB | 16 GB (Postgres + preview-service are the consumers) |
| Disk (OS) | 20 GB | 32 GB |
| Disk (data) | 40 GB | 100 GB+ (MinIO object blobs grow with every version) |

**Proxmox setup**

1. Create a VM (Debian 12 or Ubuntu 24.04 LTS), `qcow2`/ZFS-backed.
2. Give it a **second virtual disk** for `/srv/speckle` (data) so backups and
   snapshots of the data volume are independent of the OS disk.
3. CPU type `host`; enable the QEMU guest agent.
4. Install Docker Engine + the compose plugin (`docker compose`, not the legacy
   `docker-compose`).
5. Put the VM on a private VLAN/bridge (see §6). No port-forward from the
   gateway.

Format and mount the data disk (example, ZFS-on-the-VM optional; ext4 is fine):

```sh
sudo mkfs.ext4 /dev/vdb
echo '/dev/vdb /srv/speckle ext4 defaults,noatime 0 2' | sudo tee -a /etc/fstab
sudo mkdir -p /srv/speckle && sudo mount /srv/speckle
sudo mkdir -p /srv/speckle/{postgres-data,redis-data,minio-data,caddy-data,backups}
```

---

## 2. Docker Compose stack

`/srv/speckle/docker-compose.yml`. Services: Postgres, Valkey (Redis),
MinIO (S3 object store), the Speckle server + Frontend-2 + ingress, and the
preview / webhook / fileimport auxiliary services. A **Caddy** reverse proxy
fronts everything and terminates TLS.

All host ports are bound to `127.0.0.1` — only Caddy listens on the private LAN
interface. Secrets come from a sibling `.env` (see §3), never inline.

```yaml
name: speckle-server

x-restart: &restart
  restart: unless-stopped

services:
  postgres:
    <<: *restart
    image: postgres:16.9-alpine
    environment:
      POSTGRES_DB: speckle
      POSTGRES_USER: speckle
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - /srv/speckle/postgres-data:/var/lib/postgresql/data/
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U speckle -d speckle"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    <<: *restart
    image: valkey/valkey:8-alpine
    volumes:
      - /srv/speckle/redis-data:/data

  minio:
    <<: *restart
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${S3_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${S3_SECRET_KEY}
    ports:
      - "127.0.0.1:9000:9000"   # S3 API (proxied by Caddy under /minio if needed)
      - "127.0.0.1:9001:9001"   # MinIO console (keep local-only / SSH-tunnel)
    volumes:
      - /srv/speckle/minio-data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 30s
      timeout: 10s
      retries: 5

  speckle-ingress:
    <<: *restart
    image: speckle/speckle-docker-compose-ingress:latest
    ports:
      - "127.0.0.1:8080:8080"   # Caddy upstream (NOT the LAN-facing port)
    depends_on:
      - speckle-server
      - speckle-frontend-2

  speckle-frontend-2:
    <<: *restart
    image: speckle/speckle-frontend-2:latest
    environment:
      NUXT_PUBLIC_SERVER_NAME: "petoskey-pit"
      NUXT_PUBLIC_API_ORIGIN: ${CANONICAL_URL}
      NUXT_PUBLIC_BACKEND_API_ORIGIN: "http://speckle-server:3000"
      NUXT_PUBLIC_BASE_URL: ${CANONICAL_URL}
      NUXT_REDIS_URL: "redis://redis"
      NUXT_PUBLIC_SSL_ENABLED: "true"      # Caddy terminates TLS

  speckle-server:
    <<: *restart
    image: speckle/speckle-server:latest
    depends_on:
      postgres: { condition: service_healthy }
      redis:    { condition: service_started }
      minio:    { condition: service_started }
    environment:
      CANONICAL_URL: ${CANONICAL_URL}
      SESSION_SECRET: ${SESSION_SECRET}
      STRATEGY_LOCAL: "true"               # local accounts; no public signup (see §6)
      POSTGRES_URL: "postgres"
      POSTGRES_USER: "speckle"
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: "speckle"
      REDIS_URL: "redis://redis"
      S3_ENDPOINT: "http://minio:9000"
      S3_PUBLIC_ENDPOINT: "${CANONICAL_URL}/minio"
      S3_ACCESS_KEY: ${S3_ACCESS_KEY}
      S3_SECRET_KEY: ${S3_SECRET_KEY}
      S3_BUCKET: "speckle-server"
      FRONTEND_ORIGIN: ${CANONICAL_URL}
      EMAIL: "false"                        # private instance; wire SMTP if you want invites

  preview-service:
    <<: *restart
    image: speckle/speckle-preview-service:latest
    depends_on: [speckle-server]
    environment:
      REDIS_URL: "redis://redis"

  webhook-service:
    <<: *restart
    image: speckle/speckle-webhook-service:latest
    depends_on: [speckle-server]
    environment:
      PG_CONNECTION_STRING: "postgres://speckle:${POSTGRES_PASSWORD}@postgres/speckle"

  fileimport-service:
    <<: *restart
    image: speckle/speckle-fileimport-service:latest
    depends_on: [speckle-server]
    environment:
      SPECKLE_SERVER_URL: "http://speckle-server:3000"
      PG_CONNECTION_STRING: "postgres://speckle:${POSTGRES_PASSWORD}@postgres/speckle"

  caddy:
    <<: *restart
    image: caddy:2-alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - /srv/speckle/Caddyfile:/etc/caddy/Caddyfile:ro
      - /srv/speckle/caddy-data:/data
    depends_on: [speckle-ingress]
```

> The `minio` bucket `speckle-server` must exist. On first boot create it with
> the MinIO client: `docker compose exec minio mc mb local/speckle-server`
> (after `mc alias set local http://127.0.0.1:9000 $S3_ACCESS_KEY $S3_SECRET_KEY`).

---

## 3. Secrets (`.env`)

`/srv/speckle/.env`, mode `600`, **not** committed. Generate real values:

```sh
cat > /srv/speckle/.env <<EOF
CANONICAL_URL=https://speckle.lan.example.org
SESSION_SECRET=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -hex 24)
S3_ACCESS_KEY=$(openssl rand -hex 12)
S3_SECRET_KEY=$(openssl rand -hex 32)
EOF
chmod 600 /srv/speckle/.env
```

`CANONICAL_URL` must be the exact private hostname reviewers use (it is baked
into share links and the object store's public endpoint). Use a name that
resolves only on the LAN/VPN.

---

## 4. Reverse proxy (Caddy, auto-TLS)

`/srv/speckle/Caddyfile`. Caddy is the single LAN-facing entrypoint; it proxies
to the Speckle ingress and serves the MinIO S3 path used by `S3_PUBLIC_ENDPOINT`.

**Private-first, no public inbound.** This server lives on the LAN/VPN only —
none of the TLS options below require opening a port to the internet. The
recommended path is Caddy's **internal CA** on a private hostname; the optional
DNS-01 path gets a publicly-trusted cert *without* any inbound exposure (the ACME
challenge is answered over DNS, not HTTP). Never port-forward 80/443 from the
gateway just to obtain a certificate.

```
speckle.lan.example.org {
    encode zstd gzip

    # object store public path (preview thumbnails, large blobs)
    handle_path /minio/* {
        reverse_proxy 127.0.0.1:9000
    }

    # everything else → Speckle ingress (frontend + API + subscriptions)
    reverse_proxy 127.0.0.1:8080

    # TLS, private-first: internal CA needs no public ports at all. Swap for a
    # DNS-01 issuer only if you want a publicly-trusted cert — still no inbound.
    tls internal
}
```

- **Recommended — private hostname, internal CA (no public anything):**
  `tls internal` issues a cert from Caddy's own CA. Distribute Caddy's root
  (`/srv/speckle/caddy-data/caddy/pki/...`) to reviewer machines once. Resolve
  `speckle.lan.example.org` via internal DNS or `/etc/hosts`.
- **Optional — real domain via DNS-01 (still no inbound ports):** use a Caddy
  DNS-provider plugin so Let's Encrypt validates over a DNS TXT record. The host
  needs outbound 443 to the ACME + DNS APIs only; **80/443 stay closed to the
  internet**. Use this only if internal-CA cert distribution is inconvenient.
- The `:80` mapping in the compose file is the LAN-side HTTP→HTTPS redirect for
  reviewers who type a bare hostname — it is **not** a public inbound port and is
  firewalled to the LAN/VPN CIDR like 443 (see §6).
- WebSocket subscriptions (live model updates) pass through `reverse_proxy`
  unchanged — no extra config needed with Caddy 2.

If you prefer Nginx, terminate TLS there and proxy to `127.0.0.1:8080` with
`proxy_set_header Upgrade`/`Connection` for the WS upgrade; keep
`SSL_ENABLED=false` on the server (Caddy/Nginx owns TLS).

---

## 5. Storage & backups

**What holds state** (all on the dedicated `/srv/speckle` data disk):

| Store | Path | Holds |
|---|---|---|
| Postgres | `postgres-data/` | users, projects, models, versions, **object metadata + commit graph** |
| MinIO | `minio-data/` | object blobs (geometry payloads, preview images) |
| Valkey | `redis-data/` | ephemeral queues/cache (not a backup target) |
| Caddy | `caddy-data/` | TLS certs / internal CA (back up to avoid re-issuing) |

A consistent restore needs **Postgres + MinIO together** — they reference each
other (Postgres stores object ids; MinIO stores the bytes).

**Nightly backup** (`/srv/speckle/backup.sh`, run from cron/systemd-timer):

```sh
#!/usr/bin/env bash
set -euo pipefail
cd /srv/speckle
TS=$(date +%Y%m%d-%H%M%S)
DEST=/srv/speckle/backups/$TS
mkdir -p "$DEST"

# 1. Postgres logical dump (consistent snapshot)
docker compose exec -T postgres pg_dump -U speckle -Fc speckle > "$DEST/speckle.dump"

# 2. MinIO object store mirror (incremental)
docker compose exec -T minio mc mirror --overwrite --remove local/speckle-server \
    /backups-mirror/speckle-server   # bind /srv/speckle/backups into minio if mirroring on-box
#   simpler off-box: `mc mirror local/speckle-server remote/speckle-backup`

# 3. Caddy CA + compose + env (small, critical)
tar czf "$DEST/config.tgz" Caddyfile docker-compose.yml caddy-data/caddy/pki 2>/dev/null || true

# retention: keep 14 days
find /srv/speckle/backups -maxdepth 1 -type d -mtime +14 -exec rm -rf {} +
```

**Two backup layers, defence in depth:**

1. **Application-consistent** (above): `pg_dump` + `mc mirror`. Restore by
   `pg_restore` into a fresh DB and `mc mirror` the bucket back. This survives a
   bad upgrade or accidental deletion inside Speckle.
2. **PVE-level**: schedule **Proxmox Backup Server** (or `vzdump`) on the VM —
   ideally with the guest agent's `fs-freeze` so the disk image is consistent.
   This is the fast bare-metal restore path. Snapshot the VM **before every
   `docker compose pull` upgrade**.

Test a restore quarterly into a throwaway VM — an untested backup is a guess.

---

## 6. Private-network assumptions

This deployment assumes a **trusted private network** and is hardened on that
basis:

- **No public exposure.** The VM is on a private VLAN/bridge; the gateway does
  **not** forward 80/443 to it. Reach it over the LAN or a **WireGuard /
  Tailscale** tunnel. `CANONICAL_URL` resolves only inside that network.
- **Host firewall** (Proxmox firewall or `nftables` on the VM): allow 443 (and
  80 for redirect) only from the LAN/VPN CIDR; deny the rest. MinIO console
  (9001) and the S3 API (9000) stay bound to `127.0.0.1` — reach the console via
  SSH tunnel, never a published port.
- **Accounts:** keep `STRATEGY_LOCAL=true` with invites only; do **not** enable
  open OAuth/registration on a private box. After creating the first admin,
  disable new-user signup in server settings, or front it with the VPN so only
  trusted clients can even reach the login page.
- **Secrets** live in `.env` (mode 600) and never in the repo. Rotate
  `SESSION_SECRET` / S3 keys if the VM is ever snapshotted off-site unencrypted.
- **Tokens:** the publisher authenticates with a **Personal Access Token**
  (`SPECKLE_TOKEN`) scoped to stream write. Treat it like a password; pass it via
  the environment, not a flag.

---

## 7. Bring-up & smoke test

```sh
cd /srv/speckle
docker compose pull
docker compose up -d
docker compose ps                       # all healthy?
docker compose exec minio mc mb local/speckle-server   # one-time bucket
# browse https://speckle.lan.example.org → create the admin account
```

Then connect the bridge from the repo host (over the VPN/LAN):

```sh
# in the project venv, with specklepy installed:
export SPECKLE_SERVER=https://speckle.lan.example.org
export SPECKLE_TOKEN=...           # PAT from the Speckle profile page
export SPECKLE_PROJECT_ID=...      # create project "petoskey-pit-civic-bowl"
export SPECKLE_MODEL_ID=...        # create model "accepted/scenario-e-baseline"

python scripts/export_speckle_payload.py          # build the payload
python scripts/publish_speckle.py                 # DRY RUN (no network) — must say preflight OK
python scripts/publish_speckle.py --publish       # real send (only after the dry run is clean)
```

The publisher refuses to send unless `scripts/verify_unreal_export.py` passes
and the payload clears the object-truth boundary — see the README section.

---

## 8. Upgrades

1. Snapshot the VM (PVE) and run `backup.sh`.
2. `docker compose pull && docker compose up -d`.
3. Watch `docker compose logs -f speckle-server` for migration completion.
4. Smoke-test a model load; if broken, `docker compose down` and roll back the
   VM snapshot (the application-consistent dump is the fallback).

Pin image digests once a known-good set is found so an upgrade is deliberate,
not incidental to `:latest` drift.
