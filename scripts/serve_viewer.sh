#!/usr/bin/env bash
# Serve the web viewer on a private/unlisted URL with live reload.
#
#   amphitheatre.scarrow.net  (Cloudflare tunnel)  ->  127.0.0.1:8788  (serve_viewer.py)
#
# The page auto-reloads whenever web_viewer/ changes; with --rebuild it also
# re-runs build_truth_package.py when an upstream source file is edited, which
# regenerates site_data.js and triggers the reload.
#
# Why the explicit --config: cloudflared on this host otherwise loads a shared
# default config whose ingress silently overrides everything and 404s the edge
# (memory: cloudflared-config-override-gotcha). Always name the config.
#
# Usage:
#   scripts/serve_viewer.sh              # serve + live reload
#   scripts/serve_viewer.sh --rebuild    # also rebuild on source edits
#   PORT=8788 scripts/serve_viewer.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8788}"
TUNNEL_CONFIG="${TUNNEL_CONFIG:-$HOME/.cloudflared/amphitheatre.yml}"
HOSTNAME_URL="https://amphitheatre.scarrow.net"
PY="$REPO/.venv/bin/python"; [ -x "$PY" ] || PY="python3"

REBUILD_FLAG=""
[ "${1:-}" = "--rebuild" ] && REBUILD_FLAG="--rebuild"

# 1. Ensure the data payload exists (first run on a fresh checkout).
if [ ! -f "$REPO/web_viewer/data/site_data.js" ]; then
  echo "[serve_viewer.sh] site_data.js missing — building once..."
  "$PY" "$REPO/scripts/build_truth_package.py"
fi

cleanup() {
  echo "[serve_viewer.sh] stopping..."
  [ -n "${SERVER_PID:-}" ] && kill "$SERVER_PID" 2>/dev/null || true
  [ -n "${TUNNEL_PID:-}" ] && kill "$TUNNEL_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 2. Start the live-reload static server.
echo "[serve_viewer.sh] starting server on 127.0.0.1:$PORT ${REBUILD_FLAG:+(rebuild-on-source-edit)}"
"$PY" "$REPO/scripts/serve_viewer.py" --port "$PORT" $REBUILD_FLAG &
SERVER_PID=$!
sleep 1
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "[serve_viewer.sh] server failed to start" >&2; exit 1
fi

# 3. Start the cloudflared tunnel (explicit config — see note above).
if [ ! -f "$TUNNEL_CONFIG" ]; then
  echo "[serve_viewer.sh] tunnel config not found: $TUNNEL_CONFIG" >&2
  echo "  (server is still up locally at http://127.0.0.1:$PORT)" >&2
  wait "$SERVER_PID"
fi
echo "[serve_viewer.sh] starting cloudflared tunnel (config: $TUNNEL_CONFIG)"
cloudflared tunnel --config "$TUNNEL_CONFIG" run amphitheatre &
TUNNEL_PID=$!

sleep 4
echo
echo "  ┌─────────────────────────────────────────────────────────────┐"
echo "  │  Live viewer:  $HOSTNAME_URL"
echo "  │  Local:        http://127.0.0.1:$PORT/"
echo "  │  Live reload:  ON   ${REBUILD_FLAG:+(+ rebuild on source edits)}"
echo "  └─────────────────────────────────────────────────────────────┘"
echo "  Ctrl-C to stop both the server and the tunnel."
echo

wait
