import argparse
import logging
from enum import Enum
from os import getenv
from os.path import splitext
from build_to_test import BuildToTestVendors, build_to_test, init_automation_vendor
from auto_dev_sign import auto_dev_sign_android, auto_dev_sign_ios
from build import build
from certified_secure import download_certified_secure
from certified_secure_json import download_certified_secure_json, format_json_file
from context import context
from download import download, download_action
from private_sign import private_sign_android, private_sign_ios
from sign import sign_android, sign_ios
from status import wait_for_status_complete
from upload import upload
from utils import (validate_response, log_and_exit, add_common_args, init_common_args, validate_output_path,
                   init_overrides)
from status import _get_obfuscation_map_status
from crashlytics import Crashlytics
from datadog import DataDog

class Platform(Enum):
    UNKNOWN = 0
    ANDROID = 1
    IOS = 2


def parse_arguments():
    parser = argparse.ArgumentParser(description='Runs Appdome API commands')
    upload_group = parser.add_mutually_exclusive_group(required=True)
    upload_group.add_argument('-a', '--app', metavar='application_file', help='Upload app file input path')
    upload_group.add_argument('--app_id', metavar='app_id_value', help='App id of previously uploaded app')

    add_common_args(parser)

    parser.add_argument('-fs', '--fusion_set_id', metavar='fusion_set_id_value',
                        help='Appdome Fusion Set id. '
                             'Default for Android is environment variable APPDOME_ANDROID_FS_ID. '
                             'Default for iOS is environment variable APPDOME_IOS_FS_ID')
    parser.add_argument('-bv', '--build_overrides', metavar='overrides_json_file',
                        help='Path to json file with build overrides')
    parser.add_argument('-bl', '--diagnostic_logs', action='store_true',
                        help="Build the app with Appdome's Diagnostic Logs (if licensed)")
    parser.add_argument('-sv', '--sign_overrides', metavar='overrides_json_file',
                        help='Path to json file with sign overrides')
    parser.add_argument('-faid', '--firebase_app_id', metavar='firebase_app_id',
                        help='App ID in Firebase project (required for Crashlytics)')
    parser.add_argument('-dd_api_key', '--datadog_api_key', metavar='datadog_api_key',
                        help='Data Dog API_KEY (required for DataDog Deobfuscation)')


    sign_group = parser.add_mutually_exclusive_group(required=True)
    sign_group.add_argument('-s', '--sign_on_appdome', action='store_true', help='Sign on Appdome')
    sign_group.add_argument('-ps', '--private_signing', action='store_true', help='Sign application manually')
    sign_group.add_argument('-adps', '--auto_dev_private_signing', action='store_true',
                            help='Use a pre-generated signing script for automated local signing')

    # Signing credentials
    parser.add_argument('-k', '--keystore', metavar='keystore_file',
                        help='Path to keystore file to use on Appdome iOS and Android signing.')
    parser.add_argument('-kp', '--keystore_pass', metavar='keystore_password',
                        help='Password for keystore to use on Appdome iOS and Android signing..')
    parser.add_argument('-ka', '--keystore_alias', metavar='key_alias',
                        help='Key alias to use on Appdome Android signing.')
    parser.add_argument('-kyp', '--key_pass', metavar='key_password',
                        help='Password for the key to use on Appdome Android signing.')
    parser.add_argument('-cf', '--signing_fingerprint', metavar='signing_fingerprint',
                        help='SHA-1 or SHA-256 final Android signing certificate fingerprint.')
    parser.add_argument('-cfu', '--signing_fingerprint_upgrade', metavar='signing_fingerprint_upgrade',
                        help='SHA-1 or SHA-256 Upgraded signing certificate fingerprint for Google Play App Signing.')
    parser.add_argument('-gp', '--google_play_signing', action='store_true',
                        help='This Android application will be distributed via the Google Play App Signing program.')
    parser.add_argument('-pr', '--provisioning_profiles', nargs='+', metavar='provisioning_profile_file',
                        help='Path to iOS provisioning profiles files to use. Can be multiple profiles')
    parser.add_argument('-entt', '--entitlements', nargs='+', metavar='entitlements_plist_path',
                        help='Path to iOS entitlements plist to use. Can be multiple entitlements files')

    # Output parameters
    parser.add_argument('-o', '--output', metavar='output_app_file',
                        help='Output file for fused and signed app after Appdome')
    parser.add_argument('-dso', '--deobfuscation_script_output', metavar='deobfuscation_scripts_zip_file',
                        help='Output file deobfuscation scripts when building with "Obfuscate App Logic"')
    parser.add_argument('--sign_second_output', metavar='second_output_app_file',
                        help='Output file for secondary output file - universal apk when building an aab app')
    parser.add_argument('-co', '--certificate_output', metavar='certificate_output_file',
                        help='Output file for Certified Secure pdf')
    parser.add_argument('-cj', '--certificate_json', metavar='certificate_json_output_file',
                        help='Output file for Certified Secure json')
    parser.add_argument('-bt', '--build_to_test_vendor', metavar='build_to_test_vendor',
                        help='Enter vendor name on which Build to Test will happen')
    return parser.parse_args()


