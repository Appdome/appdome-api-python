import argparse
import logging
import requests

from utils import (SERVER_API_V1_URL, request_headers, validate_response, add_common_args, add_fusion_set_id_arg,
                   init_common_args, build_url, team_id_arg)


def release_fusion_set(api_key, fusion_set_id, team_id):
    headers = request_headers(api_key)
    url = build_url(SERVER_API_V1_URL, 'release_fs', fusion_set_id)
    params = { 'team_id': team_id }
   
    return requests.post(url, headers=headers, params=params)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Releases a Fusion Set from one team to another')
    add_common_args(parser, add_task_id=False, add_team_id=False)
    add_fusion_set_id_arg(parser, required=True, help='Fusion Set ID to release')
    parser.add_argument('-ti', '--team_id', metavar='team_id', required=True, type=team_id_arg, help='The team ID that will receive the released Fusion Set')
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    r = release_fusion_set(args.api_key, args.fusion_set_id, args.team_id)
    validate_response(r)
    logging.info(f"Fusion Set {args.fusion_set_id} was successfully released to team: {args.team_id}")
    logging.info(f"New Fusion Set ID: {r.json()['new_fusion_set_id']}")


if __name__ == '__main__':
    main()
