# Detailed Usage Examples

**Note:** This document assumes that you have defined the following environment variables:

```
APPDOME_API_KEY
APPDOME_TEAM_ID
APPDOME_IOS_FS_ID
APPDOME_ANDROID_FS_ID
```

To define them, you can use the following command:

```
export APPDOME_API_KEY=<api key value>
export APPDOME_TEAM_ID=<team id value>
export APPDOME_IOS_FS_ID=<ios fusion set id value>
export APPDOME_ANDROID_FS_ID=<android fusion set id value>
```

## Android whole process

```
python3 appdome_api.py --app <apk/aab file>
--sign_on_appdome
--keystore <keystore file>
--keystore_pass <keystore password>
--keystore_alias <key alias>
--key_pass <key password>
--output <output apk/aab>
--certificate_output <output certificate pdf>
--deobfuscation_script_output <file path for downloading deobfuscation zip file>
--firebase_app_id <app-id for uploading mapping file for crashlytics (requires --deobfuscation_script_output and firebase CLI tools)>
--datadog_api_key <datadog api key for uploading mapping file to datadog (requires --deobfuscation_script_output)>
```

## iOS whole process

```
python3 appdome_api.py --app <ipa file>
--sign_on_appdome --keystore <p12 file>
--keystore_pass <p12 password>
--provisioning_profiles <provisioning profile file> <another provisioning profile file if needed>
--entitlements <entitlements file> <another entitlements file if needed> --output <output ipa>
--certificate_output <output certificate pdf>
```

Private Signing and Auto-Dev Private Signing can also be invoked in the whole process commands
using the params `--private_signing` or `--auto_dev_private_signing` instead of `--sign_on_appdome`
and adjusting the required signing parameters.

## PWA whole process

Use `--pwa` with a PWA config file instead of `--app`. The platform comes from `pwa_platform` in the config file
(`aab` or `ipa`), so use the matching Android or iOS signing parameters.
- Short Flow accounts: the PWA upload also builds the app with the default Playground Fusion Set, and
  `--fusion_set_id` is ignored.
- Other accounts: the upload only creates the app, which is then built with `--fusion_set_id` (or the
  `APPDOME_ANDROID_FS_ID` / `APPDOME_IOS_FS_ID` environment variable).
- iOS: `--provisioning_profiles` is required; the profiles are also sent with the PWA upload.

