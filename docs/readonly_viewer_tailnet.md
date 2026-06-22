# Read-Only Web Viewer on the Tailnet — Deployment Plan

**Status:** `PLAN · doc-only · no infra changed, no Speckle touched, no geometry/ledger/validation mutated`
**Date:** 2026-06-20 · **Repo:** `amphitheatre` @ `d21419a` (branch `unreal/mcp-readonly-scene-v0`)

Goal: serve the **static, read-only 3D web viewer** (`web_viewer/`) from **always-on
infrastructure**, exposed over **`scarrow.tailnet`** (Headscale), so **macbook-m4 reviews it
through a browser only**. The MacBook is never the serving host except as a last-resort local
fallback. Cloudflare tunnel is an **optional, later** path for *external* (non-tailnet) reviewers.

> The viewer is **presentation only**. The Python/QGIS gates + `data/speckle_publish_ledger.json`
> remain the sole acceptance authority. Nothing here edits geometry, the ledger, the Unreal
> handoff, the validation scripts, or the live Speckle server.

---

## 1. What we are serving (and why it's safe to serve)

`web_viewer/` is a **fully self-contained, committed** static app — a `git pull` gets everything,
no build step:

| File | Tracked | Role |
|---|---|---|
| `web_viewer/index.html` | ✅ (50 KB) | the entire app (HTML/CSS/JS, one file) |
| `web_viewer/data/site_data.js` | ✅ (1.6 MB) | baked data payload — terrain grids + all design layers + audit results |
| `web_viewer/vendor/three.min.js`, `vendor/OrbitControls.js` | ✅ | vendored Three.js r147 (only dependency) |

Because terrain is **baked into `site_data.js`**, the viewer needs **none** of the git-ignored
`dem/*.tif` rasters. It is a closed set of derived, non-authoritative artifacts.

The server is `scripts/serve_viewer.py` — pure Python **stdlib** (`http.server`), no third-party
deps, runs on any `python3` (no venv/numpy needed).

---

## 2. Can `serve_viewer.py` bind to a tailnet-facing interface? — YES, with three rules

Inspected `scripts/serve_viewer.py` and `scripts/serve_viewer.sh`. The Python server is safe to
bind directly to the tailnet IP for a read-only viewer; it does **not** need a reverse proxy for
safety. Justification + the rules that make it safe:

1. **It is GET/HEAD-only.** The handler implements only `do_GET` (line 185) and inherits `do_HEAD`.
   There is **no `do_POST/PUT/DELETE`** — any write method returns **501 Not Implemented**. There
   is no endpoint that can mutate anything.
2. **Run without `--rebuild`.** `--rebuild` is the *only* code path that executes a subprocess
   (`build_truth_package.py`) and rewrites `site_data.js`. Omit it. Without it the watcher thread
   only `stat()`s files (read-only) to drive browser auto-reload, which is harmless on an always-on
   host where the files never change.
3. **Bind the specific tailnet IP, not `0.0.0.0`.** `--host 100.64.0.32` makes the listener
   reachable only via `tailscale0`; it is never exposed on the LAN (`10.10.10.101`) or publicly.
   (Same discipline as the Speckle server, which binds its tailnet IP only — never `0.0.0.0`.)

Path-traversal is handled by `SimpleHTTPRequestHandler.translate_path` (Python 3.13 normalizes and
strips `..`/`.`), so requests cannot escape `web_viewer/`. Transport encryption is provided by the
tailnet (WireGuard), and access is gated by Headscale membership — so **plain HTTP over the tailnet
is acceptable**. A reverse proxy (Caddy / `tailscale serve`) is **optional**, only to add TLS/HTTPS
or a port-less URL (see §7).

---

## 3. Recommended host

**Primary: Gentoo** (`gentoo.scarrow.tailnet` = `100.64.0.32`). It already holds the repo, the
viewer files, and is on the tailnet — zero new infrastructure, deployable in minutes.

