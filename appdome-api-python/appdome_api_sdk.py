import argparse
import logging
from enum import Enum
from os import getenv
from os.path import splitext
from appdome_api import _upload, _build, _download_file
from private_sign import private_sign_ios
from sign import sign_ios
from status import wait_for_status_complete
from certified_secure import download_certified_secure
from certified_secure_json import download_certified_secure_json, format_json_file
from download import download
from utils import (log_and_exit, add_common_args, init_common_args, validate_output_path,
                   validate_response)


class Platform(Enum):
    UNKNOWN = 0
    ANDROID = 1
    IOS = 2


def parse_arguments():
    parser = argparse.ArgumentParser(description='Runs Appdome API commands for SDK')
    upload_group = parser.add_mutually_exclusive_group(required=True)
    upload_group.add_argument('-a', '--app', metavar='application_file', help='Upload sdk file input path')
    upload_group.add_argument('--app_id', metavar='app_id_value', help='sdk id of previously uploaded sdk')

    add_common_args(parser)

    parser.add_argument('-fs', '--fusion_set_id', metavar='fusion_set_id_value',
                        help='Appdome Fusion Set id. '
                             'Default for Android is environment variable APPDOME_ANDROID_FS_ID. '
                             'Default for iOS is environment variable APPDOME_IOS_FS_ID')
    parser.add_argument('-bv', '--build_overrides', metavar='overrides_json_file',
                        help='Path to json file with build overrides')
    parser.add_argument('-bl', '--diagnostic_logs', action='store_true',
                        help="Build the SDK with Appdome's Diagnostic Logs (if licensed)")

    # Signing credentials
    parser.add_argument('-k', '--keystore', metavar='keystore_file',
                        help='Path to keystore file to use on Appdome iOS XCFramework signing.')
    parser.add_argument('-kp', '--keystore_pass', metavar='keystore_password',
                        help='Password for keystore to use on Appdome iOS XCFramework signing.')

    # Output parameters
    parser.add_argument('-o', '--output', metavar='output_app_file',
                        help='Output file for fused SDK after Appdome')
    parser.add_argument('-co', '--certificate_output', metavar='certificate_output_file',
                        help='Output file for Certified Secure pdf')
    parser.add_argument('-cj', '--certificate_json', metavar='certificate_json_output_file',
                        help='Output file for Certified Secure json')
    parser.add_argument('-wol', '--workflow_output_logs', metavar='workflow_output_logs',
                        help='Enter path to a workflow output logs file (optional)')
    return parser.parse_args()


def validate_args(args):
    fusion_set_id = args.fusion_set_id
    platform = Platform.UNKNOWN
    init_common_args(args)
    if args.app:
        app_path_ext = splitext(args.app)[-1].lower()
        if not app_path_ext == ".aar":
            platform = Platform.IOS
        else:
            platform = Platform.ANDROID

    if not fusion_set_id:
        fusion_set_id = getenv('APPDOME_IOS_FS_ID' if platform == Platform.IOS else 'APPDOME_ANDROID_FS_ID')
        if not fusion_set_id:
            log_and_exit("fusion_set_id must be specified or set though the correct platform environment variable")

    validate_output_path(args.output)
    validate_output_path(args.certificate_output)
    validate_output_path(args.certificate_json)
    if platform == Platform.IOS:
        if (args.keystore is None) ^ (args.keystore_pass is None):  # XOR operator to check if only one is None
            log_and_exit("keystore and keystore_pass must be specified")
        elif args.keystore is None and args.keystore_pass is None:
            logging.info("Keystore and keystore_pass weren't supplied. Will continue with private sign.")
    return platform, fusion_set_id


def _sign(args, platform, task_id, workflow_output_logs=None):
    if platform == Platform.IOS:
        if args.keystore:
            r = sign_ios(args.api_key, args.team_id, task_id, args.keystore, args.keystore_pass,
                         provisioning_profiles_paths=[])
        else:
            r = private_sign_ios(args.api_key, args.team_id, task_id, provisioning_profiles_paths=[])
        validate_response(r)
        logging.info(f"Signing request started. Response: {r.json()}")
        wait_for_status_complete(args.api_key, args.team_id, task_id, operation="sign",
                                 workflow_output_logs_path=workflow_output_logs)
        logging.info(f"Signing request finished.")


def main():
    args = parse_arguments()
    platform, fusion_set_id = validate_args(args)
    app_id = _upload(args.api_key, args.team_id, args.app) if args.app else args.app_id
    task_id = _build(args.api_key, args.team_id, app_id, fusion_set_id, args.build_overrides, args.diagnostic_logs,
                     None, args.workflow_output_logs)
    _sign(args, platform, task_id, args.workflow_output_logs)
    if args.output:
        _download_file(args.api_key, args.team_id, task_id, args.output, download)
    if args.certificate_output:
        _download_file(args.api_key, args.team_id, task_id, args.certificate_output, download_certified_secure)
    if args.certificate_json:
        _download_file(args.api_key, args.team_id, task_id, args.certificate_json, download_certified_secure_json)
        format_json_file(args.certificate_json)


if __name__ == '__main__':
    main()
