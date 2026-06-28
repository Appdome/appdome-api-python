import hashlib
import logging

import requests

from utils import (JSON_CONTENT_TYPE, SERVER_API_V1_URL, build_url, debug_log_request,
                   request_headers, team_params, validate_response)


def sha256_checksum(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def check_app_by_checksum(api_key, team_id, checksum):
    url = build_url(SERVER_API_V1_URL, 'apps', 'check-by-checksum')
    params = team_params(team_id)
    headers = request_headers(api_key, JSON_CONTENT_TYPE)
    body = {'checksum': checksum}
    debug_log_request(url, headers=headers, params=params, data=body)
    return requests.post(url, headers=headers, params=params, json=body)


def get_existing_app_id(api_key, team_id, file_path, skip_upload_checksum_call=False):
    if skip_upload_checksum_call:
        logging.info("Skipping check-by-checksum API call before upload")
        return None
    checksum = sha256_checksum(file_path)
    logging.info(f"Checking for existing app with checksum [{checksum}]")
    response = check_app_by_checksum(api_key, team_id, checksum)
    if response.status_code == 404:
        logging.debug("Check-by-checksum API not available, proceeding with standard upload")
        return None
    validate_response(response)
    logging.debug(f"Check-by-checksum response: {response.text}")
    result = response.json()
    if result.get('exists') and result.get('app_id'):
        return result['app_id']
    return None
