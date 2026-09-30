# PWA test scripts

Scripts for testing PWA support against the live Appdome API, based on Engineering's answer (2026-09-30):

1. iOS (`ipa`) works when the request `overrides` include the provisioning profile, base64 encoded.
2. The upload is done when the response's `app` object is returned (`status: active`); `app.id` is the App ID.
3. Short Flow accounts build automatically with the default Playground Fusion Set. Without Short Flow the upload only
   creates the app, and it's built with the regular build API and a chosen Fusion Set.

## Setup

```bash
cd appdome-api-python/pwa_test
cp env.example.sh env.sh     # fill in API key, team, Fusion Sets, signing files
./00_unit_tests.sh           # offline, no API calls
```

`env.sh` and `results/` are git-ignored. Every run writes its own folder under `results/` (log, request, response,
signed app, Certified Secure). Scripts always pass `--team_id` explicitly, and ignore `APPDOME_TEAM_ID`.
`team` means `TEAM_ID_TEST` from `env.sh`; you can also pass a team UUID.

## Scripts

| Script | What it does |
|---|---|
| `00_unit_tests.sh` | Offline unit tests (mocked API) |
| `01_raw_pwappload.sh <aab\|ipa> [personal\|team] [--no-profile]` | Calls `/pwappload` with curl, no wrapper code. Reports App ID, status and whether a Build ID came back |
| `02_pwa_upload.sh <aab\|ipa> [personal\|team]` | Upload via `pwa_upload.py`, waits for the Short Flow build if any |
| `03_full_flow.sh <aab\|ipa> [personal\|team] [fusion_set_id]` | `appdome_api.py --pwa`: upload, build, context, Sign on Appdome, download, Certified Secure, with Diagnostic Logs |
| `04_task_status.sh <build_id> [personal\|team]` | Raw task status |
| `run_matrix.sh [case ...]` | Runs the cases below and prints PASS/FAIL |

## Test matrix

| Case | Expected |
|---|---|
| `raw-aab` | 200, App ID, Build ID if the personal account has Short Flow |
| `raw-ipa` | 200, `pack_type: ipa` (new — iOS with profile) |
| `raw-ipa-noprof` | Rejected (4xx). PASS means it was rejected, confirming the profile is what makes iOS work |
| `raw-aab-team` | 200, App ID, **no** Build ID (team has no Short Flow) |
| `raw-ipa-team` | 200, App ID, no Build ID |
| `full-aab` | Signed .aab + universal .apk + Certified Secure |
| `full-ipa` | Signed .ipa + Certified Secure (new) |
| `full-aab-team` | Built with `FS_ANDROID_TEAM`, signed .aab |
| `full-ipa-team` | Built with `FS_IOS_TEAM`, signed .ipa |

Suggested order: `./run_matrix.sh unit raw-ipa raw-ipa-noprof`, then `full-ipa`, then the rest.
Record the Build IDs from each `run.log` in the ticket.

Things to check while testing:
- Whether the personal account returns a Build ID (i.e. has Short Flow). If it doesn't, personal runs need a Fusion
  Set too (`03_full_flow.sh aab personal <fs_id>`).
- `raw-ipa`: whether the upload uses the provisioning profile's bundle ID / team, and whether signing with the same
  profile succeeds.
- Short Flow runs log a warning if a Fusion Set is passed, since the automatic build already used the Playground one.
