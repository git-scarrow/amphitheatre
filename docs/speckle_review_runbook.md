# Speckle review server — operator runbook (read this first)

> Written for someone dropped in cold. It is the document I wish I'd had. It
> covers what the thing is, how to reach and operate it, **where the credentials
> actually are** (several obvious paths are dead ends), the publish workflow, and
> every landmine that cost time. Exhaustive build commands live in
> [`proxmox_speckle.md` §9](proxmox_speckle.md); the running config files are in
> [`../deploy/speckle/`](../deploy/speckle/).

Deployed 2026-06-17. Speckle **v2.25.4 + Frontend-2**.

---

## 1. What this is (and what it is NOT)

A **private, tailnet-only Speckle server** that acts as the 3D **review surface**
for the Petoskey Pit civic-bowl design. It renders the validated
`unreal_export/` package so reviewers can look at the seating bowl, ADA routes,
and context in a browser.

**It is not design truth.** The Python/QGIS repo and its gates
(`verify_unreal_export.py`, the object-truth boundary in `speckle_common.py`) are
the **only** acceptance authority. Geometry edited in Speckle means nothing until
it returns as a proposal GeoJSON (EPSG:6494) and passes those gates. The bridge
only ever *reads* `unreal_export/` and copies validated quantities verbatim.

**URL:** `https://speckle-review.scarrow.tailnet` — reachable only from the
`scarrow.tailnet` Headscale tailnet. No public or LAN port is open.

---

## 2. The fleet (who's who)

| Host | Reach it via | Role in this system |
|---|---|---|
| **gentoo** | you're probably on it (`10.10.10.101`, tailnet `100.64.0.32`) | the repo host; runs the publisher |
| **pve** | API `https://10.10.10.2:8006` (LAN) or `https://100.64.0.1:8006` (tailnet) | Proxmox 9.2.3; hosts the VM |
| **aws-ec2** | `ssh sam@aws-ec2` (tailnet `100.64.0.24`) | Headscale control server (Docker) |
| **speckle-review** | `ssh ubuntu@speckle-review.scarrow.tailnet` (tailnet `100.64.0.10`) | VM 131; runs the Speckle Docker stack |

The VM also has a LAN address `10.10.10.114` (DHCP on `vmbr0`) — **don't rely on
it**; the service is deliberately bound to the tailnet IP only.

---

## 3. Credentials & access — where they REALLY are

This is the part that wastes the most time. Read it before trying anything.

### Proxmox API
- ❌ The **proxmox MCP** is configured for `192.168.1.156` — **stale/unroutable**, every call times out. Ignore it (or repoint it at `10.10.10.2`).
- ❌ The token in `~/terraform/proxmox/terraform.tfvars` (`root@pam!terraform=…`) is **revoked** → `401`.
- ✅ The **working token** is in **1Password → vault `Remote Access Keys` → item `Proxmox api`** (user `mcp@pam!automation`, full admin incl. `VM.GuestAgent.Unrestricted`). The `op` CLI is already authenticated via a **service account** (`OP_SERVICE_ACCOUNT_TOKEN` in env), so you can resolve it non-interactively:
  ```sh
  SECRET=$(op read "op://Remote Access Keys/Proxmox api/password")
  TOK="PVEAPIToken=mcp@pam!automation=$SECRET"
  curl -sk -H "Authorization: $TOK" https://10.10.10.2:8006/api2/json/version
  ```
- ❌ **No SSH to `pve`** (publickey/password denied). Everything Proxmox-side is done over the **HTTP API** with that token.

### Headscale (the tailnet control server)
- It's a **Docker container** named `headscale` on **aws-ec2**, bound to `127.0.0.1:8080`. `sudo` is passwordless there. Drive it with:
  ```sh
  ssh sam@aws-ec2 'sudo docker exec headscale headscale <subcommand>'
  ```