def validate_args(args):
    fusion_set_id = args.fusion_set_id
    platform = Platform.UNKNOWN
    init_common_args(args)
    if args.app:
        app_path_ext = splitext(args.app)[-1].lower()
        if app_path_ext == ".ipa":
            platform = Platform.IOS
        elif app_path_ext == ".apk" or app_path_ext == ".aab":
            platform = Platform.ANDROID
        else:
            log_and_exit(f"App extension [{app_path_ext}] must be .ipa, .apk or .aab")

    if platform == Platform.UNKNOWN:
        if args.provisioning_profiles and not args.signing_fingerprint and not args.keystore_alias:
            platform = Platform.IOS
        elif not args.provisioning_profiles and (args.signing_fingerprint or args.keystore_alias):
            platform = Platform.ANDROID
        else:
            log_and_exit(f"Please specify the correct platform signing credentials")

    if not fusion_set_id:
        fusion_set_id = getenv('APPDOME_IOS_FS_ID' if platform == Platform.IOS else 'APPDOME_ANDROID_FS_ID')
        if not fusion_set_id:
            log_and_exit(f"fusion_set_id must be specified or set though the correct platform environment variable")

    if args.private_signing or args.auto_dev_private_signing:
        if platform == Platform.ANDROID and not args.signing_fingerprint:
            log_and_exit(f"signing_fingerprint must be specified when using any Android local signing")

    if platform == Platform.IOS and not args.provisioning_profiles:
        log_and_exit(f"provisioning_profiles must be specified when using any iOS signing")

    if args.sign_on_appdome:
        if not args.keystore or not args.keystore_pass:
            log_and_exit(f"keystore and keystore_pass must be specified when using on Appdome signing")
        if platform == Platform.ANDROID and (not args.keystore_alias or not args.key_pass):
            log_and_exit(f"keystore_alias and key_pass must be specified when using on Appdome Android signing")
    if args.build_to_test_vendor and not any(
            args.build_to_test_vendor == vendor.value for vendor in BuildToTestVendors):
        log_and_exit(f"Vendor name provided for Build To Test isn't one of the acceptable vendors")
    
    if args.google_play_signing:
        if args.signing_fingerprint_upgrade and not args.signing_fingerprint:
            log_and_exit(f"Base Google signing fingerprint is required to upgrade the fingerprint")

    validate_output_path(args.output)
    validate_output_path(args.certificate_output)
    validate_output_path(args.certificate_json)
    return platform, fusion_set_id


def _upload(api_key, team_id, app_path):
    upload_response = upload(api_key, team_id, app_path)
    validate_response(upload_response)
    logging.info(f"Upload done. App-id: {upload_response.json()['id']}")
    return upload_response.json()['id']


def _build(api_key, team_id, app_id, fusion_set_id, build_overrides, use_diagnostic_logs, build_to_test_vendor):
    build_overrides_json = init_overrides(build_overrides)
    if build_to_test_vendor:
        automation_vendor = init_automation_vendor(build_to_test_vendor).name
        build_response = build_to_test(api_key, team_id, app_id, fusion_set_id, automation_vendor,
                                       overrides=build_overrides_json, use_diagnostic_logs=use_diagnostic_logs)
    else:
        build_response = build(api_key, team_id, app_id, fusion_set_id, build_overrides_json, use_diagnostic_logs)
    validate_response(build_response)
    logging.info(f"Build request started. Response: {build_response.json()}")
    task_id = build_response.json()['task_id']
    wait_for_status_complete(api_key, team_id, task_id)
    logging.info(f"Build request finished.")
    return task_id


