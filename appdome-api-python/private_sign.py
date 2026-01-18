import argparse
import logging

from utils import (cleaned_fd_list, add_provisioning_profiles_entitlements, run_task_action, add_google_play_signing_fingerprint,
                   ANDROID_SIGNING_FINGERPRINT_KEY, validate_response, add_common_args, init_common_args, init_overrides, add_private_signing_args, TASK_ID_KEY,
                   add_trusted_signing_fingerprint_list, validate_trusted_fingerprint_list_args)

PRIVATE_SIGN_ACTION = 'seal'


def private_sign_android(api_key, team_id, task_id, signing_fingerprint=None, is_google_play_signing=False,
                         sign_overrides=None, signing_fingerprint_upgrade=None, trusted_signing_fingerprint_list=None):
    overrides = {}
    if trusted_signing_fingerprint_list:
        add_trusted_signing_fingerprint_list(trusted_signing_fingerprint_list, overrides)
    elif is_google_play_signing:
        add_google_play_signing_fingerprint(signing_fingerprint, overrides, signing_fingerprint_upgrade)
    else:
        overrides[ANDROID_SIGNING_FINGERPRINT_KEY] = signing_fingerprint
    if sign_overrides:
            overrides.update(sign_overrides)
    return run_task_action(api_key, team_id, PRIVATE_SIGN_ACTION, task_id, overrides, None)


def private_sign_ios(api_key, team_id, task_id, provisioning_profiles_paths, sign_overrides=None):
    overrides = {}
    files_list = []
    with cleaned_fd_list() as open_fd:
        add_provisioning_profiles_entitlements(provisioning_profiles_paths, None, files_list, overrides, open_fd)
        if sign_overrides:
            overrides.update(sign_overrides)
        return run_task_action(api_key, team_id, PRIVATE_SIGN_ACTION, task_id, overrides, files_list)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Initialize private signing on Appdome')
    add_common_args(parser, add_task_id=True)
    add_private_signing_args(parser)
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    validate_trusted_fingerprint_list_args(args)

    overrides = init_overrides(args.sign_overrides)
            
    if args.signing_fingerprint or args.signing_fingerprint_list:
        r = private_sign_android(args.api_key, args.team_id, args.task_id, args.signing_fingerprint, args.google_play_signing, overrides,
                                 args.signing_fingerprint_upgrade, args.signing_fingerprint_list)
    else:
        r = private_sign_ios(args.api_key, args.team_id, args.task_id, args.provisioning_profiles, overrides)

    validate_response(r)
    logging.info(f"Private signing for Build id: {r.json()[TASK_ID_KEY]} started")


if __name__ == '__main__':
    main()
