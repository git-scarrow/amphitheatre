# MacBook-m4 → Gentoo CivicBowl UE operator guide

How to **open, control, inspect, and pull captures from** the reproducible
Gentoo-hosted Unreal scene from MacBook-m4, over the tailnet — **read-only**, with
minimal setup. No design work, no geometry/Speckle/ledger changes.

## The three surfaces (do not conflate)

| Surface | What it is | Where | Read/write |
|---|---|---|---|
| **Static Three.js viewer** | browser review surface, **always-on**, read-only | `http://gentoo.scarrow.tailnet:8788/` | read-only |
| **Unreal UE 5.8 scene** | Gentoo-hosted **editor/commandlet** scene, reproducible, read-only inspection target | `/Game/Maps/CivicBowl` on gentoo (not a URL) | read-only inspection |
| **Speckle** | separate interactive 3D **review/publishing** surface | `https://speckle-review.scarrow.tailnet` | review/publish |

How to tell which you're looking at: a **browser tab on :8788** is the static
viewer; a **3D Unreal editor / a `VERDICT:` line from a commandlet** is the UE
scene; **anything on `speckle-review.scarrow.tailnet`** is Speckle. This doc is
only about the **UE scene** (plus opening the static viewer for convenience).

## Quick answers (acceptance)

- **What URL do I open?** `http://gentoo.scarrow.tailnet:8788/` — the static viewer.
  The UE scene itself is **not** a URL (no Pixel Streaming yet); you inspect it via SSH commands.
- **What command do I run from MacBook?** `./scripts/macbook/ue_verify_remote.sh`
- **What command runs on Gentoo?** (it runs these for you over SSH)
  `python scripts/unreal/verify_civicbowl.py` then a headless
  `UnrealEditor-Cmd … ue_civicbowl.py verify`.
- **How do I verify the UE scene is current?** `ue_verify_remote.sh` → expect
  `reload_ok: True` and `VERDICT: PASS` with all 9 groups OK.
- **How do I retrieve screenshots/logs?** `./scripts/macbook/fetch_ue_outputs.sh`
- **What is still not available from MacBook?** Live interactive 3D of the UE
  scene and one-command rendered captures — **pending** (see "Capture").

## Prerequisites

**MacBook-m4:**
- Tailscale up and logged into the Headscale tailnet (`tailscale status` shows `gentoo`).
- An SSH key authorized on gentoo (the MacBook's `id_ed25519_mac` is already in
  `~sam/.ssh/authorized_keys` on gentoo). Test: `ssh sam@gentoo.scarrow.tailnet hostname`.
- A browser; optionally `rsync` (preinstalled on macOS) for faster fetches.
- **No Unreal install needed.** The Mac is a thin operator/client.

**Gentoo (already set up — nothing to do):**
- Repo at `~/projects/amphitheatre` on branch `unreal/mcp-readonly-scene-v0`, with `.venv`.
- UE 5.8 at `/mnt/storage/UnrealEngine-5.8`; project at
  `/mnt/data/UnrealProjects/PetoskeyCivicBowl`; map `/Game/Maps/CivicBowl` built.
- Static viewer service `petoskey-viewer` (binds `100.64.0.32:8788`).
- `sshd` listening on `:22`.

## Tailnet hosts / IPs

| Host | MagicDNS | Tailnet IP |
|---|---|---|
| gentoo (UE host) | `gentoo.scarrow.tailnet` | `100.64.0.32` |
| macbook-m4 (this client) | `macbook-m4.scarrow.tailnet` | `100.64.0.46` |

Discover/refresh with `tailscale status`. If MagicDNS isn't resolving, use the raw
IP everywhere via env: `GENTOO_HOST=100.64.0.32`.

## Helper scripts (`scripts/macbook/`)

Boring, env-driven, no secrets, no root, read-only. Source of truth for defaults
is `scripts/macbook/_lib.sh`:

| Env | Default |
|---|---|
| `GENTOO_HOST` | `gentoo.scarrow.tailnet` |
| `GENTOO_USER` | `sam` |
| `REMOTE_REPO` | `~/projects/amphitheatre` |
| `REMOTE_PROJECT` | `/mnt/data/UnrealProjects/PetoskeyCivicBowl` |
| `UE_CMD` | `…/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd` |
| `VIEWER_URL` | `http://gentoo.scarrow.tailnet:8788/` |
| `LOCAL_OUT` | `./ue_outputs` |

| Script | Does |
|---|---|
| `open_static_viewer.sh` | HTTP-checks then opens the **static viewer** in a browser |
| `ue_verify_remote.sh` | SSH → offline verify + live UE reload verify (read-only) |
| `ue_capture_remote.sh` | reports the **pending** GPU capture path (non-disruptive) |
| `fetch_ue_outputs.sh` | pulls `Saved/Logs` + `Saved/Screenshots` back to `$LOCAL_OUT` |

## MacBook command sequence (the whole workflow)

