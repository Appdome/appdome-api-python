import argparse
import json
import logging

import requests

from teams_utils import (team_action_url, REMOVE_USER_FROM_TEAM_ACTION, teams_headers, add_team_id_arg)
from utils import validate_response, add_common_args, init_common_args, uuid_arg, debug_log_request


def remove_user_from_team(api_key, team_id, user_id):
    url = team_action_url(team_id, REMOVE_USER_FROM_TEAM_ACTION)
    headers = teams_headers(api_key)
    body = {'userId': user_id}
    debug_log_request(url, headers=headers, data=body, request_type='put')
    return requests.put(url, headers=headers, json=body)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Remove a user from a company team on Appdome')
    add_common_args(parser, add_team_id=False)
    add_team_id_arg(parser)
    parser.add_argument('-uid', '--user_id', required=True, metavar='user_id', type=uuid_arg,
                        help='ID of the user to remove from the team')
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    r = remove_user_from_team(args.api_key, args.team_id, args.user_id)
    validate_response(r)
    logging.info(f"Remove user from team success: {json.dumps(r.json(), indent=2)}")


if __name__ == '__main__':
    main()
