import argparse
import json
import logging

import requests

from teams_utils import (team_action_url, UPDATE_USER_ENTITLEMENTS_ACTION, teams_headers, add_team_id_arg,
                         load_users_to_add)
from utils import (validate_response, add_common_args, init_common_args, log_and_exit,
                   debug_log_request)


def update_user_entitlements(api_key, team_id, users_to_add):
    url = team_action_url(team_id, UPDATE_USER_ENTITLEMENTS_ACTION)
    headers = teams_headers(api_key)
    body = {'users_to_add': users_to_add}
    debug_log_request(url, headers=headers, data=body, request_type='put')
    return requests.put(url, headers=headers, json=body)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Add or update users in a company team on Appdome')
    add_common_args(parser, add_team_id=False)
    add_team_id_arg(parser)
    parser.add_argument('-u', '--users_json', required=True, metavar='users_json_file',
                        help='Path to JSON file with users_to_add array (max 50 users)')
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    try:
        users_to_add = load_users_to_add(args.users_json)
    except (ValueError, json.JSONDecodeError, OSError) as e:
        log_and_exit(f"Failed to load users_to_add from {args.users_json}: {e}")
    r = update_user_entitlements(args.api_key, args.team_id, users_to_add)
    validate_response(r)
    logging.info(f"Update user entitlements success: {json.dumps(r.json(), indent=2)}")


if __name__ == '__main__':
    main()
