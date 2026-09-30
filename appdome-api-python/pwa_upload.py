import argparse
import base64
import json
import logging
from os.path import basename

import requests

from download import download_action
from status import wait_for_status_complete
from utils import (SERVER_API_V1_URL, JSON_CONTENT_TYPE, OVERRIDES_KEY, TASK_ID_KEY, build_url, request_headers,
                   team_params, validate_response, debug_log_request, log_and_exit, add_common_args, add_output_arg,
                   init_common_args, validate_output_path, add_provisioning_profiles_arg, provisioning_profiles_from_env)

# PWA flow is independent of the Android/iOS binary upload flow (upload.py / direct_upload.py).
# Reference: https://apis.appdome.com/reference/post_pwappload
# Behavior (confirmed by Appdome Engineering):
# - The response's app object ("status": "active") means the upload is done; app.id is the App ID.
# - Accounts with the Short Flow license also get an automatic build with the default Playground Fusion Set
#   (named after the app); the response then includes taskId.task_id. Without Short Flow the call only uploads,
#   and the App ID is built with the regular build API and a Fusion Set.
PWA_UPLOAD_URL = build_url(SERVER_API_V1_URL, 'pwappload')
PWA_CONFIG_KEYS = ('pwa_address', 'pwa_platform', 'pwa_app_name', OVERRIDES_KEY)
PWA_REQUIRED_CONFIG_KEYS = ('pwa_address', 'pwa_platform')
# One platform per build: 'aab' (Android) or 'ipa' (iOS, requires provisioning profiles in the overrides).
PWA_PLATFORM_VALUES = ('aab', 'ipa')
PWA_PROVISIONING_PROFILE_KEY = 'provisioning_profile'


def init_pwa_config(pwa_config_file):
    """
    Loads the PWA upload config json file.
    Example: {"pwa_address": "https://example.com", "pwa_platform": "aab", "pwa_app_name": "My App", "overrides": {}}
    """
    with open(pwa_config_file, 'rb') as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            log_and_exit(f"PWA config file {pwa_config_file} contains invalid JSON: {e}")
    if not isinstance(config, dict):
        log_and_exit(f"PWA config file {pwa_config_file} must contain a JSON object")
    unknown_keys = [key for key in config if key not in PWA_CONFIG_KEYS]
    if unknown_keys:
        log_and_exit(f"Unknown keys in PWA config file: {', '.join(unknown_keys)}. "
                     f"Allowed keys: {', '.join(PWA_CONFIG_KEYS)}")
    missing_keys = [key for key in PWA_REQUIRED_CONFIG_KEYS if not config.get(key)]
    if missing_keys:
        log_and_exit(f"Missing required keys in PWA config file: {', '.join(missing_keys)}")
    if str(config['pwa_platform']).lower() not in PWA_PLATFORM_VALUES:
        log_and_exit(f"pwa_platform [{config['pwa_platform']}] is not supported. "
                     f"Supported values: {', '.join(PWA_PLATFORM_VALUES)}")
    config['pwa_platform'] = str(config['pwa_platform']).lower()
    return config


def pwa_overrides(pwa_config):
    """
    Returns the config overrides as a dict.
    The API reference documents 'overrides' as a string, but the live API rejects a JSON string (400)
    and accepts a JSON object, so string overrides are parsed and sent as an object.
    """
    overrides = pwa_config.get(OVERRIDES_KEY) or {}
    if isinstance(overrides, str):
        try:
            overrides = json.loads(overrides)
        except json.JSONDecodeError as e:
            log_and_exit(f"PWA config 'overrides' is not valid JSON: {e}")
    if not isinstance(overrides, dict):
        log_and_exit(f"PWA config 'overrides' must be a JSON object")
    return overrides