- **Caveat:** gentoo is the primary *workstation*; if it sleeps or reboots, the viewer drops. For
  the review window that's usually fine (the service auto-starts on boot and `Restart=on-failure`).
- For **guaranteed 24/7**, promote to the Proxmox/LXC fallback in §8 (mirrors the Speckle VM
  pattern). Recommendation: **deploy on Gentoo now; move to the LXC only if you need true
  always-on independent of the workstation.**

| Property | Value (Gentoo) |
|---|---|
| Host | `gentoo` |
| Service user | `sam` (owns the repo + venv) |
| Working dir | `/home/sam/projects/amphitheatre` |
| Interpreter | `/home/sam/projects/amphitheatre/.venv/bin/python` (or any `python3` — stdlib only) |
| Bind address | `100.64.0.32` (tailnet IP, `tailscale0`) |
| Port | `8788` |
| Tailnet URL | **`http://gentoo.scarrow.tailnet:8788/`** |

---

## 4. systemd unit (Gentoo)

Install as a **system** service so it's always-on at boot (independent of an interactive login).
Read-only hardening is layered on so the process **physically cannot write to disk** even though it
never tries to.

Write `/etc/systemd/system/petoskey-viewer.service`:

```ini
[Unit]
Description=Petoskey Pit read-only web viewer (tailnet, static)
After=network-online.target tailscaled.service
Wants=network-online.target tailscaled.service

[Service]
Type=simple
User=sam
Group=sam
WorkingDirectory=/home/sam/projects/amphitheatre

# Wait for the tailnet IP to exist before binding (boot race: tailscaled vs. our bind —
# the same race that bit the Speckle Caddy bind). Give up after 30s.
ExecStartPre=/bin/sh -c 'for i in $(seq 1 30); do ip -4 addr show tailscale0 2>/dev/null | grep -q "100.64.0.32" && exit 0; sleep 1; done; echo "tailnet IP 100.64.0.32 not up on tailscale0" >&2; exit 1'

# Read-only: bind the tailnet IP, NO --rebuild (never runs the build subprocess).
ExecStart=/home/sam/projects/amphitheatre/.venv/bin/python scripts/serve_viewer.py --host 100.64.0.32 --port 8788

Restart=on-failure
RestartSec=3

# --- read-only guarantees (defense in depth; the server is already GET-only) ---
NoNewPrivileges=yes
ProtectSystem=strict          # entire FS read-only to the unit ...
ProtectHome=read-only         # ... including /home, which it must READ but never write
PrivateTmp=yes
ProtectControlGroups=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
RestrictAddressFamilies=AF_INET AF_INET6
RestrictNamespaces=yes
LockPersonality=yes
# (No ReadWritePaths= is granted on purpose — the service has zero writable paths.)

[Install]
WantedBy=multi-user.target
```

Notes:
- `--host 100.64.0.32` hardcodes the Headscale-assigned IP (stable per node). Confirm with
  `tailscale ip -4` before installing; if it ever changes, update both the `ExecStartPre` grep and
  `ExecStart`.
- `python` symlink resolves to `python3.13`; stdlib-only, so the venv is not strictly required —
  `/usr/bin/python3` works too if you prefer no venv dependency.

---

## 5. Read-only guarantees (summary)

1. **Protocol:** only `do_GET`/`do_HEAD` exist → POST/PUT/DELETE return `501`. No mutation endpoint.
2. **No build path:** started **without `--rebuild`** → `build_truth_package.py` is never invoked;
   `site_data.js` is never rewritten; the watcher only reads mtimes.
3. **Content sandbox:** serves only the resolved root (`web_viewer/` by default, or an explicit
   `--root`); `translate_path` confines every request under it and blocks `..` traversal.
4. **FS sandbox:** `ProtectSystem=strict` + `ProtectHome=read-only` + no `ReadWritePaths` → the
   process cannot write anywhere — it cannot touch the ledger, geometry, validation scripts, or any
   repo file.
