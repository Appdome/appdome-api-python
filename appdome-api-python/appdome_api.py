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
from context import context, add_context_args
from direct_upload import direct_upload
from download import download, download_action
from private_sign import private_sign_android, private_sign_ios
from pwa_upload import init_pwa_config, pwa_build, pwa_overrides, add_pwa_provisioning_profiles
from sign import sign_android, sign_ios
from status import wait_for_status_complete
from upload import upload
from utils import (validate_response, log_and_exit, add_build_overrides_arg, add_common_args, add_diagnostic_logs_arg,
                   add_fusion_set_id_arg, add_output_arg, add_upload_args, init_common_args, validate_output_path,
                   init_overrides, init_build_files, init_certs_pinning, add_signing_credentials_args, TASK_ID_KEY,
                   BUILD_FILE_SPECS, android_keystore, android_keystore_pass, android_keystore_alias, android_key_pass,
                   ios_p12, ios_p12_password, ios_provisioning_profiles, validate_trusted_fingerprint_list_args,
                   uuid_arg)
from status import _get_obfuscation_map_status
from appdome_test import download_appdome_test_results, start_appdome_test
from upload_mapping_file import upload_mapping_file


class Platform(Enum):
    UNKNOWN = 0
    ANDROID = 1
    IOS = 2


PWA_PLATFORMS = {'aab': Platform.ANDROID, 'ipa': Platform.IOS}
# Options that only apply to uploading an app file do not apply to --pwa.
# --build_overrides and --diagnostic_logs are sent as the PWA request overrides (and to the build when there is no
# automatic Short Flow build). --fusion_set_id is used only when the account has no Short Flow.
PWA_UNSUPPORTED_BUILD_ARGS = ('build_to_test_vendor', 'baseline_profile', 'startup_profile',
                              'input_mapping', 'cert_pinning_zip', 'direct_upload', 'skip_upload_checksum_call')


def parse_arguments():
    parser = argparse.ArgumentParser(description='Runs Appdome API commands')
    upload_group = add_upload_args(parser, include_app_id=True)
    upload_group.add_argument('--pwa', metavar='pwa_config_json_file',
                              help='Build a Secure PWA instead of uploading an app. Path to json file with PWA '
                                   'parameters (pwa_address, pwa_platform: aab or ipa, pwa_app_name, overrides). '
                                   'Replaces the upload step. With Short Flow the upload also builds with the '
                                   'default Playground Fusion Set; otherwise the Fusion Set is used to build')

    add_common_args(parser)

    parser.add_argument('--direct_upload', action='store_true', help="Upload app directly to Appdome, and not through aws pre-signed url")
    add_fusion_set_id_arg(parser, help='Appdome Fusion Set ID. '
                                       'Default for Android is environment variable APPDOME_ANDROID_FS_ID. '
                                       'Default for iOS is environment variable APPDOME_IOS_FS_ID')
    add_build_overrides_arg(parser)
    add_diagnostic_logs_arg(parser)
    parser.add_argument('-faid', '--firebase_app_id', metavar='firebase_app_id',
                        help='App ID in Firebase project (required for Crashlytics)')
    parser.add_argument('-dd_api_key', '--datadog_api_key', metavar='datadog_api_key',
                        help='Data Dog API_KEY (required for DataDog Deobfuscation)')
    parser.add_argument('-baseline_profile', '--baseline_profile', metavar='baseline_profile',
                        help='baseline profile file to use')
    parser.add_argument('-startup_profile', '--startup_profile', metavar='startup_profile',
                        help='startup profile file to use')
    parser.add_argument('-input_mapping', '--input_mapping', metavar='input_mapping',
                        help='Input obfuscation/minimization mapping file to use')
    parser.add_argument('-cert_zip', '--cert_pinning_zip', metavar='cert_pinning_zip',
                        help='Path to zip file containing dynamic certificates for certificate pinning')

    add_context_args(parser)

    sign_group = parser.add_mutually_exclusive_group(required=True)
    sign_group.add_argument('-s', '--sign_on_appdome', action='store_true', help='Sign on Appdome')
    sign_group.add_argument('-ps', '--private_signing', action='store_true', help='Sign application manually')
    sign_group.add_argument('-adps', '--auto_dev_private_signing', action='store_true',
                            help='Use a pre-generated signing script for automated local signing')

    add_signing_credentials_args(parser)
    # Output parameters
    add_output_arg(parser)
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
    parser.add_argument('--appdome_test', nargs='*', default=None, metavar='wait | atr appdome_test_results_json',
                        help='Run Appdome Test (Standard Launch Tests) on the signed build. '
                             'No extra args: start and print the Appdome Test task ID. '
                             'wait: poll until complete. '
                             'atr appdome_test_results_json: download Appdome Test Results JSON (implies wait).')
    parser.add_argument('-wol', '--workflow_output_logs', metavar='workflow_output_logs',
                        help='Enter path to a workflow output logs file (optional)')
    return parser.parse_args()


