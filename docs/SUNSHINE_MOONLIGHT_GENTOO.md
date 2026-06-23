# Interactive UE viewing from MacBook — Sunshine (gentoo) + Moonlight (Mac)

GPU-accelerated, **tailnet-only** remote viewing of the **live gentoo Hyprland
session** (RTX 4080 SUPER) from macbook-m4, so the **Unreal UE 5.8 CivicBowl
scene** can be inspected interactively with real lighting/materials — not the
crude `-nullrhi` commandlet, and not screenshots.

This is a **fourth** surface, distinct from the other three:

| Surface | What | Where |
|---|---|---|
| Static Three.js viewer | browser review surface, always-on, read-only | `http://gentoo.scarrow.tailnet:8788/` |
| Unreal UE 5.8 scene (commandlet) | reproducible read-only inspection target | SSH / `ue_civicbowl.py verify` |
| Speckle | interactive 3D review/publishing | `https://speckle-review.scarrow.tailnet` |
| **Sunshine + Moonlight (this doc)** | **interactive GPU view of the real UE editor** | Moonlight app → `gentoo.scarrow.tailnet` |

It does **not** replace the static-viewer or read-only SSH workflows; it adds a
GPU desktop-stream path. Nothing here changes project geometry or scene content.

## What was set up on gentoo

- **`net-misc/sunshine` 2026.516.143833-r1** (LizardByte), in-tree, USE `cuda`
  (NVENC) `wayland X libdrm filecaps pipewire systemd vulkan`. The binary carries
  `cap_sys_admin,cap_sys_nice=p` for KMS grab.
  - Build needed a no-LTO env (its bundled FFmpeg's x86 asm won't link with the
    global `-flto`): `/etc/portage/package.env/sunshine` → `net-misc/sunshine no-lto.conf`
    (mirrors the existing `media-video/ffmpeg` exception).
- **Capture:** Wayland `zwlr_screencopy_manager_v1` (wlroots) of the live Hyprland
  monitor `HDMI-A-1` (Samsung Odyssey G85SB, 3440×1440). **Encode:** `hevc_nvenc`
  /`h264_nvenc`/`av1_nvenc` on the 4080 (hardware) — verified streaming 60 fps,
  Opus audio.
- **User service:** `~/.config/systemd/user/sunshine.service` with the session env
  baked in (`WAYLAND_DISPLAY=wayland-1`, `DISPLAY=:0`). Runs as sam inside the
  graphical session.
- **Web-UI admin creds:** user `sam`; password stored at
  `~/.config/sunshine/.webui_pass_note` (chmod 600). Change it in the web UI if you like.
- **Tailnet-only firewall:** independent nft table `sunshine_guard` (does not touch
  the Docker-managed rules) drops Sunshine's ports on every interface except `lo`
  and `tailscale0`. Persisted by `sunshine-fw.service` (+ `/etc/sunshine-fw.nft`),
  enabled at boot.
- **macbook-m4:** Moonlight already in `/Applications/Moonlight.app`; **paired**
  over the tailnet (PIN handshake via the CLI + Sunshine `/api/pin`).

## Prerequisites

- **MacBook:** Tailscale up; Moonlight installed (`brew install --cask moonlight`
  if ever missing). No other setup — pairing is already done.
- **gentoo:** the Hyprland graphical session must be **logged in and running**
  (Sunshine captures *that* session; it is not a headless/virtual display).

## Start / stop Sunshine (on gentoo)

The service is a **user** unit, so use sam's user systemd (from an SSH/tty shell
you need the runtime dir):

```sh
export XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
systemctl --user start   sunshine     # start
systemctl --user stop    sunshine     # stop
systemctl --user status  sunshine     # check
journalctl --user -u sunshine -e      # logs (also ~/.config/sunshine/sunshine.log)
# persist across logins (optional; pins WAYLAND_DISPLAY=wayland-1 — see Limitations):
systemctl --user enable  sunshine
```

