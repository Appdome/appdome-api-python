# Shared helpers for the PWA test scripts. Sourced, not run.
set -euo pipefail

PWA_TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_DIR="$(dirname "$PWA_TEST_DIR")"

# PWA_TEST_ENV / PWA_TEST_RESULTS override the env file and results folder (e.g. a second account).
ENV_FILE="${PWA_TEST_ENV:-$PWA_TEST_DIR/env.sh}"
RESULTS_DIR="${PWA_TEST_RESULTS:-$PWA_TEST_DIR/results}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — copy env.example.sh to env.sh and fill it in." >&2
  exit 2
fi
# shellcheck disable=SC1090
source "$ENV_FILE"
: "${APPDOME_API_KEY:?APPDOME_API_KEY is not set in env.sh}"
unset APPDOME_TEAM_ID
APPDOME_BASE_URL="${APPDOME_SERVER_BASE_URL:-https://fusion.appdome.com/}"

# resolve_team <personal|team|uuid>  → prints the team_id value to pass
resolve_team() {
  case "${1:-personal}" in
    personal) echo "personal" ;;
    team)     : "${TEAM_ID_TEST:?TEAM_ID_TEST is not set in env.sh}"; echo "$TEAM_ID_TEST" ;;
    *)        echo "$1" ;;
  esac
}

# check_platform <aab|ipa>
check_platform() {
  [[ "$1" == "aab" || "$1" == "ipa" ]] || { echo "Platform must be aab or ipa (got '$1')" >&2; exit 2; }
}

# start_run <name>  → creates results/<timestamp>_<name>, sets RUN_DIR, tees all output to RUN_DIR/run.log
start_run() {
  RUN_DIR="$RESULTS_DIR/$(date +%Y%m%d_%H%M%S)_$1"
  mkdir -p "$RUN_DIR"
  exec > >(tee -a "$RUN_DIR/run.log") 2>&1
  echo "=== $1 — $(date) ==="
  echo "Results: $RUN_DIR"
}

# write_pwa_json <aab|ipa> <out_file>
write_pwa_json() {
  python3 - "$1" "$2" <<PY
import json, os, sys
config = {"pwa_address": os.environ["PWA_ADDRESS"], "pwa_platform": sys.argv[1]}
if os.environ.get("PWA_APP_NAME"):
    config["pwa_app_name"] = os.environ["PWA_APP_NAME"]
json.dump(config, open(sys.argv[2], "w"), indent=2)
PY
  sed 's/^/  /' "$2"; echo
}