def validate_args(args):
    fusion_set_id = args.fusion_set_id
    platform = Platform.UNKNOWN
    init_common_args(args)
    if args.pwa:
        return _validate_pwa_args(args)
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
            log_and_exit(f"The Fusion Set ID must be specified or set through the correct platform environment variable")
        try:
            fusion_set_id = uuid_arg(fusion_set_id)
        except argparse.ArgumentTypeError as e:
            log_and_exit(str(e))

    _validate_signing_args(args, platform)
    return platform, fusion_set_id


def _validate_pwa_args(args):
    used_build_args = [f'--{name}' for name in PWA_UNSUPPORTED_BUILD_ARGS if getattr(args, name, None)]
    if used_build_args:
        log_and_exit(f"{', '.join(used_build_args)} cannot be used with --pwa")
    args.pwa_config = _pwa_config_with_build_options(init_pwa_config(args.pwa), args.build_overrides,
                                                     args.diagnostic_logs)
    platform = PWA_PLATFORMS[args.pwa_config['pwa_platform']]
    _validate_signing_args(args, platform)
    add_pwa_provisioning_profiles(args.pwa_config, ios_provisioning_profiles(args))
    fusion_set_id = args.fusion_set_id
    if fusion_set_id:
        try:
            fusion_set_id = uuid_arg(fusion_set_id)
        except argparse.ArgumentTypeError as e:
            log_and_exit(str(e))
    return platform, fusion_set_id


def _pwa_config_with_build_options(pwa_config, build_overrides=None, use_diagnostic_logs=False):
    """Merges --build_overrides and --diagnostic_logs into the PWA request overrides, like build.py does."""
    overrides = pwa_overrides(pwa_config)
    overrides.update(init_overrides(build_overrides))
    if use_diagnostic_logs:
        overrides['extended_logs'] = True
    if overrides:
        pwa_config['overrides'] = overrides
    return pwa_config


def _validate_signing_args(args, platform):
    if args.private_signing or args.auto_dev_private_signing:
        if platform == Platform.ANDROID and not args.signing_fingerprint and not args.signing_fingerprint_list:
            log_and_exit(f"Either signing_fingerprint or signing_fingerprint_list must be specified when using any Android local signing")

    if platform == Platform.IOS and not ios_provisioning_profiles(args):
        log_and_exit(f"Provisioning profiles must be specified when using any iOS signing")

    if args.sign_on_appdome:
        if platform == Platform.IOS:
            if not all([ios_p12(args), ios_p12_password(args)]):
                log_and_exit(f'All iOS signing credentials(keystore, keystore_pass) must be specified when using "On Appdome" signing')
        if platform == Platform.ANDROID:
            if not all([android_keystore(args), android_keystore_pass(args), android_keystore_alias(args), android_key_pass(args)]):
                log_and_exit(f'All Android signing credentials(keystore, keystore_pass, keystore_alias, key_pass) must be specified when using "On Appdome" signing')
        if args.google_play_signing and not args.signing_fingerprint:
            log_and_exit(f"Google signing fingerprint requires providing a signing fingerprint")

    if args.build_to_test_vendor and not any(
            args.build_to_test_vendor == vendor.value for vendor in BuildToTestVendors):
        log_and_exit(f"Vendor name provided for Build To Test isn't one of the acceptable vendors")

    if args.appdome_test is not None:
        if args.appdome_test not in ([], ['wait']) and not (
                len(args.appdome_test) == 2 and args.appdome_test[0] == 'atr'):
            log_and_exit("--appdome_test accepts no extra args, wait, or atr <appdome_test_results_json>")

    if args.appdome_test is not None and args.build_to_test_vendor:
        log_and_exit("Apps built via the Build-to-Test flow are not eligible — "
                     "only regular fuse/build (then sign) apps can run Appdome Test.")

    validate_trusted_fingerprint_list_args(args)

    if args.google_play_signing:
        if args.signing_fingerprint_upgrade and not args.signing_fingerprint:
            log_and_exit(f"Base Google signing fingerprint is required to upgrade the fingerprint")

    validate_output_path(args.output)
    validate_output_path(args.certificate_output)
    validate_output_path(args.certificate_json)
    if args.appdome_test and args.appdome_test[0] == 'atr':
        validate_output_path(args.appdome_test[1])


