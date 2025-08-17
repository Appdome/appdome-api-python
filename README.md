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

### Integration Example With GitHub Actions:
[GitHub Actions Example](github_actions_appdome_workflow_example.yml)
