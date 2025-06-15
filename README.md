# Appdome Python Client Library
Python client library for interacting with https://fusion.appdome.com/ tasks API.

Each API endpoint has its own file and `main` function for a single API call.

`appdome_api.py` contains the whole flow of a task from upload to download.

All APIs are documented in https://apis.appdome.com/docs.

**Note:** The examples below are using the `requests` library. You can install it with `pip3 install requests`.

---
**For detailed information about each step and more advanced use, please refer to the [detailed usage examples](./appdome-api-python/README.md)**

---

## Basic Flow Usage

**Note:**
To update certificate pinning, you need to provide a ZIP file containing the SSL certificates and a JSON mapping file.
This ZIP file should be specified using the `--cert_pinning_zip` option in your command.

Gather all of your SSL certificates and the mapping JSON file into a single ZIP archive.
Inside the ZIP, include:
One certificate file per host (e.g. api_cert.pem, auth_cert.pem, etc.)
A JSON file (e.g. pinning.json) that maps each hostname to its certificate filename, for example:
```json
{
  "api.example.com": "api_cert.pem",
  "auth.example.com": "auth_cert.pem"
}
```
Send us the ZIP archive. We’ll extract it and apply the certificate pinning for each host.
## Examples
#### Android Example:

```python
python3 appdome_api.py \
--api_key <api key> \
--fusion_set_id <fusion set id> \
--team_id <team id> \
--app <apk/aab file> \
--sign_on_appdome \
--keystore <keystore file> \
--keystore_pass <keystore password> \
--keystore_alias <key alias> \
--key_pass <key password> \
--output <output apk/aab> \
--build_to_test_vendor <bitbar,saucelabs,browserstack,lambdatest,perfecto,firebase,aws_device_farm> \
--certificate_output <output certificate pdf>
--deobfuscation_script_output <file path for downloading deobfuscation zip file>
--firebase_app_id <app-id for uploading mapping file for crashlytics (requires --deobfuscation_script_output and firebase CLI tools)>
--datadog_api_key <datadog api key for uploading mapping file to datadog (requires --deobfuscation_script_output)>
--baseline_profile <zip file for build with baseline profile>
```

#### Android SDK Example:

```python
python3 appdome_api_sdk.py \
--api_key <api key> \
--fusion_set_id <fusion set id> \
--team_id <team id> \
--app <aar file> \
--output <output aar> \
--certificate_output <output certificate pdf>
```

#### iOS Example:

```python
python3 appdome_api.py \
--api_key <api key> \
--fusion_set_id <fusion set id> \
--team_id <team id> \
--app <ipa file> \
--sign_on_appdome \
--keystore <p12 file> \
--keystore_pass <p12 password> \
--provisioning_profiles <provisioning profile file> <another provisioning profile file if needed> \
--entitlements <entitlements file> <another entitlements file if needed> \
--output <output ipa> \
--certificate_output <output certificate pdf>
```

#### iOS SDK Example:

```python
python3 appdome_api_sdk.py \
--api_key <api key> \
--fusion_set_id <fusion set id> \
--team_id <team id> \
--app <zip file> \
--keystore <p12 file> \  # only needed for sign on Appdome
--keystore_pass <p12 password> \ # only needed for sign on Appdome
--output <output zip> \
--certificate_output <output certificate pdf>
```

### Integration Example With GitHub Actions:
[GitHub Actions Example](github_actions_appdome_workflow_example.yml)
