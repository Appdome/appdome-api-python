import argparse
import json
import logging

import requests

from teams_utils import (team_url, teams_headers, pagination_params, add_team_id_arg, add_pagination_args)
from utils import validate_response, add_common_args, init_common_args, debug_log_request


def get_team(api_key, team_id, page=None, limit=None):
    url = team_url(team_id)
    headers = teams_headers(api_key)
    params = pagination_params(page, limit)
    debug_log_request(url, headers=headers, params=params, request_type='get')
    return requests.get(url, headers=headers, params=params)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Retrieve a company team on Appdome')
    add_common_args(parser, add_team_id=False)
    add_team_id_arg(parser)
    add_pagination_args(parser)
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    r = get_team(args.api_key, args.team_id, args.page, args.limit)
    validate_response(r)
    logging.info(f"Get team success: {json.dumps(r.json(), indent=2)}")


if __name__ == '__main__':
    main()
