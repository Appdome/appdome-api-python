import argparse
import logging

import requests

from certified_secure_json import format_json_file
from status import WAIT_TIMEOUT_SEC, status, wait_for_status_complete
from utils import (ACTION_KEY, TASKS_URL, TASK_ID_KEY, add_common_args, debug_log_request, empty_files,
                   init_common_args, log_and_exit, request_headers, task_output_command, team_params,
                   validate_output_path, validate_response)


def start_appdome_test(api_key, team_id, parent_task_id):
    headers = request_headers(api_key)
    params = team_params(team_id)
    body = {ACTION_KEY: 'appdome_test', 'parent_task_id': parent_task_id}
    debug_log_request(TASKS_URL, headers=headers, params=params, data=body)
    return requests.post(TASKS_URL, headers=headers, params=params, data=body, files=empty_files())


def download_appdome_test_results(api_key, team_id, task_id, output_path, required=True):
    validate_output_path(output_path)
    response = task_output_command(api_key, team_id, task_id, 'appdome-test-result')
    if response.status_code not in (200, 204):
        if required:
            validate_response(response)
        return False
    with open(output_path, 'wb') as f:
        f.write(response.content)
    format_json_file(output_path)
    logging.info(f"Downloaded Appdome Test results to {output_path}")
    return True


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Run Appdome Test (Standard Launch Tests) on a previously built and signed app, '
                    'or download results for an existing Appdome Test task. '
                    'Apps built via the Build-to-Test flow are not eligible — '
                    'only regular fuse/build (then sign) apps can run Appdome Test.')
    add_common_args(parser, add_task_id=True)
    wait_group = parser.add_mutually_exclusive_group()
    wait_group.add_argument('--wait', dest='wait', action='store_true',
                            help='Poll until the Appdome Test completes. Applies when starting a new test or when --task_id is already running.')
    wait_group.add_argument('--no-wait', dest='wait', action='store_false',
                            help='Do not poll for completion (default). When starting a new test, print the Appdome Test task ID and exit.')
    parser.set_defaults(wait=False)
    parser.add_argument('-atr', '--appdome_test_results', metavar='appdome_test_results_json',
                        help='Download Appdome Test Results JSON. Running test: wait then download. '
                             'Completed test: download immediately. Signed build: start a new test, wait, then download.')
    parser.add_argument('--timeout', type=int, default=WAIT_TIMEOUT_SEC, metavar='seconds',
                        help=f'Timeout in seconds when waiting for the test to complete. Default is {WAIT_TIMEOUT_SEC}.')
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)

    status_response = status(args.api_key, args.team_id, args.task_id, TASKS_URL)
    validate_response(status_response)
    current_status = status_response.json().get('status', '')

    if current_status == 'error':
        status_json = status_response.json()
        message = status_json.get('message') or status_json or status_response.text
        log_and_exit(f"Task not completed successfully. Response: {message}")

    if current_status == 'progress':
        logging.info("Appdome Test is already running.")
        if args.wait or args.appdome_test_results:
            if args.appdome_test_results:
                logging.info("Waiting for it to finish before downloading results.")
            wait_for_status_complete(args.api_key, args.team_id, args.task_id, timeout_sec=args.timeout,
                                     operation='appdome_test')
            logging.info("Appdome Test completed")
            if args.appdome_test_results:
                download_appdome_test_results(args.api_key, args.team_id, args.task_id, args.appdome_test_results)
        return

    if current_status == 'completed' and args.appdome_test_results:
        if download_appdome_test_results(args.api_key, args.team_id, args.task_id, args.appdome_test_results,
                                         required=False):
            return

    response = start_appdome_test(args.api_key, args.team_id, args.task_id)
    validate_response(response)
    test_task_id = response.json()[TASK_ID_KEY]
    logging.info(f"Appdome Test started: Task ID: {test_task_id}")

    if args.wait or args.appdome_test_results:
        wait_for_status_complete(args.api_key, args.team_id, test_task_id, timeout_sec=args.timeout,
                                 operation='appdome_test')
        logging.info("Appdome Test completed")

    if args.appdome_test_results:
        download_appdome_test_results(args.api_key, args.team_id, test_task_id, args.appdome_test_results)


if __name__ == '__main__':
    main()
