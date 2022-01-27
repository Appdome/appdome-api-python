import argparse
import logging
from time import sleep
from os.path import join

import requests

from utils import url_with_team, TASKS_URL, request_headers, JSON_CONTENT_TYPE, validate_response, log_and_exit, add_common_args, init_logging


def status(api_key, team_id, task_id):
    url = url_with_team(join(TASKS_URL, task_id, 'status'), team_id)
    headers = request_headers(api_key, JSON_CONTENT_TYPE)
    return requests.get(url, headers=headers)


def wait_for_status_complete(api_key, team_id, task_id, timeout_sec=3600):
    sleep_time = 10
    accumulated_sleep = 0
    status_value = 'not initialized'
    status_response_json = ''
    while accumulated_sleep <= timeout_sec:
        status_response = status(api_key, team_id, task_id)
        validate_response(status_response)
        status_response_json = status_response.json()
        status_value = status_response_json.get('status', '')
        if status_value == 'progress':
            logging.debug(f'Task not complete. Response: {status_response_json}. Sleeping for {sleep_time} seconds')
            print('.', end='', flush=True)
            sleep(sleep_time)
            accumulated_sleep += sleep_time
        else:
            print('', flush=True)
            break

    if accumulated_sleep > timeout_sec:
        log_and_exit(f"\nTask did not complete in the specified timeout of: {timeout_sec} seconds")

    if status_value != 'completed':
        log_and_exit(f"Task not completed successfully. Response: {status_response_json}")


def parse_arguments():
    parser = argparse.ArgumentParser(description='Wait for status of task to be done')
    add_common_args(parser, True)
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_logging(args.verbose)
    wait_for_status_complete(args.api_key, args.team_id, args.task_id)
    logging.info("Task complete")


if __name__ == '__main__':
    main()
