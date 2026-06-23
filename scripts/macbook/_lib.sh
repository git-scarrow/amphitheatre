#!/usr/bin/env bash
# Shared helpers for the MacBook-m4 -> Gentoo CivicBowl UE operator scripts.
#
# These are READ-ONLY operator tools. They open the static viewer, run remote
# verification, and pull logs/screenshots back. They never edit accepted
# geometry, Speckle, the static-viewer data, or any design ledger. `source` this
# from the sibling scripts; do not run it directly.
#
# All connection details come from ENV (no secrets, no hardcoded keys):
#   GENTOO_HOST     tailnet host of the UE host   (default gentoo.scarrow.tailnet)
#   GENTOO_USER     ssh user                       (default sam)
#   REMOTE_REPO     repo path ON gentoo            (default ~/projects/amphitheatre)
#   REMOTE_PROJECT  UE project dir ON gentoo       (default /mnt/data/UnrealProjects/PetoskeyCivicBowl)
#   UE_CMD          UnrealEditor-Cmd ON gentoo     (default .../UnrealEngine-5.8/.../UnrealEditor-Cmd)
#   VIEWER_URL      static Three.js viewer URL     (default http://gentoo.scarrow.tailnet:8788/)
#   SSH_OPTS        extra ssh options              (default -o ConnectTimeout=10)
#   LOCAL_OUT       local dir for fetched outputs  (default ./ue_outputs)
set -euo pipefail

GENTOO_HOST="${GENTOO_HOST:-gentoo.scarrow.tailnet}"
GENTOO_USER="${GENTOO_USER:-sam}"
REMOTE_REPO="${REMOTE_REPO:-~/projects/amphitheatre}"          # remote ~ — do NOT expand locally
REMOTE_PROJECT="${REMOTE_PROJECT:-/mnt/data/UnrealProjects/PetoskeyCivicBowl}"
UE_CMD="${UE_CMD:-/mnt/storage/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd}"
VIEWER_URL="${VIEWER_URL:-http://gentoo.scarrow.tailnet:8788/}"
SSH_OPTS="${SSH_OPTS:--o ConnectTimeout=10}"
LOCAL_OUT="${LOCAL_OUT:-./ue_outputs}"

c_red=$'\033[31m'; c_grn=$'\033[32m'; c_ylw=$'\033[33m'; c_rst=$'\033[0m'
info() { printf '%s\n' "$*" >&2; }
ok()   { printf '%s%s%s\n' "$c_grn" "$*" "$c_rst" >&2; }
warn() { printf '%s%s%s\n' "$c_ylw" "$*" "$c_rst" >&2; }
die()  { printf '%sERROR:%s %s\n' "$c_red" "$c_rst" "$*" >&2; exit 1; }

# ssh wrapper. Usage: ssh_gentoo '<remote bash command>'
ssh_gentoo() {
  # shellcheck disable=SC2086
  ssh $SSH_OPTS -o BatchMode=yes "${GENTOO_USER}@${GENTOO_HOST}" "$@"
}

# Fail early with an actionable message if gentoo is unreachable by ssh.
preflight_ssh() {
  command -v ssh >/dev/null 2>&1 || die "ssh not found on this Mac."
  if ! ssh_gentoo 'true' 2>/dev/null; then
    die "cannot SSH to ${GENTOO_USER}@${GENTOO_HOST}.
  - Is Tailscale up on this Mac?           tailscale status | grep gentoo
  - Is the host name resolving?            ping -c1 ${GENTOO_HOST}
  - Is your key authorized on gentoo?      ssh ${GENTOO_USER}@${GENTOO_HOST} hostname
  - Override target with env:              GENTOO_HOST=100.64.0.32 $0 ..."
  fi
}
