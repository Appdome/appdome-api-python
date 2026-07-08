import json
import sys
from os.path import abspath, dirname, join

_pkg_dir = abspath(dirname(__file__))
_repo_root = abspath(join(_pkg_dir, '..', 'appdome-api-python'))
for _path in (_repo_root, _pkg_dir):
    if _path not in sys.path:
        sys.path.insert(1, _path)

from utils import (build_url, SERVER_API_V1_URL, JSON_CONTENT_TYPE, request_headers, uuid_arg)

TEAMS_URL = build_url(SERVER_API_V1_URL, 'myCompany', 'teams')
UPDATE_USER_ENTITLEMENTS_ACTION = 'updateUserEntitlements'
REMOVE_USER_FROM_TEAM_ACTION = 'removeUserFromTeam'


def team_url(team_id):
    return build_url(TEAMS_URL, team_id)


def team_action_url(team_id, action):
    return build_url(team_url(team_id), action)


def teams_headers(api_key):
    return request_headers(api_key, JSON_CONTENT_TYPE)


def pagination_params(page=None, limit=None):
    params = {}
    if page is not None:
        params['page'] = page
    if limit is not None:
        params['limit'] = limit
    return params


def add_team_id_arg(parser, required=True):
    parser.add_argument('-t', '--team_id', required=required, metavar='team_id', type=uuid_arg,
                        help='Company team ID')


def add_pagination_args(parser):
    parser.add_argument('--page', type=int, metavar='page', help='Page number (starts from 1)')
    parser.add_argument('--limit', type=int, metavar='limit', help='Results per page (default 20, max 100)')


def load_users_to_add(users_json):
    with open(users_json, 'r') as f:
        users = json.load(f)
    if not isinstance(users, list):
        raise ValueError('users_to_add must be a JSON array')
    if len(users) > 50:
        raise ValueError('users_to_add cannot contain more than 50 users')
    return users
