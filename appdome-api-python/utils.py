import json
import logging
import shutil
import tempfile
import zipfile
from contextlib import contextmanager
from os import getenv, makedirs, listdir
from os.path import isdir, dirname, exists, splitext, join
from shutil import rmtree
from urllib.parse import urljoin
import requests

SERVER_BASE_URL = getenv('APPDOME_SERVER_BASE_URL', 'https://fusion.appdome.com/')
SERVER_API_V1_URL = urljoin(SERVER_BASE_URL, 'api/v1')
API_KEY_ENV = 'APPDOME_API_KEY'
TEAM_ID_ENV = 'APPDOME_TEAM_ID'
OVERRIDES_KEY = 'overrides'
ACTION_KEY = 'action'
TASK_ID_KEY = 'task_id'
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
        if tempDir and exists(tempDir):
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


def add_trusted_signing_fingerprint_list(trusted_signing_fingerprint_list_file, overrides):
    """
    Reads a JSON file containing trusted signing fingerprint list and adds it to overrides.

    :param trusted_signing_fingerprint_list_file: Path to JSON file with fingerprint list
    :param overrides: Dictionary to add the fingerprint list to
    """
    if trusted_signing_fingerprint_list_file:
        if not exists(trusted_signing_fingerprint_list_file):
            log_and_exit(f"Trusted signing fingerprint list file not found: {trusted_signing_fingerprint_list_file}")
        with open(trusted_signing_fingerprint_list_file, 'r') as f:
            fingerprint_list = json.load(f)
        # Ensure each fingerprint entry has TrustedStoreSigning field
        for fingerprint in fingerprint_list:
            if 'TrustedStoreSigning' not in fingerprint:
                fingerprint['TrustedStoreSigning'] = False
        overrides['trusted_signing_fingerprint_list'] = fingerprint_list


def validate_trusted_fingerprint_list_args(args):
    """
    Validates that trusted_signing_fingerprint_list is not used with Google Play signing parameters.
    """
    if hasattr(args, 'signing_fingerprint_list') and args.signing_fingerprint_list:
        conflicting_params = []
        if hasattr(args, 'signing_fingerprint') and args.signing_fingerprint:
            conflicting_params.append('--signing_fingerprint')
        if hasattr(args, 'signing_fingerprint_upgrade') and args.signing_fingerprint_upgrade:
            conflicting_params.append('--signing_fingerprint_upgrade')
        if hasattr(args, 'google_play_signing') and args.google_play_signing:
            conflicting_params.append('--google_play_signing')
        if conflicting_params:
            log_and_exit(f"--signing_fingerprint_list cannot be used with: {', '.join(conflicting_params)}")


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

def init_baseline_file(baseline_profile, files):
    if baseline_profile:
        files.append(("baseline_profile", (baseline_profile, open(baseline_profile, "rb"), "application/zip")))


def init_certs_pinning(cert_pinning_zip):
    """
    Extracts certificates and JSON mapping from the given zip file.

    :param cert_pinning_zip: Path to the zip file containing certs and JSON mapping.
    :return: List of files in the required format.
    """
    if not cert_pinning_zip:
        return []  # Return an empty list if no zip file is provided
    if not cert_pinning_zip.endswith('.zip') or not exists(cert_pinning_zip):
        logging.warning("No zip file provided or file does not exist.")
        return []  # Return an empty list if the file is not a valid zip or does not exist
    files = []
    with zipfile.ZipFile(cert_pinning_zip, 'r') as zip_ref:
        extract_path = splitext(cert_pinning_zip)[0] + "_unzipped"  # Extract to a folder with the same name as the zip
        zip_ref.extractall(extract_path)

        # Locate the JSON file and parse it
        json_file = next((f for f in listdir(extract_path) if f.endswith('.json')), None)
        if not json_file:
            logging.error("No JSON file found in the extracted zip contents.")
            return []  # Return an empty list if no JSON file is found

        with open(join(extract_path, json_file), 'r') as jf:
            cert_mapping = json.load(jf)

        # Add cert and pem files to the files list in the required format
        for index, file_name in cert_mapping.items():
            file_path = join(extract_path, file_name)
            if exists(file_path):
                files.append((
                    f"mitm_host_server_pinned_certs_list['{index}'].value.mitm_host_server_pinned_certs_file_content",
                    (file_name, open(file_path, 'rb'), 'application/octet-stream')
                ))
    shutil.rmtree(extract_path)
    return files

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


