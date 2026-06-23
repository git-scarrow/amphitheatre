#!/usr/bin/env bash
# Render/capture a frame of the Gentoo UE 5.8 CivicBowl scene for MacBook review.
#
# STATUS: PENDING (GPU/GUI capture is not yet wired). v0 assembly runs headless
# with -nullrhi, which produces NO pixels. Rendered captures need a real RHI on
# gentoo's GPU display (DISPLAY=:0, live Hyprland/Xwayland session).
#
# This script is deliberately NON-DISRUPTIVE: it will NOT spawn a GUI editor on
# gentoo's live desktop on its own (that would pop windows on the workstation).
# It reports the current state and the exact documented commands, and only issues
# a screenshot if a GPU editor is ALREADY running AND you set UE_CAPTURE_CONFIRM=1.
#
#   ./scripts/macbook/ue_capture_remote.sh           # show state + pending path
# See docs/MACBOOK_UNREAL_CLIENT.md "Capture (pending)" for the full route.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${here}/_lib.sh"

preflight_ssh
ok "ssh ${GENTOO_USER}@${GENTOO_HOST} reachable"

state="$(ssh_gentoo "bash -lc '
  echo display=\${DISPLAY:-none}
  if pgrep -x UnrealEditor >/dev/null 2>&1; then echo gui_editor=running; else echo gui_editor=none; fi
  ls -td ${REMOTE_PROJECT}/Saved/Screenshots/* 2>/dev/null | head -1 | sed \"s|^|latest_shot=|\" || true
'")" || die "could not query gentoo capture state."
printf '%s\n' "$state" >&2

gui_running="$(printf '%s' "$state" | sed -n 's/^gui_editor=//p')"

warn "Capture is PENDING — headless -nullrhi assembly renders no pixels."
cat >&2 <<EOF

To capture (a human at/over gentoo, or once wired):
  GUI/GPU route (renders on gentoo's DISPLAY=:0):
    ssh ${GENTOO_USER}@${GENTOO_HOST}
    ${REMOTE_PROJECT}/run_mcp_server.sh 8000 gui      # full editor on :0 (GPU)
    # then drive a HighResShot of camera 'ctx_cam_sunset_review' (MCP or console),
    # which writes a PNG under ${REMOTE_PROJECT}/Saved/Screenshots/
  Pull it back to this Mac:
    ./scripts/macbook/fetch_ue_outputs.sh

Not available from MacBook yet: live interactive 3D of the UE scene (no Pixel
Streaming / Sunshine host installed). Use the static viewer for interactive 3D.
EOF

if [ "${UE_CAPTURE_CONFIRM:-0}" = "1" ] && [ "${gui_running}" = "running" ]; then
  warn "UE_CAPTURE_CONFIRM=1 and a GUI editor is already running — but issuing a"
  warn "HighResShot needs the MCP session/console; this is intentionally left to"
  warn "the documented interactive path so we never touch the live desktop blindly."
fi
exit 0