5. **Exposure:** binds the tailnet IP only → not on LAN or public; reachable only by tailnet members.
6. **No authoritative egress:** the viewer makes no outbound calls and never contacts Speckle.

---

## 6. Firewall assumptions

- **No new firewall rule needed** when bound to `100.64.0.32`: the socket is only reachable through
  `tailscale0`. The LAN address (`10.10.10.101`) and any public path never see port 8788.
- Do **not** bind `0.0.0.0` — that would expose 8788 on the LAN and require an explicit
  nftables/iptables drop on non-`tailscale0`. Binding the specific IP avoids the whole problem.
- **Optional hardening:** a Headscale ACL policy restricting who may reach `gentoo:8788` (e.g. only
  `macbook-m4`, `macbook-m2`). Drive Headscale on `aws-ec2`:
  `ssh sam@aws-ec2 'sudo docker exec headscale headscale ...'`. Not required for a trusted personal
  tailnet.
- **Outbound:** none required.

---

## 7. How the MacBook opens it

`macbook-m4` is already on the tailnet (`100.64.0.46`, active). No tunnel, no certs, no client
software beyond the browser:

1. Confirm tailnet up: `tailscale status | grep gentoo` (should show `100.64.0.32 gentoo`).
2. Open in Safari/Chrome:  **`http://gentoo.scarrow.tailnet:8788/`**
3. Controls: drag = orbit · right-drag = pan · wheel = zoom · keys **1–7** camera presets · **0**
   reset · click a tread for its per-row audit (elevation, seats, sightline C mm, Band-A status).

Plain HTTP is fine — the tailnet encrypts the hop. (If the browser ever objects to HTTP, use the
optional TLS upgrade below.)

**Optional TLS / port-less URL** (nice-to-have, not required):
- `tailscale serve` — if Headscale cert provisioning is enabled:
  `tailscale serve --bg 8788` → `https://gentoo.scarrow.tailnet` (auto-TLS, no port). Verify your
  Headscale supports HTTPS certs first.
- Caddy reverse proxy (mirrors the Speckle internal-CA pattern): bind Caddy to `100.64.0.32:443`,
  `reverse_proxy 127.0.0.1:8788`, change `serve_viewer.py --host 127.0.0.1`. Heavier; only if you
  want TLS consistent with the Speckle server.

---

## 8. Proxmox / LXC fallback (true 24/7) — documented, not executed

For always-on independent of the workstation. **New infra → needs explicit approval before
building.** Mirrors the Speckle VM (tailnet-only, Headscale-joined).

1. Unprivileged LXC on `pve` (e.g. Debian 12, ctid 132, hostname `petoskey-viewer`, 1 vCPU /
   512 MB / 4 GB).
2. Join tailnet: install tailscale →
   `tailscale up --login-server=https://vpn.scarrow.net --hostname=petoskey-viewer`.
3. Get the static viewer in (no venv needed — `serve_viewer.py` is stdlib):
   - `git clone` the repo (**requires `scripts/serve_viewer.py` to be committed** — see §9), **or**
   - copy just `web_viewer/` + `scripts/serve_viewer.py`.
4. Create a `viewer` system user; install the §4 unit with `User=viewer`,
   `WorkingDirectory=<deploy dir>`, `ExecStart=/usr/bin/python3 scripts/serve_viewer.py --host <LXC
   tailnet IP> --port 8788 --root <deploy dir>/web_viewer`, and the same hardening (drop
   `ProtectHome=read-only` if the deploy dir isn't under `/home`; use `ReadOnlyPaths=<deploy dir>`
   instead). The `--root` flag pins the served directory explicitly so the copy-only layout works
   even when `serve_viewer.py` isn't two levels under a repo that contains `web_viewer/` (without it
   the script falls back to `<its dir>/../web_viewer`).
5. URL: **`http://petoskey-viewer.scarrow.tailnet:8788/`**.

---

## 9. Classification of the dirty viewer files (Task 4 — classified, NOT staged/committed)

