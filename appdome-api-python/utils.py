
import json
import logging
from contextlib import contextmanager
from os import getenv
from os.path import join

import requests

SERVER_BASE_URL = getenv('APPDOME_SERVER_BASE_URL', 'https://fusion.appdome.com')
SERVER_API_V1_URL = join(SERVER_BASE_URL, 'api/v1')

API_KEY_ENV = 'APPDOME_API_KEY'
TASKS_URL = join(SERVER_API_V1_URL, 'tasks')
OVERRIDES_KEY = 'overrides'
ACTION_KEY = 'action'
ANDROID_SIGNING_FINGERPRINT_KEY = 'signing_sha1_fingerprint'

JSON_CONTENT_TYPE = 'application/json'


def url_with_team(url, team_id):
    return url + f"?team_id={team_id}" if team_id else url


def request_headers(api_key, content_type=None):
    headers = {
        'Authorization': api_key,
        'Cache-Control': 'no-cache',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    if content_type:
        headers['Content-Type'] = content_type
    return headers


def empty_files():
    return {"None": ""}


@contextmanager
def cleaned_fd_list():
    fd_list = []
    try:
        yield fd_list
    finally:
        for f in fd_list:
            f.close()


def add_google_play_signing_fingerprint(google_play_signing_fingerprint, overrides):
    if google_play_signing_fingerprint:
        overrides['signing_keystore_use_google_signing'] = True
        overrides['signing_keystore_google_signing_sha1_key'] = google_play_signing_fingerprint


def add_provisioning_profiles_entitlements(provisioning_profiles_paths, entitlements_paths, files_list, overrides, open_fd):
    for prov_profile_path in provisioning_profiles_paths:
        f = open(prov_profile_path, 'rb')
        open_fd.append(f)
        files_list.append(('provisioning_profile', (prov_profile_path, f)))
    if entitlements_paths:
        overrides['manual_entitlements_matching'] = True
        for entitlements_path in entitlements_paths:
            f = open(entitlements_path, 'rb')
            open_fd.append(f)
            files_list.append(('entitlements_files', (entitlements_path, f)))


def run_task_action(api_key, team_id, action, task_id, overrides, files):
    if not files:
        files = empty_files()
    headers = request_headers(api_key)
    url = url_with_team(TASKS_URL, team_id)
    body = {ACTION_KEY: action, 'parent_task_id': task_id, OVERRIDES_KEY: json.dumps(overrides)}
    debug_log_request(url, headers=headers, data=body, files=files)
    return requests.post(url, headers=headers, data=body, files=files)


def validate_response(response):
    if response.status_code != 200:
        log_and_exit(f'Validation status for request {response.request.url} with headers {response.request.headers} and body {response.request.body} failed.'
                     f' Status Code: {response.status_code}. Response: {response.text}')


def log_and_exit(log_line):
    logging.error(log_line)
    exit(-1)


def init_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format='[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d - %(funcName)s] %(message)s', level=level)
    init_logging.func_code = (lambda: None).__code__


def debug_log_request(url, headers=None, data=None, files=None, request_type='post'):
    headers_line = f" with headers: {headers}." if headers else ""
    data_line = f" with data: {data}." if data else ""
    files_line = f" with file: {files}." if files else ""
    logging.debug(f"About to {request_type} {url}{headers_line}{data_line}{files_line}")


def add_common_args(parser, add_task_id=False, add_team_id=True):
    parser.add_argument('-key', '--api_key', default=getenv(API_KEY_ENV), help=f"Appdome API key. Default is environment variable '{API_KEY_ENV}'")
    if add_team_id:
        parser.add_argument('-t', '--team_id', default=getenv('APPDOME_TEAM_ID'), help="Appdome team id. Default is environment variable 'APPDOME_TEAM_ID'")
    parser.add_argument('-v', '--verbose', action='store_true', help="Show debug logs")
    if add_task_id:
        parser.add_argument('--task_id', required=True, help="Build id on Appdome")


def init_common_args(args):
    if not args.api_key:
        log_and_exit(f"api_key must be specified or set though the '{API_KEY_ENV}' environment variable")
    init_logging(args.verbose)
