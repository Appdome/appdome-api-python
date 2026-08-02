import argparse
import logging
from os.path import basename

import requests

from check_by_checksum import get_existing_app_id
from utils import (build_url, team_params, SERVER_API_V1_URL, request_headers, validate_response,
                   debug_log_request, add_common_args, add_upload_args, init_common_args)


def direct_upload(api_key, team_id, file_path, skip_upload_checksum_call=False):
    existing_app_id = get_existing_app_id(api_key, team_id, file_path, skip_upload_checksum_call)
    if existing_app_id:
        logging.info(f"Found existing app by checksum. App ID: {existing_app_id}")
        return existing_app_id

    url = build_url(SERVER_API_V1_URL, 'upload')
    params = team_params(team_id)
    headers = request_headers(api_key)
    with open(file_path, 'rb') as f:
        files = {'file': (basename(file_path), f)}
        debug_log_request(url, headers=headers, params=params, files=files)
        response = requests.post(url, headers=headers, params=params, files=files)
    validate_response(response)
    return response.json()['id']


def parse_arguments():
    parser = argparse.ArgumentParser(description='Upload app directly to Appdome')
    add_common_args(parser)
    add_upload_args(parser)
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    app_id = direct_upload(args.api_key, args.team_id, args.app, args.skip_upload_checksum_call)
    logging.info(f"Direct upload success: App ID: {app_id}")


if __name__ == '__main__':
    main()