| File | git state | Relevance to this plan | Action |
|---|---|---|---|
| `README_web_viewer.md` | modified (+31 lines, additive) | Documents the **Cloudflare tunnel** live-preview (`serve_viewer.sh` → `amphitheatre.scarrow.net`). Host/Cloudflare-specific — relevant only to the *optional external* path (§10), **not** tailnet serving. | **Leave untouched.** |
| `scripts/serve_viewer.py` | untracked | **Central** — the server we deploy. stdlib-only, cross-platform, GET/HEAD-only. Already on disk on gentoo (works now); **must be committed for the LXC `git clone` path** (§8). | Recommend a **bounded follow-up commit** (see below). Not staged now. |
| `scripts/serve_viewer.sh` | untracked | Gentoo + `cloudflared` wrapper. Relevant only to the optional external path (§10); **not** needed for tailnet systemd serving. | Commit alongside `serve_viewer.py` only if/when the Cloudflare path is adopted. Not staged now. |

**Bounded follow-up commit (recommended, when you choose to):** commit
`scripts/serve_viewer.py` (+ optionally `scripts/serve_viewer.sh` and the `README_web_viewer.md`
addition) on a small branch so the LXC fallback can `git clone` it. This is a code+doc change —
keep it **separate** from any geometry/ledger work. Not done here.

---

## 10. Optional: Cloudflare tunnel for EXTERNAL reviewers (later, not default)

`scripts/serve_viewer.sh` runs `serve_viewer.py` + `cloudflared` →
`https://amphitheatre.scarrow.net`. Use **only** to share with reviewers who are **not** on the
tailnet. Caveats: it publishes to the Cloudflare edge (external service); pass an explicit
`--config` (the host's shared default cloudflared config otherwise silently 404s the edge —
`cloudflared-config-override-gotcha`). Not needed for the MacBook, which uses the tailnet directly.

---

## 11. Alternative tailnet review surface (context)

The private **Speckle** server (`https://speckle-review.scarrow.tailnet`, accepted model
`017f613f5a`) is the other, heavier tailnet review surface (interactive 3D, federated models). It's
already deployed and is also browser-only from the Mac (needs the Caddy internal-CA root trusted).
This doc's static viewer is the **lightweight, zero-dependency** option. Both are read-only review;
neither is acceptance authority.

---

## 12. Deploy — exact commands (Gentoo, run as a user with sudo)

```sh
# 0. (read-only sanity) confirm the tailnet IP and that the viewer files are present
tailscale ip -4                                   # expect 100.64.0.32
ls /home/sam/projects/amphitheatre/web_viewer/index.html \
   /home/sam/projects/amphitheatre/web_viewer/data/site_data.js

# 1. install the unit from §4
sudo tee /etc/systemd/system/petoskey-viewer.service >/dev/null   # paste §4 contents
sudo systemctl daemon-reload
sudo systemctl enable --now petoskey-viewer.service

# 2. verify it's up and bound to the tailnet IP only
systemctl --no-pager status petoskey-viewer.service
ss -ltnp | grep 8788                               # expect 100.64.0.32:8788 (NOT 0.0.0.0)
curl -sI http://gentoo.scarrow.tailnet:8788/ | head -1   # expect HTTP/1.1 200 OK

# manage
sudo systemctl restart petoskey-viewer.service
sudo systemctl disable --now petoskey-viewer.service      # stop serving
journalctl -u petoskey-viewer.service -e                  # logs
```

---

## 13. Bottom line

- **MacBook URL today:** **`http://gentoo.scarrow.tailnet:8788/`** (browser only; tailnet must be up).
- **Recommended host:** Gentoo now (zero new infra); promote to the Proxmox/LXC in §8 for true 24/7.
- **Read-only:** guaranteed by GET-only server + no `--rebuild` + systemd FS sandbox + tailnet-IP
  bind. No Speckle, ledger, geometry, handoff, or validation change.