Context, signing and download then run as usual. `--diagnostic_logs` and `--build_overrides` are merged into the
config file's `overrides` and also used for the build. Options that only apply to uploading an app file
(`--direct_upload`, `--build_to_test_vendor`, baseline/startup profiles, certificate pinning) cannot be combined
with `--pwa`.
See [PWA Upload](#pwa-upload) for the config file format.

```
python3 appdome_api.py --pwa <pwa config json file>
--fusion_set_id <fusion set id (accounts without Short Flow)>
--sign_on_appdome
--keystore <keystore file>
--keystore_pass <keystore password>
--keystore_alias <key alias>
--key_pass <key password>
--output <output aab>
--certificate_output <output certificate pdf>
```

## Android SDK Protect whole process

Required inputs for this sample are the SDK file, protected SDK output path, and Certified Secure PDF output path.
For Android SDK Protect only, include `--deobfuscation_script_output` when you want the Obfuscate SDK Logic mapping
ZIP downloaded as part of the same run.

```
python3 appdome_api_sdk.py --app <aar file>
--output <output aar>
--certificate_output <output Certified Secure pdf>
--deobfuscation_script_output <file path for downloading deobfuscation zip file>
```

## iOS SDK Protect whole process

Required inputs for this sample are the SDK file, protected SDK output path, and Certified Secure PDF output path.
Deobfuscation mapping files are only available for Android SDK Protect.

```
python3 appdome_api_sdk.py --app <xcframework zip file>
--output <output zip>
--certificate_output <output Certified Secure pdf>
```

___
## The next section details individual actions
___

## Upload

```
python3 upload.py --app <apk/aab/ipa file>
```

## PWA Upload
Creates a Secure PWA app from a website address ([Build a PWA](https://apis.appdome.com/reference/post_pwappload)).
The response's app object (`"status": "active"`) means the upload is done and gives the App ID.
With the Short Flow license the upload also starts a build with the default Playground Fusion Set and returns its
Build ID, which can be used with `context.py`, `sign.py`, `status.py` and `download.py`. Without Short Flow, build the
App ID with `build.py` or `appdome_api.py --app_id ... --fusion_set_id ...`.
For iOS (`ipa`), pass the provisioning profiles; they are sent base64 encoded in `overrides.provisioning_profile`.

```
python3 pwa_upload.py --pwa_config <pwa config json file>
--provisioning_profiles <iOS provisioning profile files (ipa only)>
--wait
--output <output unsigned aab/ipa file>
```

`--wait` and `--output` apply to the Short Flow build; `--output` implies `--wait`. The PWA config file replaces inline parameters:

```json
{
  "pwa_address": "https://example.com",
  "pwa_platform": "aab",
  "pwa_app_name": "My App",
  "overrides": {}
}
```

- `pwa_address` and `pwa_platform` are required. Unknown keys are rejected.
- `pwa_platform` is the output package type, one platform per build: `aab` for Android or `ipa` for iOS.
- `overrides` is optional and sent to the API as a JSON object (e.g. `{"extended_logs": true}` for Diagnostic Logs).

## Status
All of the actions from this point are asynchronous. You can check the status of the action with the following command:
```
python3 status.py --task_id <task id value>
```

## Build
[Possible overrides](https://apis.appdome.com/reference/post_tasks-build)

```
python3 build.py --app_id <app id value>
--fusion_set_id <fusion set id value>
--build_overrides <overrides json file>
```

## Context
[Possible overrides](https://apis.appdome.com/reference/post_tasks-context)

```
python3 context.py --task_id <task id value>
--new_bundle_id <bundle id value>
--new_version <version value>
--new_build_number <build number value>
--new_display_name <display name value>
--app_icon <app icon file>
--icon_overlay <icon overlay file>
```

## On Appdome Signing

[Possible overrides](https://apis.appdome.com/reference/post_tasks-sign)

**Android**

```
python3 sign.py --task_id <task id value>
--keystore <keystore file>
--keystore_pass <keystore password>
--keystore_alias <key alias>
--key_pass <key password>
--sign_overrides <overrides json file>
```

**Android (with signing fingerprint list)**
```
python3 sign.py --task_id <task id value>
--keystore <keystore file>
--keystore_pass <keystore password>
--keystore_alias <key alias>
--key_pass <key password>
--signing_fingerprint_list <path_to_json_file>
--sign_overrides <overrides json file>
```

**iOS**

```
python3 sign.py --task_id <task id value>
--keystore <p12 file>
--keystore_pass <p12 password>
--sign_overrides <overrides json file>
--provisioning_profiles <provisioning profile file> <another provisioning profile file if needed>
--entitlements <entitlements file> <another entitlements file if needed>
```

## Private Signing

[Possible overrides](https://apis.appdome.com/reference/post_tasks-privatesign)

**Android**
```
python3 private_sign.py --task_id <task id value>
--signing_fingerprint <signing fingerprint>
--sign_overrides <overrides json file>
--google_play_signing
```

**Android (with signing fingerprint list)**
```
python3 private_sign.py --task_id <task id value>
--signing_fingerprint_list <path_to_json_file>
--sign_overrides <overrides json file>
```

**iOS**

```
python3 private_sign.py --task_id <task id value>
--sign_overrides <overrides json file>
--provisioning_profiles <provisioning profile file> <another provisioning profile file if needed>
```

## Auto-Dev Private Signing

[Possible overrides](https://apis.appdome.com/reference/post_tasks-autodev)

**Android**

```
python3 auto_dev_sign.py --task_id <task id value>
--signing_fingerprint <signing fingerprint>
--google_play_signing
```

**Android (with signing fingerprint list)**
```
python3 auto_dev_sign.py --task_id <task id value>
--signing_fingerprint_list <path_to_json_file>
```

**iOS**

```
python3 auto_dev_sign.py --task_id <task id value>
--sign_overrides <overrides json file>
--provisioning_profiles <provisioning profile file> <another provisioning profile file if needed>
--entitlements <entitlements file> <another entitlements file if needed>
```

## Download

```
python3 download.py --task_id <task id value>
--output <output file>
--deobfuscation_script_output <deobfuscation scripts zip file>
--sign_second_output <second output app file>
```

## Download Certified Secure pdf file

```
python3 certified_secure.py --task_id <task id value>
--certificate_output <output certificate pdf>
```

## Download Certified Secure json file
```
python3 certified_secure_json.py --task_id <task id value>
--certificate_json <certificate json output file>
```

## Validate App after local signing

```
python3 validate.py --validate_app <app file>
```
