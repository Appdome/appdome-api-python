import argparse
import json
import logging

import requests

from teams_utils import TEAMS_URL, teams_headers
from utils import validate_response, debug_log_request, add_common_args, init_common_args


def create_team(api_key, team_name, team_description="", team_leaders_to_add=None):
    url = TEAMS_URL
    headers = teams_headers(api_key)
    body = {
        "name": team_name,
        "description": team_description,
        "team_leaders_to_add": team_leaders_to_add or []
    }
    debug_log_request(url, headers=headers, data=body)
    return requests.post(url, headers=headers, json=body)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Create a new team on Appdome')
    add_common_args(parser, add_team_id=False)
    parser.add_argument('-n', '--team_name', required=True, metavar='team_name', help='Name of the team to create')
    parser.add_argument('-d', '--team_description', required=True, default='', metavar='team_description', help='Description of the team')
    parser.add_argument('-l', '--team_leaders', required=True, nargs='+', default=[], metavar='leader_id', help='User IDs to add as team leaders')
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    r = create_team(args.api_key, args.team_name, args.team_description, args.team_leaders)
    validate_response(r)
    logging.info(f"Create team success: {json.dumps(r.json(), indent=2)}")


if __name__ == '__main__':
    main()
