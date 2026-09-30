#!/usr/bin/env bash
# Shows the status of a Build ID (task). Useful for a Short Flow auto-build started by 01_raw_pwappload.sh.
#
# Usage: 04_task_status.sh <build_id> [personal|team|<team_uuid>]
source "$(dirname "$0")/common.sh"
TASK_ID="${1:?Usage: $0 <build_id> [personal|team|<team_uuid>]}"
TEAM="$(resolve_team "${2:-personal}")"
curl -sS "${APPDOME_BASE_URL%/}/api/v1/tasks/$TASK_ID/status?team_id=$TEAM" -H "Authorization: $APPDOME_API_KEY"
echo