def encode_provisioning_profile(profile_path):
    with open(profile_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode('ascii')
    return {'filename': basename(profile_path), 'content': content}


def add_pwa_provisioning_profiles(pwa_config, provisioning_profiles):
    """
    iOS (ipa) PWA uploads require the provisioning profile(s) in the overrides:
    {"provisioning_profile": [{"filename": "X.mobileprovision", "content": "<base64>"}]}
    Profiles given on the command line replace any already in the config. No-op for aab.
    """
    if pwa_config['pwa_platform'] != 'ipa':
        return pwa_config
    overrides = pwa_overrides(pwa_config)
    if provisioning_profiles:
        overrides[PWA_PROVISIONING_PROFILE_KEY] = [encode_provisioning_profile(p) for p in provisioning_profiles]
    if not overrides.get(PWA_PROVISIONING_PROFILE_KEY):
        log_and_exit("iOS PWA (pwa_platform ipa) requires provisioning profiles. "
                     "Use --provisioning_profiles or the IOS_MOBILEPROVISION_1..N environment variables")
    pwa_config[OVERRIDES_KEY] = overrides
    return pwa_config


def create_pwa_upload_request(api_key, team_id, pwa_config):
    url = PWA_UPLOAD_URL
    params = team_params(team_id)
    headers = request_headers(api_key, JSON_CONTENT_TYPE)
    body = {key: value for key, value in pwa_config.items() if value}
    if OVERRIDES_KEY in body:
        body[OVERRIDES_KEY] = pwa_overrides(body)
    return url, headers, body, params


def _redacted_body(body):
    """Keeps base64 provisioning profiles out of the debug log."""
    overrides = body.get(OVERRIDES_KEY)
    if not isinstance(overrides, dict) or PWA_PROVISIONING_PROFILE_KEY not in overrides:
        return body
    profiles = [dict(p, content=f"<base64, {len(p.get('content', ''))} chars>")
                for p in overrides[PWA_PROVISIONING_PROFILE_KEY]]
    return dict(body, overrides=dict(overrides, **{PWA_PROVISIONING_PROFILE_KEY: profiles}))


def pwa_upload(api_key, team_id, pwa_config):
    url, headers, body, params = create_pwa_upload_request(api_key, team_id, pwa_config)
    debug_log_request(url, headers=headers, params=params, data=_redacted_body(body))
    return requests.post(url, headers=headers, params=params, json=body)


def parse_pwa_upload_response(response):
    """
    Returns a list of {'app_id', 'task_id', 'pack_type', 'status'} dicts, one per uploaded platform.
    'task_id' is None when no automatic build was started (account without Short Flow).
    Short Flow:    [{"app": {"id": ..., "pack_type": "aab", "status": "active", ...}, "taskId": {"task_id": ...}}]
    Upload only:   [{"app": {"id": ..., "pack_type": "aab", "status": "active", ...}}]
    The published spec documents {"task_id": ...}, which is also accepted.
    """
    try:
        response_json = response.json()
    except ValueError:
        response_json = None
    items = response_json if isinstance(response_json, list) else [response_json]
    uploads = []
    for item in items:
        if not isinstance(item, dict):
            log_and_exit(f"Error in PWA upload response: {response.text}")
        app = item.get('app') or {}
        task_id = (item.get('taskId') or {}).get(TASK_ID_KEY) or item.get(TASK_ID_KEY)
        if not app.get('id') and not task_id:
            log_and_exit(f"Error in PWA upload response: {response.text}")
        uploads.append({'app_id': app.get('id'), TASK_ID_KEY: task_id, 'pack_type': app.get('pack_type'),
                        'status': app.get('status')})
    if not uploads:
        log_and_exit(f"Error in PWA upload response: {response.text}")
    return uploads


def pwa_build(api_key, team_id, pwa_config, wait=False, workflow_output_logs=None):
    """Uploads the PWA. When the account's Short Flow starts an automatic build, optionally waits for it."""
    logging.info(f"Preparing PWA upload for [{pwa_config.get('pwa_address')}] ({pwa_config.get('pwa_platform')})")
    response = pwa_upload(api_key, team_id, pwa_config)
    validate_response(response)
    uploads = parse_pwa_upload_response(response)
    for u in uploads:
        logging.info(f"PWA upload done. App ID: {u['app_id']}. Type: {u['pack_type']}. Status: {u['status']}")
        if u['status'] and u['status'] != 'active':
            logging.warning(f"PWA app status is [{u['status']}], expected [active]")
        if not u[TASK_ID_KEY]:
            logging.info("No automatic build started (Short Flow not enabled on this account). "
                         "Build the App ID with a Fusion Set using the regular build flow.")
            continue
        logging.info(f"Automatic build started (Short Flow, default Playground Fusion Set). "
                     f"Build ID: {u[TASK_ID_KEY]}")
        if wait:
            wait_for_status_complete(api_key, team_id, u[TASK_ID_KEY], operation="build",
                                     workflow_output_logs_path=workflow_output_logs)
            logging.info(f"PWA build {u[TASK_ID_KEY]} finished.")
    return uploads


def add_pwa_config_arg(parser):
    parser.add_argument('--pwa_config', required=True, metavar='pwa_config_json_file',
                        help='Path to json file with PWA upload parameters '
                             '(pwa_address, pwa_platform, pwa_app_name, overrides)')


def parse_arguments():
    parser = argparse.ArgumentParser(description='Upload a PWA app to Appdome from a website address')
    add_common_args(parser)
    add_pwa_config_arg(parser)
    add_provisioning_profiles_arg(parser)
    parser.add_argument('--wait', action='store_true',
                        help='Wait for the automatic (Short Flow) build to complete')
    add_output_arg(parser, help='Output file for the automatically built (unsigned) PWA app. Implies --wait')
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    validate_output_path(args.output)
    pwa_config = init_pwa_config(args.pwa_config)
    add_pwa_provisioning_profiles(pwa_config, args.provisioning_profiles or provisioning_profiles_from_env())
    uploads = pwa_build(args.api_key, args.team_id, pwa_config, wait=args.wait or bool(args.output))
    print(json.dumps(uploads))
    if args.output:
        if len(uploads) > 1:
            log_and_exit("--output supports a single platform build. Use download.py with each Build ID instead")
        if not uploads[0][TASK_ID_KEY]:
            log_and_exit(f"Nothing to download: no automatic build was started. Build App ID "
                         f"{uploads[0]['app_id']} with a Fusion Set (appdome_api.py --app_id ... --fusion_set_id ...)")
        download_action(args.api_key, args.team_id, uploads[0][TASK_ID_KEY], args.output, None)


if __name__ == '__main__':
    main()
