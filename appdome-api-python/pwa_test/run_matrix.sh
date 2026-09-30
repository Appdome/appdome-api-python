#!/usr/bin/env bash
# Runs the PWA test matrix and prints a PASS/FAIL summary. Each case keeps its own folder under results/.
#
# Usage: run_matrix.sh [case ...]      (no args = all cases)
# Cases:
#   unit            offline unit tests
#   raw-aab         raw API, Android, personal
#   raw-ipa         raw API, iOS with provisioning profile, personal
#   raw-ipa-noprof  raw API, iOS without profile (PASS = the API rejects it with HTTP 4xx)
#   raw-aab-team    raw API, Android, team (expect upload only, no Build ID)
#   raw-ipa-team    raw API, iOS, team
#   full-aab        appdome_api.py --pwa, Android, personal
#   full-ipa        appdome_api.py --pwa, iOS, personal
#   full-aab-team   appdome_api.py --pwa, Android, team + FS_ANDROID_TEAM
#   full-ipa-team   appdome_api.py --pwa, iOS, team + FS_IOS_TEAM
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
ALL=(unit raw-aab raw-ipa raw-ipa-noprof raw-aab-team raw-ipa-team full-aab full-ipa full-aab-team full-ipa-team)
if [[ $# -eq 0 ]]; then CASES=("${ALL[@]}"); else CASES=("$@"); fi   # bash 3.2 (macOS) safe

run_case() {
  case "$1" in
    unit)           "$DIR/00_unit_tests.sh" ;;
    raw-aab)        "$DIR/01_raw_pwappload.sh" aab personal ;;
    raw-ipa)        "$DIR/01_raw_pwappload.sh" ipa personal ;;
    raw-ipa-noprof) "$DIR/01_raw_pwappload.sh" ipa personal --no-profile; [[ $? -eq 4 ]] ;;
    raw-aab-team)   "$DIR/01_raw_pwappload.sh" aab team ;;
    raw-ipa-team)   "$DIR/01_raw_pwappload.sh" ipa team ;;
    full-aab)       "$DIR/03_full_flow.sh" aab personal ;;
    full-ipa)       "$DIR/03_full_flow.sh" ipa personal ;;
    full-aab-team)  "$DIR/03_full_flow.sh" aab team ;;
    full-ipa-team)  "$DIR/03_full_flow.sh" ipa team ;;
    *) echo "Unknown case: $1"; return 2 ;;
  esac
}

SUMMARY=()
for c in "${CASES[@]}"; do
  echo; echo "################ $c ################"
  start=$(date +%s)
  if run_case "$c"; then r=PASS; else r=FAIL; fi
  SUMMARY+=("$(printf '%-16s %s  (%ss)' "$c" "$r" "$(( $(date +%s) - start ))")")
done

echo; echo "================ Summary ================"
RESULTS="${PWA_TEST_RESULTS:-$DIR/results}"; mkdir -p "$RESULTS"
printf '%s\n' "${SUMMARY[@]}" | tee "$RESULTS/summary_$(date +%Y%m%d_%H%M%S).txt"
