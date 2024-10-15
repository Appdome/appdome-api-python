import json
import logging
import os
import tempfile
from contextlib import contextmanager
from os import getenv, makedirs
from os.path import isdir, dirname, exists
from shutil import rmtree
from urllib.parse import urljoin
import requests

SERVER_BASE_URL = getenv('APPDOME_SERVER_BASE_URL', 'https://fusion.appdome.com/')
SERVER_API_V1_URL = urljoin(SERVER_BASE_URL, 'api/v1')
API_KEY_ENV = 'APPDOME_API_KEY'
TEAM_ID_ENV = 'APPDOME_TEAM_ID'
OVERRIDES_KEY = 'overrides'
ACTION_KEY = 'action'
ANDROID_SIGNING_FINGERPRINT_KEY = 'signing_sha1_fingerprint'
JSON_CONTENT_TYPE = 'application/json'
APPDOME_CLIENT_HEADER = getenv('APPDOME_CLIENT_HEADER', 'Appdome-cli-python/1.0')


@contextmanager
def erased_temp_dir():
    """
    Context manager to create and erase a temporary directory.

    :yield: Temporary directory path
    """
    tempDir = tempfile.mkdtemp()
    try:
        yield tempDir
    except Exception as e:
        raise e
    finally:
        if tempDir and os.path.exists(tempDir):
            rmtree(tempDir, ignore_errors=True)


def build_url(*args):
    url = "/".join(args)
    return url


TASKS_URL = build_url(SERVER_API_V1_URL, 'tasks')
UPLOAD_URL = build_url(SERVER_API_V1_URL, 'upload')
BUILD_TO_TEST_URL = build_url(SERVER_API_V1_URL, 'build-to-test')


def team_params(team_id):
    params = {}
    if team_id:
        params['team_id'] = team_id
    return params


def request_headers(api_key, content_type=None):
    headers = {
        'Authorization': api_key,
        'Cache-Control': 'no-cache',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'X-Appdome-Client': APPDOME_CLIENT_HEADER
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


def add_google_play_signing_fingerprint(google_play_signing_fingerprint, overrides,
                                        google_play_signing_fingerprint_upgrade=None):
    if google_play_signing_fingerprint:
        overrides['signing_keystore_use_google_signing'] = True
        overrides['signing_keystore_google_signing_sha1_key'] = google_play_signing_fingerprint
        if google_play_signing_fingerprint_upgrade:
            overrides['signing_keystore_google_signing_upgrade'] = True
            overrides['signing_keystore_google_signing_sha1_key_2nd_cert'] = google_play_signing_fingerprint_upgrade


def add_provisioning_profiles_entitlements(provisioning_profiles_paths, entitlements_paths, files_list, overrides,
                                           open_fd):
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
    else:
        overrides['manual_entitlements_matching'] = False


def init_overrides(overrides_file):
    overrides = {}
    if overrides_file:
        with open(overrides_file, 'rb') as f:
            overrides = json.load(f)
    return overrides


def run_task_action(api_key, team_id, action, task_id, overrides, files):
    if not files:
        files = empty_files()
    headers = request_headers(api_key)
    url = TASKS_URL
    params = team_params(team_id)
    body = {ACTION_KEY: action, 'parent_task_id': task_id, OVERRIDES_KEY: json.dumps(overrides)}
    debug_log_request(url, headers=headers, params=params, data=body, files=files)
    return requests.post(url, headers=headers, params=params, data=body, files=files)


def task_output_command(api_key, team_id, task_id, command, action=None):
    url = build_url(TASKS_URL, task_id, command)
    params = team_params(team_id)
    if action:
        params[ACTION_KEY] = action
    headers = request_headers(api_key, JSON_CONTENT_TYPE)
    debug_log_request(url, headers=headers, params=params, request_type='get')
    return requests.get(url, headers=headers, params=params)


def validate_response(response):
    accepted_response_codes = [200, 204]
    if response.status_code not in accepted_response_codes:
        headers_to_print = {}
        for key, value in response.request.headers.items():
            headers_to_print[key] = value_to_print(value)
        body_to_print = value_to_print(response.request.body)

        log_and_exit(
            f'Validation status for request {response.request.url} with headers {headers_to_print} and body {body_to_print} failed.'
            f' Status Code: {response.status_code}. Response: {response.text}')


def value_to_print(value):
    max_str_len = 500
    return value if len(str(value)) < max_str_len else str(value)[:max_str_len] + " ... '"


def log_and_exit(log_line):
    import sys
    sys.tracebacklimit = 0
    raise Exception(log_line)


def init_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format='[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d - %(funcName)s] %(message)s',
                        level=level)
    init_logging.func_code = (lambda: None).__code__


def debug_log_request(url, headers=None, data=None, params=None, files=None, request_type='post'):
    params_line = f" with params: {params}." if params else ""
    headers_line = f" with headers: {headers}." if headers else ""
    data_line = f" with data: {data}." if data else ""
    files_line = f" with file: {files}." if files else ""
    logging.debug(f"About to {request_type} {url}{params_line}{headers_line}{data_line}{files_line}")


def add_common_args(parser, add_task_id=False, add_team_id=True):
    parser.add_argument('-key', '--api_key', default=getenv(API_KEY_ENV), metavar=API_KEY_ENV,
                        help=f"Appdome API key. Default is environment variable '{API_KEY_ENV}'")
    if add_team_id:
        parser.add_argument('-t', '--team_id', default=getenv(TEAM_ID_ENV), metavar=TEAM_ID_ENV,
                            help=f"Appdome team id. Default is environment variable '{TEAM_ID_ENV}'")
    parser.add_argument('-v', '--verbose', action='store_true', help='Show debug logs')
    if add_task_id:
        parser.add_argument('--task_id', required=True, metavar='task_id_value', help='Build id on Appdome')


def init_common_args(args):
    if not args.api_key:
        log_and_exit(f"api_key must be specified or set though the '{API_KEY_ENV}' environment variable")
    init_logging(args.verbose)


def validate_output_path(path):
    if not path:
        return
    if isdir(path):
        log_and_exit(f"Output parameter [{path}] should be a path to a file, not a directory")
    path_dir = dirname(path)
    if path_dir and not exists(path_dir):
        logging.info(f"Creating non-existent output directory [{path_dir}]")
        makedirs(path_dir)
