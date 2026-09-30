#!/usr/bin/env bash
# Full flow through appdome_api.py --pwa: upload → build → context → Sign on Appdome → download → Certified Secure.
# Diagnostic Logs (-bl) are on.
#
# Usage: 03_full_flow.sh <aab|ipa> [personal|team|<team_uuid>] [fusion_set_id]
#   fusion_set_id  Used only when the upload is not auto-built (no Short Flow).
#                  Defaults to FS_ANDROID_TEAM / FS_IOS_TEAM for "team".
source "$(dirname "$0")/common.sh"

PLATFORM="${1:?Usage: $0 <aab|ipa> [personal|team|<team_uuid>] [fusion_set_id]}"; check_platform "$PLATFORM"
TEAM_ARG="${2:-personal}"
TEAM="$(resolve_team "$TEAM_ARG")"
FS_ID="${3:-}"
if [[ -z "$FS_ID" && "$TEAM_ARG" == "team" ]]; then
  if [[ "$PLATFORM" == "aab" ]]; then FS_ID="${FS_ANDROID_TEAM:-}"; else FS_ID="${FS_IOS_TEAM:-}"; fi
fi
start_run "full_${PLATFORM}_${TEAM_ARG}"

write_pwa_json "$PLATFORM" "$RUN_DIR/pwa.json"
FS_ARGS=()
[[ -n "$FS_ID" ]] && FS_ARGS=(--fusion_set_id "$FS_ID")

if [[ "$PLATFORM" == "aab" ]]; then
  SIGN_ARGS=(--sign_on_appdome)   # keystore / passwords / alias come from ANDROID_* in env.sh
  OUT="$RUN_DIR/signed.aab"
  EXTRA=(--sign_second_output "$RUN_DIR/universal.apk")
else
  SIGN_ARGS=(--sign_on_appdome --provisioning_profiles "${IOS_MOBILEPROVISION:?IOS_MOBILEPROVISION is not set}")
  OUT="$RUN_DIR/signed.ipa"
  EXTRA=()
fi

cd "$WRAPPER_DIR"
python3 appdome_api.py --team_id "$TEAM" --pwa "$RUN_DIR/pwa.json" ${FS_ARGS[@]+"${FS_ARGS[@]}"} -bl \
  "${SIGN_ARGS[@]}" --output "$OUT" ${EXTRA[@]+"${EXTRA[@]}"} \
  --certificate_output "$RUN_DIR/certified_secure.pdf" --certificate_json "$RUN_DIR/certified_secure.json"

echo
echo "Outputs:"; ls -la "$RUN_DIR"
grep -Eo 'App ID: [0-9a-f-]{36}' "$RUN_DIR/run.log" | sort -u || true
grep -Eo "(Build ID: |'task_id': ')[0-9a-f-]{36}" "$RUN_DIR/run.log" | sed "s/'task_id': '/Build ID: /" | sort -u || true
