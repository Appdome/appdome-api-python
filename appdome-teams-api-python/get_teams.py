import argparse
import json
import logging

import requests

from teams_utils import TEAMS_URL, teams_headers, pagination_params, add_pagination_args
from utils import validate_response, add_common_args, init_common_args, debug_log_request


def get_teams(api_key, page=None, limit=None):
    headers = teams_headers(api_key)
    params = pagination_params(page, limit)
    debug_log_request(TEAMS_URL, headers=headers, params=params, request_type='get')
    return requests.get(TEAMS_URL, headers=headers, params=params)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Retrieve all company teams on Appdome')
    add_common_args(parser, add_team_id=False)
    add_pagination_args(parser)
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    r = get_teams(args.api_key, args.page, args.limit)
    validate_response(r)
    logging.info(f"Get teams success: {json.dumps(r.json(), indent=2)}")


if __name__ == '__main__':
    main()
