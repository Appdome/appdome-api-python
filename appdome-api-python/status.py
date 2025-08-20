import argparse
import logging
from datetime import datetime
from time import sleep

import requests

from utils import (TASKS_URL, request_headers, JSON_CONTENT_TYPE, validate_response,
                   log_and_exit, add_common_args, init_common_args, build_url, team_params)


def status(api_key, team_id, task_id, url, last_date=None, messages=None):
    url = build_url(url, task_id, 'status')
    params = team_params(team_id)
    headers = request_headers(api_key, JSON_CONTENT_TYPE)
    if messages:
        if last_date is not None and last_date != '':
            request_url = f"{url}?messages=true&lastDate={last_date}"
        else:
            request_url = f"{url}?messages=true"
    else:
        request_url = url
    return requests.get(request_url, headers=headers, params=params)


def wait_for_status_complete(api_key, team_id, task_id, url=TASKS_URL, interval_sec=10, timeout_sec=3600,
                             num_of_retries=3, operation=None, workflow_output_logs_path=None):
    accumulated_sleep = 0
    status_value = 'not initialized'
    file_handle = open(workflow_output_logs_path, 'a') if workflow_output_logs_path else None
    status_response_json = ''
    last_date = ''

    # Determine whether to use detailed logging based on the URL
    detailed_logging = operation != "upload" and file_handle is not None

    if file_handle:
        file_handle.write(operation + ":\n")

    while accumulated_sleep <= timeout_sec:
        status_response = None
        for i in range(num_of_retries):
            try:
                if detailed_logging:
                    last_date = last_date
                    messages = True
                else:
                    last_date = None
                    messages = False
                status_response = status(api_key, team_id, task_id, url, last_date, messages)

                # Validate HTTP status code is 200 or 204
                if status_response.status_code in [200, 204]:
                    break  # Exit retry loop on success
                else:
                    # Continue retrying if status code is not valid
                    sleep(interval_sec)
            except Exception as e:
                if i == num_of_retries - 1:
                    raise Exception(f'Wait for status Error. Error: {e}')
                sleep(interval_sec)

        validate_response(status_response)
        status_response_json = status_response.json()
        status_value = status_response_json.get('status', '')

        if status_value == 'progress':
            if detailed_logging:
                messages = status_response_json.get('messages', [])
                for message in messages:
                    message_text = message.get('message', {}).get('text', '')
                    message_type = message.get('message_type', '')

                    if message_text:
                        print(f" - {message_text}")
                        if message_text:
                            if file_handle:
                                file_handle.write(message_text + '\n')

                if messages:
                    last_date = messages[-1].get('creation_time')

            else:
                print('.', end='', flush=True)

            sleep(interval_sec)
            accumulated_sleep += interval_sec

        else:
            print('', flush=True)
            break

    if accumulated_sleep > timeout_sec:
        log_and_exit(f"\nTask did not complete in the specified timeout of: {timeout_sec} seconds")

    if status_value != 'completed':
        log_and_exit(f"Task not completed successfully. Response: {status_response_json.get('message')}")


def _get_obfuscation_map_status(api_key, team_id, task_id):
    try:
        status_response = status(api_key, team_id, task_id, TASKS_URL)
        status_response_json = status_response.json()
        return status_response_json.get('obfuscationMapExists', False)
    except Exception as e:
        print(f"Couldn't get status of obfuscation map. Error: {e}")


def parse_arguments():
    parser = argparse.ArgumentParser(description='Wait for status of task to be done')
    add_common_args(parser, add_task_id=True)
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    wait_for_status_complete(args.api_key, args.team_id, args.task_id)
    logging.info("Task complete")


if __name__ == '__main__':
    main()
