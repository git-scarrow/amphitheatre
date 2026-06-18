# deploy/speckle — as-built artifacts for the private tailnet Speckle server

These are the exact files running on VM `speckle-review` (Proxmox `pve`, id 131),
reachable only at **`https://speckle-review.scarrow.tailnet`** over the
Headscale-managed tailnet. Full deployment narrative, exact Headscale / Tailscale
/ Proxmox commands, and backup/restore are in
[`docs/proxmox_speckle.md` §9](../../docs/proxmox_speckle.md).

| File | Where it lives on the VM | Purpose |
|---|---|---|
| `docker-compose.yml` | `/srv/speckle/docker-compose.yml` | the 9-service stack (Caddy fronts directly; the upstream ingress is dropped — it crash-loops) |
| `Caddyfile` | `/srv/speckle/Caddyfile` | internal-CA TLS + ingress route map; bound to the tailnet IP via compose `ports` |
| `.env.example` | `/srv/speckle/.env` (fill + chmod 600) | secrets + `CANONICAL_URL` + `TS_BIND` |
| `cloud-init.user-data.example` | NoCloud seed ISO (`cidata`) | first-boot: qemu-guest-agent + docker + `tailscale up` (insert the pre-auth key) |
| `backup.sh` | `/srv/speckle/backup.sh` | daily pg_dump + MinIO mirror + config tarball |
| `speckle-backup.{service,timer}` | `/etc/systemd/system/` | runs `backup.sh` daily at 03:30 UTC |
| `speckle-stack.service` | `/etc/systemd/system/` | restart-survival: brings the stack up *after* the tailnet IP exists, force-recreating Caddy so its tailnet bind reattaches |

Speckle is a **review surface only** — the Python/QGIS repo remains the sole
acceptance authority (see the repo `README.md` → "Speckle review boundary").
