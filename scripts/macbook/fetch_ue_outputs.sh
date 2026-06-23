#!/usr/bin/env bash
# Pull UE logs + any screenshots from gentoo back to MacBook (READ-ONLY pull).
#
# Copies (does not move) the UE project's Saved/Logs and Saved/Screenshots, plus
# unreal_export/captures if present, into $LOCAL_OUT. Never edits anything remote.
#
#   ./scripts/macbook/fetch_ue_outputs.sh                 # -> ./ue_outputs/
#   LOCAL_OUT=~/Desktop/civicbowl ./scripts/macbook/fetch_ue_outputs.sh
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${here}/_lib.sh"

preflight_ssh
mkdir -p "${LOCAL_OUT}" || die "cannot create LOCAL_OUT: ${LOCAL_OUT}"
ok "fetching into ${LOCAL_OUT}/"

# Resolve remote sources (skip those that don't exist) to avoid noisy errors.
# Portable to macOS default Bash 3.2: no `mapfile` (Bash 4+). Capture the remote
# listing into a string, then read it line-by-line into the srcs array.
remote_list="$(ssh_gentoo "bash -lc '
  for p in \"${REMOTE_PROJECT}/Saved/Logs\" \"${REMOTE_PROJECT}/Saved/Screenshots\" \"${REMOTE_REPO}/unreal_export/captures\"; do
    [ -e \"\$p\" ] && echo \"\$p\"
  done
  true
'")" || die "could not enumerate remote outputs."

srcs=()
while IFS= read -r line; do
  if [ -n "${line}" ]; then
    srcs+=("${line}")
  fi
done <<EOF
${remote_list}
EOF

[ "${#srcs[@]}" -gt 0 ] || { warn "nothing to fetch yet (no Logs/Screenshots/captures on gentoo — capture is pending)."; exit 0; }

use_rsync=0; command -v rsync >/dev/null 2>&1 && use_rsync=1
for s in "${srcs[@]}"; do
  info "  <- ${s}"
  if [ "${use_rsync}" = "1" ]; then
    # shellcheck disable=SC2086
    rsync -az -e "ssh ${SSH_OPTS}" "${GENTOO_USER}@${GENTOO_HOST}:${s}" "${LOCAL_OUT}/" \
      || warn "rsync failed for ${s} (skipped)"
  else
    # shellcheck disable=SC2086
    scp ${SSH_OPTS} -r "${GENTOO_USER}@${GENTOO_HOST}:${s}" "${LOCAL_OUT}/" \
      || warn "scp failed for ${s} (skipped)"
  fi
done
ok "done. Contents:"
ls -la "${LOCAL_OUT}" >&2