def _upload(api_key, team_id, app_path, direct_upload_param=False, skip_upload_checksum_call=False):
    upload_func = direct_upload if direct_upload_param else upload
    app_id = upload_func(api_key, team_id, app_path, skip_upload_checksum_call=skip_upload_checksum_call)
    logging.info(f"Upload done. App ID: {app_id}")
    return app_id


def _build(api_key, team_id, app_id, fusion_set_id, build_overrides, use_diagnostic_logs, build_to_test_vendor,
           workflow_output_logs=None, cert_pinning_zip=None, args=None):
    build_overrides_json = init_overrides(build_overrides)
    files = init_certs_pinning(cert_pinning_zip)
    build_files = {key: getattr(args, key, None) for key in BUILD_FILE_SPECS} if args else None
    init_build_files(build_files, files)
    if build_to_test_vendor:
        automation_vendor = init_automation_vendor(build_to_test_vendor).name
        build_response = build_to_test(api_key, team_id, app_id, fusion_set_id, automation_vendor,
                                       overrides=build_overrides_json, use_diagnostic_logs=use_diagnostic_logs,
                                       files=files)
    else:
        build_response = build(api_key, team_id, app_id, fusion_set_id, build_overrides_json, use_diagnostic_logs,
                               files=files)
    validate_response(build_response)
    logging.info(f"Build request started. Response: {build_response.json()}")
    task_id = build_response.json()[TASK_ID_KEY]
    wait_for_status_complete(api_key, team_id, task_id, operation="build",
                             workflow_output_logs_path=workflow_output_logs)
    logging.info(f"Build request finished.")
    return task_id


def _pwa_upload_and_build(args, platform, fusion_set_id):
    """
    Uploads the PWA and returns the Build ID.
    Short Flow accounts: the upload is built automatically (default Playground Fusion Set) and --fusion_set_id is
    ignored. Otherwise the App ID is built with --fusion_set_id (or APPDOME_ANDROID_FS_ID / APPDOME_IOS_FS_ID).
    """
    uploads = pwa_build(args.api_key, args.team_id, args.pwa_config, wait=True,
                        workflow_output_logs=args.workflow_output_logs)
    if len(uploads) != 1:
        log_and_exit(f"Expected a single PWA upload, got {len(uploads)}: {uploads}")
    app_id, task_id = uploads[0]['app_id'], uploads[0][TASK_ID_KEY]
    if task_id:
        if fusion_set_id:
            logging.warning(f"--fusion_set_id {fusion_set_id} was not used: Short Flow built the app automatically "
                            f"with the default Playground Fusion Set")
        logging.info(f"PWA upload and build finished.")
        return task_id

    if not fusion_set_id:
        fusion_set_id = getenv('APPDOME_IOS_FS_ID' if platform == Platform.IOS else 'APPDOME_ANDROID_FS_ID')
    if not fusion_set_id:
        log_and_exit(f"PWA uploaded (App ID: {app_id}) but not built: this account has no automatic Short Flow build. "
                     f"Pass --fusion_set_id (or set the platform Fusion Set environment variable), or build it with "
                     f"--app_id {app_id} --fusion_set_id <id>")
    try:
        fusion_set_id = uuid_arg(fusion_set_id)
    except argparse.ArgumentTypeError as e:
        log_and_exit(str(e))
    logging.info(f"Building PWA App ID {app_id} with Fusion Set {fusion_set_id}")
    return _build(args.api_key, args.team_id, app_id, fusion_set_id, args.build_overrides, args.diagnostic_logs,
                  None, args.workflow_output_logs)


def _context(api_key, team_id, task_id, workflow_output_logs=None, new_bundle_id=None, new_version=None,
             new_build_num=None, new_display_name=None, app_icon=None, icon_overlay=None):
    context_response = context(api_key, team_id, task_id, new_bundle_id, new_version, new_build_num, new_display_name, app_icon, icon_overlay)
    validate_response(context_response)
    logging.info(f"Context request started. Response: {context_response.json()}")
    wait_for_status_complete(api_key, team_id, task_id, operation="context",
                             workflow_output_logs_path=workflow_output_logs)
    logging.info(f"Context request finished.")