The firewall guard is a **system** service: `sudo systemctl start|stop sunshine-fw`.

## Connect from MacBook (interactive)

Moonlight's stream window needs the Mac's GUI — drive it from the **Moonlight
app**, not SSH:

1. Open **Moonlight** on the Mac. The host **gentoo** appears (paired). If not,
   add it manually: **+** → `gentoo.scarrow.tailnet`.
2. Click **gentoo** → pick an app:
   - **Desktop** — the whole Hyprland desktop (use this to watch the UE editor).
   - *Low Res Desktop* / *Steam Big Picture* are Sunshine defaults.
3. The 4080-encoded stream opens. Close with **Ctrl+Alt+Shift+Q** (Moonlight quit).

CLI equivalents (the GUI is preferred for actual viewing):
```sh
/Applications/Moonlight.app/Contents/MacOS/Moonlight list   gentoo.scarrow.tailnet
/Applications/Moonlight.app/Contents/MacOS/Moonlight stream gentoo.scarrow.tailnet "Desktop"
```

## Open the CivicBowl UE scene (on gentoo)

Launch the **full editor** (GPU/Vulkan) opening the map, into the live session —
then watch it via Moonlight → Desktop:

```sh
cd /mnt/data/UnrealProjects/PetoskeyCivicBowl
DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 \
  /mnt/storage/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor \
  "$PWD/PetoskeyCivicBowl.uproject" /Game/Maps/CivicBowl -stdout >/tmp/ue_editor_gui.log 2>&1 &
```
First launch compiles global shaders (several minutes; the viewport appears after).
This is the **read-only inspection** scene — don't move/edit geometry; any change
must still return as an EPSG:6494 proposal through the repo gates.

## Security / tailnet binding

- Sunshine listens on `0.0.0.0` but the **`sunshine_guard` nft table drops its
  ports (TCP 47984/47989/47990/48010, UDP 47998/47999/48000/48002/48010) on
  everything except `lo` + `tailscale0`** → reachable only over the tailnet
  (preferably to `100.64.0.32`). Verify: `sudo nft list table inet sunshine_guard`.
- Web UI (47990) is password-protected (basic auth) and tailnet-only via the same
  guard. Pairing a new client needs the PIN entered there (or via `/api/pin`).
- Not exposed publicly; no port-forward; Pixel Streaming intentionally not used.

## Known limitations

- **Single Wayland monitor** captured (`HDMI-A-1`). Multi-output needs config.
- **Capture is the *live* session** — whatever is on the gentoo desktop is what you
  see (and Moonlight input controls it). It is not a separate virtual desktop.
- **Streaming can't be driven over SSH** — Moonlight needs the Mac's GUI to open
  the video window (verified: a stream established over the tailnet but rendered no
  window headlessly). Use the Moonlight app.
- **The user service pins `WAYLAND_DISPLAY=wayland-1`** (the current socket). If a
  future Hyprland session uses a different socket, edit the unit and
  `systemctl --user daemon-reload`.
- **NVIDIA + Wayland**: works via wlr-screencopy here; if capture ever breaks after
  a driver update, check `~/.config/sunshine/sunshine.log` for the `[wlgrab]` lines.

## Rollback / removal

```sh
# stop + disable services
export XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
systemctl --user disable --now sunshine
sudo systemctl disable --now sunshine-fw
sudo nft delete table inet sunshine_guard 2>/dev/null

# remove host config + units
rm -f ~/.config/systemd/user/sunshine.service && systemctl --user daemon-reload
sudo rm -f /etc/systemd/system/sunshine-fw.service /etc/sunshine-fw.nft && sudo systemctl daemon-reload

# uninstall Sunshine (+ the build env exception)
sudo emerge --deselect net-misc/sunshine && sudo emerge -cav net-misc/sunshine
sudo rm -f /etc/portage/package.env/sunshine
# optional: drop the Sunshine config + paired clients
rm -rf ~/.config/sunshine
# Moonlight on the Mac stays; remove with: brew uninstall --cask moonlight
```