- Login server clients use: **`https://vpn.scarrow.net`**. MagicDNS is on tailnet-wide (`base_domain scarrow.tailnet`) — a node named `X` resolves as `X.scarrow.tailnet` automatically.
- The headscale **user** is id `1` = `sam`. Do **not** stand up a second Headscale.

### The VM
- `ssh ubuntu@speckle-review.scarrow.tailnet` (gentoo's `~/.ssh/id_ed25519` is injected). Passwordless `sudo`. The whole stack is in **`/srv/speckle/`**.

### Speckle app
- **Admin:** `sscarrow@gmail.com` (role `server:admin`). Password is **not** in the repo — it's in `/srv/speckle/` history / should be saved to 1Password.
- **Publisher token:** a scoped PAT (`streams:read`, `streams:write`, `profile:read`) — same caveat, save it to 1Password.
- **TLS:** Caddy **internal CA**. Root cert: `/srv/speckle/caddy-data/caddy/pki/authorities/local/root.crt`. Clients (and the publisher) need it to verify TLS.

### IDs you'll need
| Thing | ID |
|---|---|
| Project "Petoskey Pit Civic Bowl" | `3d44308d44` |
| Model `accepted/scenario-e-baseline` | `017f613f5a` |
| Model `proposal/stage-rule9-open-20260617` | `16ee3641bf` |
| Model `proposal/scenario-d2-alternative-20260617` | `1c837c46fa` |
| Model `reference/context` | `a8b820ea72` |

---

## 4. Architecture (one VM, one Docker stack)

VM 131 (Ubuntu 24.04 cloud image, 4 vCPU / 8 GB / 64 GB) runs a Docker Compose
stack in `/srv/speckle` (compose project name `speckle-server`, network
`speckle-server_default`):

```
postgres:16.9  valkey:8  minio  speckle-server:2  speckle-frontend-2:2
preview-service:2  webhook-service:2  fileimport-service:2  caddy:2-alpine
```

- **Caddy** is the only thing published, and **only on the tailnet IP**
  (`100.64.0.10:443` / `:80`). It terminates TLS (internal CA) and routes:
  `/(graphql|explorer|auth/*|objects/*|preview/*|api/*|static/*)` →
  `speckle-server:3000`, `/minio/*` → `minio:9000`, everything else →
  `speckle-frontend-2:8080`. (We do **not** run the upstream
  `speckle-docker-compose-ingress` — see Gotchas.)
- **Joins the tailnet** at first boot via cloud-init (`tailscale up
  --login-server=https://vpn.scarrow.net --hostname=speckle-review`).

---

## 5. Operating it

```sh
# health
ssh ubuntu@speckle-review.scarrow.tailnet 'cd /srv/speckle && sudo docker compose ps'
# logs for one service
ssh ubuntu@speckle-review.scarrow.tailnet 'cd /srv/speckle && sudo docker compose logs --tail=50 speckle-server'
# bring the stack up / down (prefer the systemd unit so the tailnet bind is correct)
ssh ubuntu@speckle-review.scarrow.tailnet 'sudo systemctl restart speckle-stack.service'
# is the UI up? (from any tailnet client, with the CA)
curl --cacert <caddy-root.crt> https://speckle-review.scarrow.tailnet/graphql \
     -H content-type:application/json -d '{"query":"{ serverInfo { version } }"}'
```

- **Restart survival:** `restart: unless-stopped` + VM `onboot=1` +
  `speckle-stack.service`, which waits for the tailnet IP then runs
  `docker compose up -d` and **force-recreates caddy**. A full reboot recovers
  unattended in ~40 s. (The force-recreate is essential — see Gotchas #6.)
- **Upgrades:** snapshot the VM (PVE) and run `backup.sh` first, then
  `docker compose pull && docker compose up -d`; watch `speckle-server` logs for
  migrations. Roll back the snapshot if it breaks.

---

## 6. Publishing from the repo (the review workflow)

Speckle versions are produced by the repo bridge, never hand-edited.

```sh
# 1. one-time: specklepy in a venv (never system pip), and a CA bundle the
#    publisher trusts (system certs + the Caddy internal-CA root):
python -m venv .venv && . .venv/bin/activate && pip install specklepy
cat "$(python -c 'import certifi;print(certifi.where())')" caddy-root.crt > speckle-ca-bundle.pem

# 2. point at the server + the target model, and trust the CA
export SPECKLE_SERVER=https://speckle-review.scarrow.tailnet
export SPECKLE_TOKEN=<publisher-PAT>
export SPECKLE_PROJECT_ID=3d44308d44
export SPECKLE_MODEL_ID=017f613f5a          # accepted/scenario-e-baseline
export REQUESTS_CA_BUNDLE=$PWD/speckle-ca-bundle.pem SSL_CERT_FILE=$PWD/speckle-ca-bundle.pem

# 3. build the payload, dry-run (gates only, no network), then publish
python scripts/export_speckle_payload.py        # -> speckle_export/petoskey_pit.accepted.speckle.json
python scripts/publish_speckle.py                # DRY RUN: must say "preflight: OK"
python scripts/publish_speckle.py --publish      # real send
```

- The publisher **refuses** unless `verify_unreal_export.py` exits 0 **and** the
  payload clears the object-truth boundary **and** the branch prefix matches
  `acceptance.state`. That's by design.
- **Accepted bundle = Seating / ADA / Reference only.** The exporter's `--layers`
  selector drops the Stage from accepted (see Gotchas #9). To publish the stage
  (or another proposal):
  ```sh
  python scripts/export_speckle_payload.py --state proposal --topic stage-rule9-open --layers Stage,Reference
  SPECKLE_MODEL_ID=16ee3641bf python scripts/publish_speckle.py --publish \
      --payload speckle_export/petoskey_pit.proposal.speckle.json
  ```
- Create a new model (returns its id) before publishing to it:
  ```sh
  curl --cacert caddy-root.crt $SPECKLE_SERVER/graphql -H "authorization: Bearer <ADMIN_TOKEN>" \
    -H content-type:application/json \
    -d '{"query":"mutation($i:CreateModelInput!){ modelMutations{ create(input:$i){ id name } } }","variables":{"i":{"projectId":"3d44308d44","name":"proposal/<topic>-<yyyymmdd>"}}}'
  ```

---

## 7. Gotchas (the landmines — every one of these cost real time)

1. **Proxmox MCP IP is stale** (`192.168.1.156`) and the **terraform token is revoked**. Use the 1Password `Proxmox api` token over `10.10.10.2:8006` / `100.64.0.1:8006` (§3).
2. **No SSH to `pve` and the token lacks `Sys.Modify`** → the storage `download-url` API is **denied**. To get a file onto pve storage, **`upload`** it (needs only `Datastore.AllocateTemplate`, which the token has).
3. **No Ubuntu cloud image on the host** and **no way to upload cloud-init snippets via API** (that needs pve SSH, which bpg/Terraform uses but we don't have). Bootstrap is therefore a **NoCloud seed ISO** (`cidata`-labelled, holds `user-data`+`meta-data`) attached as a CD-ROM. There are **no ISO tools on gentoo** (`genisoimage`/`xorriso`/`cloud-localds` all missing) — build it with **`pycdlib` in a venv**.
4. **The VM is on the LAN** (`ens18 = 10.10.10.114`), not an isolated subnet. So `0.0.0.0` binding would expose Speckle on the LAN. Caddy is bound to the **tailnet IP only** (`100.64.0.10`) — keep it that way.
5. **The upstream `speckle-docker-compose-ingress:2` image crash-loops** (`pcre_jit` directive emitted into the nginx `http` include context). We dropped it and let **Caddy do the route map** directly (§4). Don't re-add the ingress.
6. **Caddy's tailnet-IP bind races `tailscaled` on boot.** Docker's auto-start brings caddy up before the `100.64.0.10` address exists → the publish silently fails and `docker compose up -d` won't restart an already-"running" container. `speckle-stack.service` fixes this by **force-recreating caddy** after the tailnet IP is up. If the UI is down after a reboot, run `sudo systemctl restart speckle-stack.service`.
7. **`preview-service` needs `PORT`; `fileimport-service` needs `REDIS_URL`** (newer images validate env with `znv` and crash without them).
8. **specklepy 3.x drops an *assigned* `speckle_type`.** `_dict_to_base` must **construct the real classes** (`objects.geometry.Polyline`/`Point`, `…collections.collection.Collection`) or every object serializes as `"Base"` and the **viewer renders nothing**. (The original test only mocked the send, so it never caught this.)
9. **Planimetric layers fall to datum 0.** Stage/ADA footprints with no source elevation rendered at NAVD88 0 ft (~186 m below the bowl — a "floating lower layer"). The exporter now **drapes** them to the site base grade for rendering while keeping the faithful source z (+`z_draped` flag) in `@geo_epsg6494`.
10. **The published stage was wrong by design-canon.** It's the inherited `design_open_low` footprint = the **Rule-9-OPEN** mismatch (−22.3 ft / +25.4° off the seating frame) that overlaps the seating. It is **not** in the accepted bundle; it ships as `proposal/stage-rule9-open-…`. **Do not "fix" it by moving geometry** — closing Rule 9 (adopting P_opt or another stage + re-emitting stage-derived artifacts) is a governed human decision.
11. **Speckle's viewer defaults to a federated "Multiple…" scene.** If you loaded several models, you'll see them overlaid (e.g., the stage on top of the bowl). Open a single model directly: `…/projects/3d44308d44/models/017f613f5a`.
12. **The DEM source files are git-ignored** (`dem/*.tif`), present only in the main checkout. The publisher's boundary check requires `source_file` to exist, so a fresh worktree must symlink `dem/dem_design_1ft.tif` and `dem/proposed_grade_1ft.tif` from the main checkout, or the publish is refused.
13. **`docs/proxmox_speckle.md` only exists on the `speckle-review-bridge` branch** (unpushed), not `origin/main`. A worktree for this work must branch from `speckle-review-bridge`, not the default `origin/main`.

---

## 8. Backups & restore

Two layers (full procedure in [`proxmox_speckle.md` §9.5](proxmox_speckle.md)):
1. **App-consistent** — `/srv/speckle/backup.sh` daily via `speckle-backup.timer` (03:30 UTC, 14-day retention): `pg_dump -Fc` + MinIO `mc mirror` + config tarball → `/srv/speckle/backups/<ts>/`.
2. **PVE-level** — VM snapshot `postdeploy20260618` + a `vzdump` archive on `hdd2tb` (`vzdump-qemu-131-*.vma.zst`).

Postgres + MinIO must be restored **together** (they cross-reference object ids).
Don't run `vzdump` and a snapshot at the same instant — the second fails with "VM
is locked".

---

## 9. Open items / decisions not mine to make

- **Rule 9 (stage adoption)** is OPEN. The accepted model shows no stage on
  purpose; the inherited stage lives in `proposal/stage-rule9-open-20260617`.
  Closing it = choosing a corrected stage geometry + fan + typology and
  re-emitting every stage-derived artifact (see
  `analysis/stage_adoption/STAGE_RULE9_DECISION_TEMPLATE.md`).
- **Stale versions:** `accepted/scenario-e-baseline` has superseded versions
  (`d243a81b32` typeless, `218758225c` pre-drape, `ab14ebdef7` had-stage) behind
  the current clean `a6e9dab770`. Safe to delete.
- **This work is uncommitted** on worktree branch `speckle-tailnet-deploy`
  (branched from `speckle-review-bridge`).
- **Secrets** (admin password, publisher PAT) live only on the VM / in the
  deploy run — copy them into 1Password.