def _sign(args, platform, task_id, sign_overrides, workflow_output_logs=None):
    sign_overrides_json = init_overrides(sign_overrides)
    if platform == Platform.ANDROID:
        if args.sign_on_appdome:
            r = sign_android(args.api_key, args.team_id, task_id, android_keystore(args), android_keystore_pass(args),
                             android_keystore_alias(args), android_key_pass(args),
                             args.signing_fingerprint if args.google_play_signing else None, sign_overrides_json,
                             args.signing_fingerprint_upgrade if args.google_play_signing else None,
                             args.signing_fingerprint_list)
        elif args.private_signing:
            r = private_sign_android(args.api_key, args.team_id, task_id, args.signing_fingerprint,
                                     args.google_play_signing, sign_overrides_json, args.signing_fingerprint_upgrade,
                                     args.signing_fingerprint_list)
        else:
            r = auto_dev_sign_android(args.api_key, args.team_id, task_id, args.signing_fingerprint,
                                      args.google_play_signing, sign_overrides_json, args.signing_fingerprint_upgrade,
                                      args.signing_fingerprint_list)
    else:
        if args.sign_on_appdome:
            r = sign_ios(args.api_key, args.team_id, task_id, ios_p12(args), ios_p12_password(args),
                         ios_provisioning_profiles(args), args.entitlements, sign_overrides_json)
        elif args.private_signing:
            r = private_sign_ios(args.api_key, args.team_id, task_id, ios_provisioning_profiles(args), sign_overrides_json)
        else:
            r = auto_dev_sign_ios(args.api_key, args.team_id, task_id, ios_provisioning_profiles(args), args.entitlements,
                                  sign_overrides_json)

    validate_response(r)
    logging.info(f"Signing request started. Response: {r.json()}")
    wait_for_status_complete(args.api_key, args.team_id, task_id, operation="sign",
                             workflow_output_logs_path=workflow_output_logs)
    logging.info(f"Signing request finished.")


def _download_file(api_key, team_id, task_id, output_path, download_func):
    download_response = download_func(api_key, team_id, task_id)
    validate_response(download_response)
    with open(output_path, 'wb') as f:
        f.write(download_response.content)
    logging.info(f"File written to {output_path}")


def _appdome_test(api_key, team_id, parent_task_id, wait=False, results_path=None):
    response = start_appdome_test(api_key, team_id, parent_task_id)
    validate_response(response)
    test_task_id = response.json()[TASK_ID_KEY]
    logging.info(f"Appdome Test started: Task ID: {test_task_id}")
    if wait or results_path:
        wait_for_status_complete(api_key, team_id, test_task_id, operation='appdome_test')
        logging.info("Appdome Test completed")
    if results_path:
        download_appdome_test_results(api_key, team_id, test_task_id, results_path)


def main():
    args = parse_arguments()
    platform, fusion_set_id = validate_args(args)

    if args.pwa:
        task_id = _pwa_upload_and_build(args, platform, fusion_set_id)
    else:
        app_id = _upload(args.api_key, args.team_id, args.app, args.direct_upload,
                         args.skip_upload_checksum_call) if args.app else args.app_id

        task_id = _build(args.api_key, args.team_id, app_id, fusion_set_id, args.build_overrides,
                         args.diagnostic_logs, args.build_to_test_vendor, args.workflow_output_logs,
                         args.cert_pinning_zip, args)

    _context(args.api_key, args.team_id, task_id, args.workflow_output_logs, args.new_bundle_id, args.new_version,
             args.new_build_num, args.new_display_name, args.app_icon, args.icon_overlay)

    _sign(args, platform, task_id, args.sign_overrides, args.workflow_output_logs)

    if args.output:
        _download_file(args.api_key, args.team_id, task_id, args.output, download)
    if _get_obfuscation_map_status(args.api_key, args.team_id, task_id):
        download_action(args.api_key, args.team_id, task_id, args.deobfuscation_script_output, 'deobfuscation_script')
        if args.deobfuscation_script_output and (args.datadog_api_key or args.firebase_app_id):
            upload_mapping_file(deobfuscation_mapping_file=args.deobfuscation_script_output,
                                fire_base_app_id=args.firebase_app_id, data_dog_api_key=args.datadog_api_key)
    if not args.auto_dev_private_signing:
        download_action(args.api_key, args.team_id, task_id, args.sign_second_output, 'sign_second_output')
    if args.certificate_output:
        _download_file(args.api_key, args.team_id, task_id, args.certificate_output, download_certified_secure)
    if args.certificate_json:
        _download_file(args.api_key, args.team_id, task_id, args.certificate_json, download_certified_secure_json)
        format_json_file(args.certificate_json)

    if args.appdome_test is not None:
        results_path = args.appdome_test[1] if args.appdome_test and args.appdome_test[0] == 'atr' else None
        _appdome_test(args.api_key, args.team_id, task_id,
                      wait=args.appdome_test == ['wait'] or bool(results_path),
                      results_path=results_path)

if __name__ == '__main__':
    main()
