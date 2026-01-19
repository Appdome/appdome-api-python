import argparse
import json
import logging

import requests

from utils import (request_headers, empty_files, validate_response, debug_log_request, TASKS_URL,
                   ACTION_KEY, OVERRIDES_KEY, add_common_args, init_common_args, init_overrides, team_params, TASK_ID_KEY)


def create_build_request(api_key, team_id, app_id, fusion_set_id, overrides=None, use_diagnostic_logs=False):
    headers = request_headers(api_key)
    url = TASKS_URL
    params = team_params(team_id)
    body = {ACTION_KEY: 'fuse', 'app_id': app_id, 'fusion_set_id': fusion_set_id}

    if use_diagnostic_logs:
        if overrides is None:
            overrides = {}
        overrides['extended_logs'] = True

    if overrides:
        body[OVERRIDES_KEY] = json.dumps(overrides)
    
    return url, headers, body, params


def build(api_key, team_id, app_id, fusion_set_id, overrides=None, use_diagnostic_logs=False, files=None):
    url, headers, body, params = create_build_request(api_key, team_id, app_id, fusion_set_id, overrides, use_diagnostic_logs)
    debug_log_request(url, headers=headers, params=params, data=body)
    return requests.post(url, headers=headers, params=params, data=body, files=files if files else empty_files())


def parse_arguments():
    parser = argparse.ArgumentParser(description='Initialize Build app on Appdome')
    add_common_args(parser)
    parser.add_argument('--app_id', required=True, metavar='app_id_value', help='App id on Appdome')
    parser.add_argument('-fs', '--fusion_set_id', required=True, metavar='fusion_set_id_value', help='Appdome Fusion Set id.')
    parser.add_argument('-bv', '--build_overrides', metavar='overrides_json_file', help='Path to json file with build overrides')
    parser.add_argument('-bl', '--diagnostic_logs', action='store_true', help="Build the app with Appdome's Diagnostic Logs (if licensed)")
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)

    overrides = init_overrides(args.build_overrides)

    r = build(args.api_key, args.team_id, args.app_id, args.fusion_set_id, overrides, args.diagnostic_logs)
    validate_response(r)
    logging.info(f"Build started: Build id: {r.json()[TASK_ID_KEY]}")


if __name__ == '__main__':
    main()
