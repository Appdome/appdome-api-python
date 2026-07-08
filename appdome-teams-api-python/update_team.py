import argparse
import json
import logging

import requests

from teams_utils import team_url, teams_headers, add_team_id_arg
from utils import validate_response, add_common_args, init_common_args, debug_log_request


def update_team(api_key, team_id, name=None, description=None):
    url = team_url(team_id)
    headers = teams_headers(api_key)
    body = {}
    if name is not None:
        body['name'] = name
    if description is not None:
        body['description'] = description
    debug_log_request(url, headers=headers, data=body, request_type='put')
    return requests.put(url, headers=headers, json=body)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Update a company team on Appdome')
    add_common_args(parser, add_team_id=False)
    add_team_id_arg(parser)
    parser.add_argument('-n', '--team_name', metavar='team_name', help='New name for the team')
    parser.add_argument('-d', '--team_description', metavar='team_description', help='New description for the team')
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    if args.team_name is None and args.team_description is None:
        logging.error('At least one of --team_name or --team_description must be provided')
        exit(1)
    r = update_team(args.api_key, args.team_id, args.team_name, args.team_description)
    validate_response(r)
    logging.info(f"Update team success: {json.dumps(r.json(), indent=2)}")


if __name__ == '__main__':
    main()
