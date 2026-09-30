#!/usr/bin/env bash
# Calls POST /api/v1/pwappload directly with curl — no wrapper code involved.
# Use it to confirm API behavior for Engineering independently of the wrapper.
#
# Usage: 01_raw_pwappload.sh <aab|ipa> [personal|team|<team_uuid>] [--no-profile]
#   --no-profile   ipa only: omit the provisioning profile (expected to fail per Engineering)
#
# Exit codes: 0 = accepted, 4 = rejected by the API (HTTP 4xx), other = network/script error
#
# Reports: HTTP status, App ID, app status, is_pwapp, and whether an automatic build (taskId) started.
source "$(dirname "$0")/common.sh"

PLATFORM="${1:?Usage: $0 <aab|ipa> [personal|team|<team_uuid>] [--no-profile]}"; check_platform "$PLATFORM"
TEAM="$(resolve_team "${2:-personal}")"
NO_PROFILE="${3:-}"
start_run "raw_${PLATFORM}_${2:-personal}${NO_PROFILE:+_noprofile}"

BODY="$RUN_DIR/request.json"
python3 - "$PLATFORM" "$NO_PROFILE" "$BODY" <<'PY'
import base64, json, os, sys
platform, no_profile, out = sys.argv[1], sys.argv[2], sys.argv[3]
body = {"pwa_address": os.environ["PWA_ADDRESS"], "pwa_platform": platform}
if os.environ.get("PWA_APP_NAME"):
    body["pwa_app_name"] = os.environ["PWA_APP_NAME"]
if platform == "ipa" and no_profile != "--no-profile":
    path = os.environ.get("IOS_MOBILEPROVISION") or sys.exit("IOS_MOBILEPROVISION is not set in env.sh")
    body["overrides"] = {"provisioning_profile": [
        {"filename": os.path.basename(path), "content": base64.b64encode(open(path, "rb").read()).decode()}]}
json.dump(body, open(out, "w"))
# Print the body with the base64 content shortened
shown = json.loads(json.dumps(body))
for p in shown.get("overrides", {}).get("provisioning_profile", []):
    p["content"] = f"<base64, {len(p['content'])} chars>"
print("Request body:", json.dumps(shown))
PY

echo "team_id: $TEAM"
HTTP_CODE=$(curl -sS -o "$RUN_DIR/response.json" -w '%{http_code}' \
  -X POST "${APPDOME_BASE_URL%/}/api/v1/pwappload?team_id=$TEAM" \
  -H "Authorization: $APPDOME_API_KEY" -H "Content-Type: application/json" \
  --data-binary "@$BODY")
echo "HTTP $HTTP_CODE"
echo "Response saved: $RUN_DIR/response.json"

python3 - "$RUN_DIR/response.json" "$HTTP_CODE" <<'PY'
import json, sys
raw, code = open(sys.argv[1]).read(), sys.argv[2]
try:
    data = json.loads(raw)
except ValueError:
    print("Non-JSON response:", raw[:1000]); sys.exit(4 if code.startswith("4") else 1)
if not code.startswith("2"):
    print("Error response:", json.dumps(data)[:1000])
    sys.exit(4 if code.startswith("4") else 1)   # 4 = rejected by the API (used by run_matrix.sh)
for item in (data if isinstance(data, list) else [data]):
    app = item.get("app") or {}
    task = (item.get("taskId") or {}).get("task_id") or item.get("task_id")
    print(f"App ID:     {app.get('id')}")
    print(f"pack_type:  {app.get('pack_type')}   is_pwapp: {app.get('is_pwapp')}   status: {app.get('status')}")
    if task:
        print(f"Build ID:   {task}   → automatic build started (Short Flow)")
    else:
        print("Build ID:   none      → upload only (no Short Flow); build with --app_id + --fusion_set_id")
PY