def _context(api_key, team_id, task_id):
    context_response = context(api_key, team_id, task_id)
    validate_response(context_response)
    logging.info(f"Context request started. Response: {context_response.json()}")
    wait_for_status_complete(api_key, team_id, task_id)
    logging.info(f"Context request finished.")


def _sign(args, platform, task_id, sign_overrides):
    sign_overrides_json = init_overrides(sign_overrides)
    if platform == Platform.ANDROID:
        if args.sign_on_appdome:
            r = sign_android(args.api_key, args.team_id, task_id, args.keystore, args.keystore_pass,
                             args.keystore_alias, args.key_pass,
                             args.signing_fingerprint if args.google_play_signing else None, sign_overrides_json,
                             args.signing_fingerprint_upgrade if args.google_play_signing else None)
        elif args.private_signing:
            r = private_sign_android(args.api_key, args.team_id, task_id, args.signing_fingerprint,
                                     args.google_play_signing, sign_overrides_json, args.signing_fingerprint_upgrade)
        else:
            r = auto_dev_sign_android(args.api_key, args.team_id, task_id, args.signing_fingerprint,
                                      args.google_play_signing, sign_overrides_json, args.signing_fingerprint_upgrade)
    else:
        if args.sign_on_appdome:
            r = sign_ios(args.api_key, args.team_id, task_id, args.keystore, args.keystore_pass,
                         args.provisioning_profiles, args.entitlements, sign_overrides_json)
        elif args.private_signing:
            r = private_sign_ios(args.api_key, args.team_id, task_id, args.provisioning_profiles, sign_overrides_json)
        else:
            r = auto_dev_sign_ios(args.api_key, args.team_id, task_id, args.provisioning_profiles, args.entitlements,
                                  sign_overrides_json)

    validate_response(r)
    logging.info(f"Signing request started. Response: {r.json()}")
    wait_for_status_complete(args.api_key, args.team_id, task_id)
    logging.info(f"Signing request finished.")


def _download_file(api_key, team_id, task_id, output_path, download_func):
    download_response = download_func(api_key, team_id, task_id)
    validate_response(download_response)
    with open(output_path, 'wb') as f:
        f.write(download_response.content)
    logging.info(f"File written to {output_path}")


def main():
    args = parse_arguments()
    platform, fusion_set_id = validate_args(args)

    app_id = _upload(args.api_key, args.team_id, args.app) if args.app else args.app_id

    task_id = _build(args.api_key, args.team_id, app_id, fusion_set_id, args.build_overrides, args.diagnostic_logs,
                     args.build_to_test_vendor)

    _context(args.api_key, args.team_id, task_id)

    _sign(args, platform, task_id, args.sign_overrides)

    if args.output:
        _download_file(args.api_key, args.team_id, task_id, args.output, download)
    if _get_obfuscation_map_status(args.api_key, args.team_id, task_id):
        download_action(args.api_key, args.team_id, task_id, args.deobfuscation_script_output, 'deobfuscation_script')
        if args.deobfuscation_script_output:
            if args.firebase_app_id:
                crashlytics = Crashlytics()
                crashlytics.upload_deobfuscation_map(args.deobfuscation_script_output, args.firebase_app_id)
            if args.datadog_api_key:
                datadog = DataDog()
                datadog.upload_deobfuscation_map(deobfuscation_script_output=args.deobfuscation_script_output,
                                                 dd_api_key=args.datadog_api_key)
    if not args.auto_dev_private_signing:
        download_action(args.api_key, args.team_id, task_id, args.sign_second_output, 'sign_second_output')
    if args.certificate_output:
        _download_file(args.api_key, args.team_id, task_id, args.certificate_output, download_certified_secure)
    if args.certificate_json:
        _download_file(args.api_key, args.team_id, task_id, args.certificate_json, download_certified_secure_json)
        format_json_file(args.certificate_json)


if __name__ == '__main__':
    main()
