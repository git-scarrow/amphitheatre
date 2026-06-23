#!/usr/bin/env bash
# Open the STATIC Three.js review viewer (read-only browser surface) from MacBook.
#
# This is NOT the Unreal scene and NOT Speckle — it is the always-on static
# web viewer served from gentoo over tailnet. See docs/MACBOOK_UNREAL_CLIENT.md.
#
#   ./scripts/macbook/open_static_viewer.sh          # check + open in browser
#   VIEWER_URL=http://100.64.0.32:8788/ ./scripts/macbook/open_static_viewer.sh
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${here}/_lib.sh"

info "Static Three.js viewer (browser review surface, always-on, read-only)"
info "URL: ${VIEWER_URL}"

code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "${VIEWER_URL}" || true)"
if [ "${code}" != "200" ]; then
  die "viewer did not return 200 (got '${code:-no response}').
  - Is Tailscale up on this Mac?                 tailscale status | grep gentoo
  - Is the viewer service up on gentoo?          ssh ${GENTOO_USER}@${GENTOO_HOST} systemctl is-active petoskey-viewer
  - Try the raw tailnet IP:                       VIEWER_URL=http://100.64.0.32:8788/ $0"
fi
ok "viewer responded HTTP 200"

if command -v open >/dev/null 2>&1; then        # macOS
  open "${VIEWER_URL}"
elif command -v xdg-open >/dev/null 2>&1; then  # linux fallback
  xdg-open "${VIEWER_URL}"
else
  warn "no 'open'/'xdg-open' — point your browser at: ${VIEWER_URL}"
fi
