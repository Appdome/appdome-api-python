#!/usr/bin/env bash
# Upload only, through the wrapper's pwa_upload.py (no signing). Waits for the automatic build if one starts.
#
# Usage: 02_pwa_upload.sh <aab|ipa> [personal|team|<team_uuid>]
source "$(dirname "$0")/common.sh"

PLATFORM="${1:?Usage: $0 <aab|ipa> [personal|team|<team_uuid>]}"; check_platform "$PLATFORM"
TEAM="$(resolve_team "${2:-personal}")"
start_run "upload_${PLATFORM}_${2:-personal}"

write_pwa_json "$PLATFORM" "$RUN_DIR/pwa.json"
PROFILE_ARGS=()
[[ "$PLATFORM" == "ipa" ]] && PROFILE_ARGS=(--provisioning_profiles "${IOS_MOBILEPROVISION:?IOS_MOBILEPROVISION is not set}")

cd "$WRAPPER_DIR"
python3 pwa_upload.py --team_id "$TEAM" --pwa_config "$RUN_DIR/pwa.json" ${PROFILE_ARGS[@]+"${PROFILE_ARGS[@]}"} --wait \
  | tee "$RUN_DIR/uploads.json"
