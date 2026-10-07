# Appdome Python Client Library
Python client library for interacting with https://fusion.appdome.com/ tasks API.

Each API endpoint has its own file and `main` function for a single API call.

`appdome_api.py` contains the whole flow of a task from upload to download.

All APIs are documented in https://apis.appdome.com/docs.

---
**For detailed information about each step and more advanced use, please refer to the [detailed usage examples](./appdome-api-python/README.md)**

---

## Requirements
- Python **3.7 or later**
- `requests` library **>= 2.28.0`


## Basic Flow Usage

## Examples
#### Android Example:

```python
python3 appdome_api.py \
--api_key <api key> \
--fusion_set_id <fusion-set-id> \
--team_id <team-id> \
--app <apk/aab file> \
--sign_on_appdome \
--keystore <keystore file> \
--keystore_pass <keystore password> \
--keystore_alias <key alias> \
--key_pass <key password> \
--output <output apk/aab> \
--build_to_test_vendor <bitbar,saucelabs,browserstack,lambdatest,perfecto,firebase,aws_device_farm,app_debug,app_profiler> \
--certificate_output <output certificate pdf> \
--deobfuscation_script_output <file path for downloading deobfuscation zip file> \
--build_overrides <json_file_path> \
--context_overrides <json_file_path> \
--sign_overrides <json_file_path>
--firebase_app_id <app-id for uploading mapping file for crashlytics (requires --deobfuscation_script_output and firebase CLI tools)>
--datadog_api_key <datadog api key for uploading mapping file to datadog (requires --deobfuscation_script_output)>
--baseline_profile <zip file for build with baseline profile>
--startup_profile <zip file for build with startup profile>
--input_mapping <txt file for build with input obfuscation/minimization mapping>
--cert_pinning_zip <zip file containing dynamic certificates>
--signing_fingerprint_list <path_to_json_file> \
--new_bundle_id <new bundle id>
--new_version <new app version>
--new_build_num <new app build number>
--new_display_name <new app display name>
```

#### Android SDK Example:

Required inputs for this sample are the API key, team ID, Fusion Set ID, SDK file, protected SDK output path, and
Certified Secure PDF output path. For Android SDK Protect only, include `--deobfuscation_script_output` when you want the Obfuscate SDK Logic
mapping ZIP downloaded as part of the same run.

```python
python3 appdome_api_sdk.py \
--api_key <api key> \
--fusion_set_id <fusion-set-id> \
--team_id <team-id> \
--app <aar> \
--output <output aar> \
--certificate_output <output Certified Secure pdf> \
--deobfuscation_script_output <file path for downloading deobfuscation zip file> \
--build_overrides <json_file_path> 
```

#### iOS Example:

```python
python3 appdome_api.py \
--api_key <api key> \
--fusion_set_id <fusion-set-id> \
--team_id <team-id> \
--app <ipa file> \
--sign_on_appdome \
--keystore <p12 file> \
--keystore_pass <p12 password> \
--provisioning_profiles <provisioning profile file> <another provisioning profile file if needed> \
--entitlements <entitlements file> <another entitlements file if needed> \
--output <output ipa> \
--certificate_output <output certificate pdf> \
--build_overrides <json_file_path> \
--context_overrides <json_file_path> \
--sign_overrides <json_file_path>
--cert_pinning_zip <zip file containing dynamic certificates>
--new_bundle_id <new bundle id>
--new_version <new app version>
--new_build_num <new app build number>
--new_display_name <new app display name>
```

#### iOS SDK Example:

Required inputs for this sample are the API key, team ID, Fusion Set ID, SDK file, protected SDK output path, and
Certified Secure PDF output path. The keystore inputs are only needed for Appdome signing. Deobfuscation mapping
files are only available for Android SDK Protect.

```python
python3 appdome_api_sdk.py \
--api_key <api key> \
--fusion_set_id <fusion set id> \
--team_id <team id> \
--app <zip file> \
--keystore <p12 file> \  # only needed for sign on Appdome
--keystore_pass <p12 password> \ # only needed for sign on Appdome
--output <output zip> \
--certificate_output <output Certified Secure pdf> \
--build_overrides <json_file_path> 
```

#### PWA Example:

Pass `--pwa` with a PWA config JSON instead of `--app`. Use Android or iOS signing parameters to match `pwa_platform` (`aab` or `ipa`). See [detailed usage](./appdome-api-python/README.md#pwa-upload) for the config format.

```python
python3 appdome_api.py \
--api_key <api key> \
--team_id <team-id> \
--pwa <pwa config json file> \
--fusion_set_id <fusion-set-id> \
--sign_on_appdome \
--keystore <keystore file> \
--keystore_pass <keystore password> \
--keystore_alias <key alias> \
--key_pass <key password> \
--output <output aab> \
--certificate_output <output certificate pdf>
```

## Signing Fingerprint List (Android only)

The `--signing_fingerprint_list` option allows you to specify a list of trusted signing fingerprints for Android applications. This is useful when you need to trust multiple signing certificates.

**Important Notes:**
- This option is **only valid for Android applications** (APK/AAB files)
- It is **mutually exclusive** with `--google_play_signing`, `--signing_fingerprint`, and `--signing_fingerprint_upgrade`
- You cannot use `--signing_fingerprint_list` together with any of the other signing fingerprint options

### Usage

```bash
--signing_fingerprint_list <path_to_json_file>
```

**JSON File Format:**
The JSON file should contain an array of fingerprint objects. Each object must include:
- `SHA`: The SHA-1 or SHA-256 certificate fingerprint (required)
- `TrustedStoreSigning`: true/false Indicates whether the certificate fingerprint is used for store submissions (e.g., Google Play). (Optional; defaults to false)

**Example JSON file (`fingerprints.json`):**
```json
[
  {
    "SHA": "E71186B4D94016F0A3F2A68DF5BC75D27CA307663C6DFDE5923084486D43150E",
    "TrustedStoreSigning": false
  },
  {
    "SHA": "857444B499AAABF7DF388DEA89CC2DA0258273B7C1B091866FA1267E8AA3495D",
    "TrustedStoreSigning": true
  },
  {
    "SHA": "C11E39F29C946A6408E5C5EA65D94FCB05C0DB302B43E6A8ABCB01256257442A",
    "TrustedStoreSigning": true
  }
]
```

**Fields:**
- `SHA`: The SHA-1 or SHA-256 fingerprint of the signing certificate (required)


# Update Certificate Pinning
To update certificate pinning, you need to bundle your certificates and mapping file into a ZIP archive and pass it to your build command.
## What to include
- **Certificate files** (one per host), in any of these formats:  
  - `.cer`  
  - `.crt`  
  - `.pem`  
  - `.der`  
  - `.zip`  
- **JSON mapping file** (e.g. `pinning.json`), with entries like:
  ```json
  {
    "api.example.com": "api_cert.pem",
    "auth.example.com": "auth_cert.crt"
  }