```sh
cd ~/projects/amphitheatre            # your local clone of the repo

# 1. Open the always-on static viewer (browser review surface)
./scripts/macbook/open_static_viewer.sh

# 2. Confirm the UE scene on gentoo is assembled + current (read-only)
./scripts/macbook/ue_verify_remote.sh          # add --gen to regenerate the plan first
#    expect: reload_ok: True … VERDICT: PASS … "UE scene verification PASS"

# 3. (pending) see the capture path / current state
./scripts/macbook/ue_capture_remote.sh

# 4. Pull any logs/screenshots back to this Mac
./scripts/macbook/fetch_ue_outputs.sh          # -> ./ue_outputs/
```

If MagicDNS is flaky, prefix any of the above with `GENTOO_HOST=100.64.0.32`.

## Gentoo command sequence (what the scripts run for you over SSH)

```sh
cd ~/projects/amphitheatre
.venv/bin/python scripts/unreal/verify_civicbowl.py          # offline: inputs+plan+counts
# (if on a branch that has it) .venv/bin/python scripts/unreal/verify_context.py

# live reload verify — boots a headless commandlet, loads the map, counts actors:
UEC=/mnt/storage/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd
PROJ=/mnt/data/UnrealProjects/PetoskeyCivicBowl/PetoskeyCivicBowl.uproject
"$UEC" "$PROJ" -run=pythonscript -unattended -nullrhi -nosplash \
  -script="$PWD/scripts/unreal/ue_civicbowl.py verify"
# trust the [civicbowl]/VERDICT log lines, NOT the process exit code (UE prints
# "Exiting abnormally (error code: 1)" on shutdown even on success).
```

### (Re)assemble the read-only viewer scene — explicit, separate

The helper scripts never assemble. To rebuild `/Game/Maps/CivicBowl` from the
gated, deterministic plan (regenerates the **read-only viewer**, not design truth):

```sh
cd ~/projects/amphitheatre && .venv/bin/python scripts/unreal/gen_review_meshes.py
"$UEC" "$PROJ" -run=pythonscript -unattended -nullrhi -nosplash \
  -script="$PWD/scripts/unreal/ue_civicbowl.py assemble --plan $PWD/build/unreal_scene/scene_plan.json"
```

## Capture (PENDING)

v0 assembly runs **headless `-nullrhi`** → **no pixels**. Rendered captures need a
real RHI on gentoo's GPU display (live Hyprland/Xwayland `DISPLAY=:0`). This is
**not yet wired**, and launching a GUI editor on gentoo's live desktop over SSH is
disruptive, so `ue_capture_remote.sh` will **not** do it automatically — it reports
state and the documented route:

```sh
ssh sam@gentoo.scarrow.tailnet
/mnt/data/UnrealProjects/PetoskeyCivicBowl/run_mcp_server.sh 8000 gui   # full editor on :0 (GPU)
# drive a HighResShot of camera 'ctx_cam_sunset_review' (MCP/console) ->
#   …/PetoskeyCivicBowl/Saved/Screenshots/*.png
```

Then back on the Mac: `./scripts/macbook/fetch_ue_outputs.sh`.

**Not available from MacBook yet:** live interactive 3D of the UE scene (no Pixel
Streaming / Sunshine host installed; `xpra` + `Xvfb` + `ffmpeg` are present on
gentoo as future building blocks, but UE needs GPU Vulkan, so software-GL streaming
would not be capture-trustworthy). For interactive 3D today, use the **static
viewer** or **Speckle**.

## What was validated (2026-06-22 session, on gentoo)

- Static viewer: `http://gentoo.scarrow.tailnet:8788/` and `http://100.64.0.32:8788/`
  both return **HTTP 200** (served by `scripts/serve_viewer.py`).
- SSH transport: `sshd` listening on `:22`; MacBook key `id_ed25519_mac` present in
  gentoo `authorized_keys` → `ssh sam@gentoo.scarrow.tailnet` works **from the Mac**.
- Remote offline verify: **VERDICT: PASS** (9 inputs present).
- Remote live UE reload verify: **reload_ok True**, all 9 SCENE_SPEC groups OK,
  **VERDICT: PASS**.
- `open_static_viewer.sh`: HTTP gate + browser open verified (happy + failure paths).
- `ue_verify_remote.sh` remote command body verified by direct execution on gentoo
  (offline path; live path proven by the reload verify above). The SSH-wrapped
  end-to-end run must be launched **from the MacBook** (this session can't present
  the Mac's key under `BatchMode`).

## What remains blocked / pending

- **Rendered captures from MacBook** — pending GPU/GUI wiring (see "Capture").
- **Live interactive 3D of the UE scene from MacBook** — no Pixel Streaming yet.
- **24/7 availability** — the UE host is the workstation; reachable when gentoo is
  up. (The static viewer has a `Restart=on-failure` service; UE inspection is on-demand.)
