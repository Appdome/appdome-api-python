import argparse
import logging

from utils import (validate_response, add_common_args, init_common_args, validate_output_path, task_output_command)
from status import _get_obfuscation_map_status


def download(api_key, team_id, task_id, action=None):
    return task_output_command(api_key, team_id, task_id, 'output', action)


def download_action(api_key, team_id, task_id, command_output_path, action):
    if not command_output_path:
        return
    validate_output_path(command_output_path)
    r = download(api_key, team_id, task_id, action)
    if action == 'deobfuscation_script' and r.status_code == 404:
        logging.debug(f"couldn't find deobfuscation scripts.")
        return
    validate_response(r)
    with open(command_output_path, 'wb') as f:
        f.write(r.content)
    logging.info(f"Downloaded {action + ' ' if action else ''}output file to {command_output_path}")


def parse_arguments():
    parser = argparse.ArgumentParser(description='Download final output from Appdome')
    add_common_args(parser, add_task_id=True)
    parser.add_argument('-o', '--output', required=True, metavar='output_app_file', help='Output file for fused and signed app after Appdome')
    parser.add_argument('--deobfuscation_script_output', metavar='deobfuscation_scripts_zip_file', help='Output file deobfuscation scripts when building with "Obfuscate App Logic"')
    parser.add_argument('--sign_second_output', metavar='second_output_app_file', help='Output file for secondary output file - universal apk when building an aab app')
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    download_action(args.api_key, args.team_id, args.task_id, args.output, None)
    if _get_obfuscation_map_status(args.api_key, args.team_id, args.task_id):
        download_action(args.api_key, args.team_id, args.task_id, args.deobfuscation_script_output, 'deobfuscation_script')
    download_action(args.api_key, args.team_id, args.task_id, args.sign_second_output, 'sign_second_output')


if __name__ == '__main__':
    main()
