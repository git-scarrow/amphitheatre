#!/usr/bin/env bash
# Verify the Gentoo-hosted Unreal UE 5.8 CivicBowl scene from MacBook (READ-ONLY).
#
# Runs, over SSH on gentoo:
#   1. offline  scripts/unreal/verify_civicbowl.py        (inputs + plan + counts)
#   2. offline  scripts/unreal/verify_context.py          (if present on the branch)
#   3. live     ue_civicbowl.py verify  (boots UnrealEditor-Cmd -nullrhi, loads
#               /Game/Maps/CivicBowl, counts actors vs SCENE_SPEC)  unless --no-live
#
# Nothing here assembles or edits geometry. To (re)assemble the read-only viewer
# scene, see docs/MACBOOK_UNREAL_CLIENT.md (explicit, separate command).
#
#   ./scripts/macbook/ue_verify_remote.sh             # offline + live verify
#   ./scripts/macbook/ue_verify_remote.sh --gen       # regenerate plan first (offline, safe)
#   ./scripts/macbook/ue_verify_remote.sh --no-live   # skip the UE boot (offline only)
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${here}/_lib.sh"

DO_GEN=0; DO_LIVE=1
for a in "$@"; do
  case "$a" in
    --gen) DO_GEN=1 ;;
    --no-live) DO_LIVE=0 ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) die "unknown arg: $a" ;;
  esac
done

preflight_ssh
ok "ssh ${GENTOO_USER}@${GENTOO_HOST} reachable"

# Build the remote command. Quote the heredoc marker so $vars expand on gentoo.
remote_cmd() {
cat <<REMOTE
set -e
cd ${REMOTE_REPO} || { echo "REMOTE: repo not found: ${REMOTE_REPO}"; exit 3; }
PY=.venv/bin/python; [ -x "\$PY" ] || PY=python3
echo "== gentoo: \$(hostname)  repo: \$(pwd)  branch: \$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
if [ "${DO_GEN}" = "1" ]; then
  echo "== offline gen (regenerable, read-only wrt design truth) =="
  "\$PY" scripts/unreal/gen_review_meshes.py >/dev/null && echo "  gen_review_meshes: ok"
  [ -f scripts/unreal/gen_context.py ] && "\$PY" scripts/unreal/gen_context.py >/dev/null && echo "  gen_context: ok" || true
fi
echo "== offline verify_civicbowl.py =="
"\$PY" scripts/unreal/verify_civicbowl.py | grep -E "required inputs|VERDICT" || true
if [ -f scripts/unreal/verify_context.py ]; then
  echo "== offline verify_context.py =="
  "\$PY" scripts/unreal/verify_context.py | grep -E "^\[|VERDICT" || true
fi
if [ "${DO_LIVE}" = "1" ]; then
  echo "== live UE reload verify (UnrealEditor-Cmd -nullrhi, read-only) =="
  PROJ=\$(ls ${REMOTE_PROJECT}/*.uproject 2>/dev/null | head -1)
  [ -n "\$PROJ" ] || { echo "REMOTE: no .uproject under ${REMOTE_PROJECT}"; exit 4; }
  LOG=${REMOTE_PROJECT}/Saved/Logs/\$(basename "\${PROJ%.uproject}").log
  timeout 300 "${UE_CMD}" "\$PROJ" -run=pythonscript -unattended -nullrhi -nosplash \
    -script="\$(pwd)/scripts/unreal/ue_civicbowl.py verify" >/dev/null 2>&1 || true
  grep -aE "reload_ok|MISMATCH|VERDICT: " "\$LOG" | tail -12
fi
REMOTE
}

out="$(ssh_gentoo "bash -lc $(printf '%q' "$(remote_cmd)")")" || die "remote verify failed (see output above)"
printf '%s\n' "$out"

# Gate on the live VERDICT if we ran it, else the offline one.
if printf '%s' "$out" | grep -qE "VERDICT: PASS|VERDICT: PASS \(offline\)"; then
  if printf '%s' "$out" | grep -qiE "MISMATCH|VERDICT: FAIL|ISSUES"; then
    die "verification reported problems — see above."
  fi
  ok "UE scene verification PASS"
else
  die "no PASS verdict found — see output above."
fi
