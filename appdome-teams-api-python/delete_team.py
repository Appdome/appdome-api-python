import argparse
import json
import logging

import requests

from teams_utils import team_url, teams_headers, add_team_id_arg
from utils import validate_response, add_common_args, init_common_args, debug_log_request


def delete_team(api_key, team_id):
    url = team_url(team_id)
    headers = teams_headers(api_key)
    debug_log_request(url, headers=headers, request_type='delete')
    return requests.delete(url, headers=headers)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Delete a company team on Appdome')
    add_common_args(parser, add_team_id=False)
    add_team_id_arg(parser)
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    r = delete_team(args.api_key, args.team_id)
    validate_response(r)
    logging.info(f"Delete team success: {json.dumps(r.json(), indent=2)}")


if __name__ == '__main__':
    main()
