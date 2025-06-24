import argparse
import logging
from os.path import basename

import requests

from utils import (build_url, team_params, SERVER_API_V1_URL, request_headers, validate_response,
                   debug_log_request, add_common_args, init_common_args)


def direct_upload(api_key, team_id, file_path):
    url = build_url(SERVER_API_V1_URL, 'upload')
    params = team_params(team_id)
    headers = request_headers(api_key)
    with open(file_path, 'rb') as f:
        files = {'file': (basename(file_path), f)}
        debug_log_request(url, headers=headers, params=params, files=files)
        return requests.post(url, headers=headers, params=params, files=files)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Upload app to directly to Appdome')
    add_common_args(parser)
    parser.add_argument('-a', '--app_path', required=True, metavar='application_path', help="Upload app input path")
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    r = direct_upload(args.api_key, args.team_id, args.app_path)
    validate_response(r)
    logging.info(f"Direct upload success: App id: {r.json()['id']}")


if __name__ == '__main__':
    main()