## How to run
Gather all certificate files and pinning.json into a single certs_bundle.zip.
Invoke your build with:

your-build-command --cert_pinning_zip=/path/to/certs_bundle.zip

## Appdome Test (Standard Launch Tests)

Runs Appdome's Standard Launch Tests on a previously built and signed app. Apps built via the Build-to-Test flow are not eligible — only regular fuse/build (then sign) apps can run Appdome Test.

In the full `appdome_api.py` flow, after sign and artifact download:

```
python3 appdome_api_python/appdome_api.py ... --appdome_test
python3 appdome_api_python/appdome_api.py ... --appdome_test wait
python3 appdome_api_python/appdome_api.py ... --appdome_test atr <appdome_test_results_json>
```

`--appdome_test` with no extra args starts the test and prints the task ID. `wait` polls until complete. `atr appdome_test_results_json` downloads Appdome Test Results JSON (implies wait). Cannot be combined with `--build_to_test_vendor`.

Standalone `appdome_test.py` uses `--task_id` as a signed fuse/build ID or an Appdome Test task ID. `--wait` polls until complete when starting a new test or when `--task_id` is already running.

If `--task_id` is already running:
```
python3 appdome_api_python/appdome_test.py --task_id <task id>
python3 appdome_api_python/appdome_test.py --task_id <task id> --wait
python3 appdome_api_python/appdome_test.py --task_id <task id> --appdome_test_results <appdome_test_results_json>
```

If `--task_id` is a completed Appdome Test, download results:
```
python3 appdome_api_python/appdome_test.py --task_id <appdome test task id> --appdome_test_results <appdome_test_results_json>
```

If `--task_id` is a signed build (start a new test):
```
python3 appdome_api_python/appdome_test.py --task_id <build id value>
python3 appdome_api_python/appdome_test.py --task_id <build id value> --wait
python3 appdome_api_python/appdome_test.py --task_id <build id value> --appdome_test_results <appdome_test_results_json>
```
