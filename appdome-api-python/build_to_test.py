import argparse
import json
import logging
from enum import Enum

import requests

from utils import (request_headers, empty_files, validate_response, debug_log_request, BUILD_TO_TEST_URL, log_and_exit,
                   ACTION_KEY, OVERRIDES_KEY, add_common_args, init_common_args, init_overrides, team_params, TASK_ID_KEY)


class BuildToTestVendors(Enum):
    AUTOMATION_BITBAR = 'bitbar'
    AUTOMATION_SAUCELABS = 'saucelabs'
    AUTOMATION_BROWSERSTACK = 'browserstack'
    AUTOMATION_LAMBDATEST = 'lambdatest'
    AUTOMATION_PERFECTO = 'perfecto'
    AUTOMATION_FIREBASE = 'firebase'
    AUTOMATION_KATALON = 'katalon'
    AUTOMATION_KOBITON = 'kobiton'
    AUTOMATION_TOSCA = 'tosca'
    AUTOMATION_AWS_DEVICE_FARM = 'aws_device_farm'



build_to_test_default_message = "App is not running on {}. Exiting"


def create_build_to_test_request(api_key, team_id, app_id, fusion_set_id, vendor,
                                 automation_vendor_err_msg=None, overrides=None, use_diagnostic_logs=False):
    automation_vendor_err_msg = automation_vendor_err_msg if automation_vendor_err_msg \
        else build_to_test_default_message.format(vendor)
    headers = request_headers(api_key)
    url = BUILD_TO_TEST_URL
    params = team_params(team_id)
    body = {ACTION_KEY: 'fuse', 'app_id': app_id, 'fusion_set_id': fusion_set_id}
    build_to_test_overrides = {"build_to_test_vendor": vendor, "build_to_test_message": automation_vendor_err_msg}

    if overrides:
        overrides.update(build_to_test_overrides)
    else:
        overrides = build_to_test_overrides

    if use_diagnostic_logs:
        overrides['extended_logs'] = True

    body[OVERRIDES_KEY] = json.dumps(overrides)

    return url, headers, body, params


def build_to_test(api_key, team_id, app_id, fusion_set_id, vendor,
                  automation_vendor_err_msg=None, overrides=None, use_diagnostic_logs=False, files=None):
    url, headers, body, params = create_build_to_test_request(api_key, team_id, app_id, fusion_set_id,
                                                              vendor, automation_vendor_err_msg, overrides,
                                                              use_diagnostic_logs)
    debug_log_request(url, headers=headers, params=params, data=body)
    return requests.post(url, headers=headers, params=params, data=body, files=files if files else empty_files())


def init_automation_vendor(automation_vendor):
    try:
        return BuildToTestVendors(automation_vendor.lower())
    except ValueError:
        log_and_exit(f'{automation_vendor} is not a valid testing vendor. Exiting')


def parse_arguments():
    parser = argparse.ArgumentParser(description='Initialize build_to_test app on Appdome')
    add_common_args(parser)
    parser.add_argument('--app_id', required=True, metavar='app_id_value', help='App id on Appdome')
    parser.add_argument('-fs', '--fusion_set_id', required=True, metavar='fusion_set_id_value', help='Appdome Fusion Set id.')
    parser.add_argument('-av', '--automation_vendor', required=True, metavar='automation_vendor', help='Automation vendor that the app will run on')
    parser.add_argument('-avem', '--automation_vendor_err_msg', metavar='automation_vendor_err_msg', help='The popup message when running the app on a different vendor')
    parser.add_argument('-bv', '--build_overrides', metavar='overrides_json_file', help='Path to json file with build overrides')
    parser.add_argument('-bl', '--diagnostic_logs', action='store_true', help="Build the app with Appdome's Diagnostic Logs (if licensed)")
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)

    overrides = init_overrides(args.build_overrides)
    automation_vendor = init_automation_vendor(args.automation_vendor)
    automation_vendor_err_msg = args.automation_vendor_err_msg if args.automation_vendor_err_msg else None

    r = build_to_test(args.api_key, args.team_id, args.app_id, args.fusion_set_id, automation_vendor.name,
                      automation_vendor_err_msg, overrides, args.diagnostic_logs)
    validate_response(r)
    logging.info(f"Build_to_test started: Build id: {r.json()[TASK_ID_KEY]}")


if __name__ == '__main__':
    main()
