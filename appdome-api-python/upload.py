import argparse
import logging
from os.path import basename

import requests

from check_by_checksum import get_existing_app_id
from utils import (SERVER_API_V1_URL, UPLOAD_URL, request_headers, empty_files, validate_response, debug_log_request,
                   add_common_args, add_upload_args, log_and_exit, init_common_args, build_url, team_params)
from status import wait_for_status_complete


def get_upload_link(api_key, team_id):
    url = build_url(SERVER_API_V1_URL, 'upload-link')
    params = team_params(team_id)
    headers = request_headers(api_key)
    debug_log_request(url, headers, params=params, request_type='get')
    return requests.get(url, headers=headers, params=params)


def put_file_in_aws(file_path, aws_url):
    with open(file_path, 'rb') as f:
        debug_log_request(aws_url, request_type='put')
        return requests.put(aws_url, data=f)


def upload_using_link(api_key, team_id, file_id, file_name):
    url = build_url(SERVER_API_V1_URL, 'upload-using-link')
    params = team_params(team_id)
    params["async"] = True
    headers = request_headers(api_key)
    body = {'file_app_id': file_id, 'file_name': file_name}
    debug_log_request(url, params=params, data=body)
    return requests.post(url, headers=headers, params=params, data=body, files=empty_files())


def upload(api_key, team_id, file_path, skip_upload_checksum_call=False):
    logging.info(f"Preparing to upload [{file_path}]")
    existing_app_id = get_existing_app_id(api_key, team_id, file_path, skip_upload_checksum_call)
    if existing_app_id:
        logging.info(f"Found existing app by checksum. App ID: {existing_app_id}")
        return existing_app_id

    upload_link_response = get_upload_link(api_key, team_id)
    validate_response(upload_link_response)
    upload_link_json = upload_link_response.json()
    aws_url = upload_link_json.get('url')
    file_id = upload_link_json.get('file_id')
    if not aws_url or not file_id:
        log_and_exit('Error in upload link response: ' + upload_link_response.text)

    logging.info(f"Uploading file ID {file_id}")
    aws_put_response = put_file_in_aws(file_path, aws_url)
    logging.info(f"Upload status: uploading to our cloud")
    validate_response(aws_put_response)
    app = upload_using_link(api_key, team_id, file_id, basename(file_path))
    logging.info(f"Upload status: analyzing and saving file info on our servers")
    validate_response(app)
    app_id = app.json()['id']
    wait_for_status_complete(api_key, team_id, app_id, url=UPLOAD_URL, operation="upload")
    return app_id


def parse_arguments():
    parser = argparse.ArgumentParser(description='Upload app to Appdome')
    add_common_args(parser)
    add_upload_args(parser)
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    app_id = upload(args.api_key, args.team_id, args.app, args.skip_upload_checksum_call)
    logging.info(f"Upload success: App ID: {app_id}")


if __name__ == '__main__':
    main()