def add_signing_credentials_args(parser, required=False, add_platform_extra_signing_params=True):
    parser.add_argument('-k', '--keystore', metavar='keystore_file',
                        help='Path to keystore file to use on Appdome iOS and Android signing.', required=required)
    parser.add_argument('-kp', '--keystore_pass', metavar='keystore_password',
                        help='Password for keystore to use on Appdome iOS and Android signing.', required=required)
    parser.add_argument('-kyp', '--key_pass', metavar='key_password', help='Password for the key to use on Appdome Android signing.',)
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument('-ka', '--keystore_alias', metavar='key_alias', help='Key alias to use on Appdome Android signing.')
    add_provisioning_profiles_arg(group)
    add_common_private_signing_args(parser, add_platform_extra_signing_params=add_platform_extra_signing_params)
    if add_platform_extra_signing_params:
        add_signing_fingerprint_arg(parser)


def add_private_signing_args(parser, add_entitlements=False):
    group = parser.add_mutually_exclusive_group(required=True)
    add_provisioning_profiles_arg(group)
    add_signing_fingerprint_arg(group)
    add_trusted_signing_fingerprint_list_arg(group)
    add_common_private_signing_args(parser, add_entitlements=add_entitlements, add_trusted_fingerprint_list=False)


def add_common_private_signing_args(parser, add_platform_extra_signing_params=True, add_entitlements=True, add_trusted_fingerprint_list=True):
    if add_platform_extra_signing_params:
        parser.add_argument('-cfu', '--signing_fingerprint_upgrade', metavar='signing_fingerprint_upgrade', help='SHA-1 or SHA-256 Google Play upgrade App Signing certificate fingerprint.')
        parser.add_argument('-gp', '--google_play_signing', action='store_true', help='This Android application will be distributed via the Google Play App Signing program.')
        parser.add_argument('-sv', '--sign_overrides', metavar='overrides_json_file', help='Path to json file with sign overrides')
        if add_trusted_fingerprint_list:
            add_trusted_signing_fingerprint_list_arg(parser)
    if add_entitlements:
        parser.add_argument('-entt', '--entitlements', nargs='+', metavar='entitlements_plist_path', help='Path to iOS entitlements plist to use. Can be multiple entitlements files')


def add_provisioning_profiles_arg(target):
    target.add_argument('-pr', '--provisioning_profiles', nargs='+', metavar='provisioning_profile_file', help='Path to iOS provisioning profiles files to use. Can be multiple profiles')


def add_signing_fingerprint_arg(target):
    target.add_argument('-cf', '--signing_fingerprint', metavar='signing_fingerprint', help='SHA-1 or SHA-256 final Android signing certificate fingerprint.')


def add_trusted_signing_fingerprint_list_arg(parser):
    parser.add_argument('-sfp', '--signing_fingerprint_list', metavar='signing_fingerprint_list_json_file',
                        help='Path to JSON file containing trusted signing fingerprint list. Cannot be used with --signing_fingerprint, --signing_fingerprint_upgrade, or --google_play_signing.')


def android_keystore(args):
    return args.keystore or getenv('ANDROID_KEYSTORE')

def android_keystore_pass(args):
    return args.keystore_pass or getenv('ANDROID_KEYSTORE_PASS')

def android_keystore_alias(args):
    return args.keystore_alias or getenv('ANDROID_KEYSTORE_ALIAS')

def android_key_pass(args):
    return args.key_pass or getenv('ANDROID_KEY_PASS')

def ios_p12(args):
    return args.keystore or getenv('IOS_P12')

def ios_p12_password(args):
    return args.keystore_pass or getenv('IOS_P12_PASSWORD')

def ios_provisioning_profiles(args):
    return args.provisioning_profiles or provisioning_profiles_from_env()

def provisioning_profiles_from_env():
    profiles = []
    idx = 1
    while True:
        val = getenv(f'IOS_MOBILEPROVISION_{idx}')
        if not val:
            break
        profiles.append(val)
        idx += 1
    if not profiles and getenv('IOS_MOBILEPROVISION'):
        profiles.append(getenv('IOS_MOBILEPROVISION'))
    return profiles
