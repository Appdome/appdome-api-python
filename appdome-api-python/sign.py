import argparse
import logging

from utils import (add_provisioning_profiles_entitlements, add_google_play_signing_fingerprint,
                   run_task_action, cleaned_fd_list, validate_response, add_common_args, init_common_args, init_overrides,
                   add_signing_credentials_args, TASK_ID_KEY, android_keystore, android_keystore_pass, android_keystore_alias,
                   android_key_pass, ios_p12, ios_p12_password, ios_provisioning_profiles,
                   add_trusted_signing_fingerprint_list, validate_trusted_fingerprint_list_args)

SIGN_ACTION = 'sign'


def sign_android(api_key, team_id, task_id,
                 keystore_path, keystore_pass, key_alias, key_pass,
                 google_play_signing_fingerprint=None, sign_overrides=None,
                 google_play_signing_fingerprint_upgrade=None, trusted_signing_fingerprint_list=None):
    overrides = {
        'signing_keystore_password':  keystore_pass,
        'signing_keystore_alias': key_alias,
        'signing_keystore_key_password': key_pass
    }
    
    if trusted_signing_fingerprint_list:
        add_trusted_signing_fingerprint_list(trusted_signing_fingerprint_list, overrides)
    else:
        add_google_play_signing_fingerprint(google_play_signing_fingerprint, overrides,
                                            google_play_signing_fingerprint_upgrade)

    if sign_overrides:
        overrides.update(sign_overrides)

    with open(keystore_path, 'rb') as f:
        files = {'signing_keystore': (keystore_path, f)}
        return run_task_action(api_key, team_id, SIGN_ACTION, task_id, overrides, files)


def sign_ios(api_key, team_id, task_id,
             keystore_p12_path, keystore_pass, provisioning_profiles_paths, entitlements_paths=None, sign_overrides=None):
    overrides = {'signing_p12_password':  keystore_pass}

    with cleaned_fd_list() as open_fd:
        f = open(keystore_p12_path, 'rb')
        open_fd.append(f)
        files_list = [('signing_p12_content', (keystore_p12_path, f))]
        add_provisioning_profiles_entitlements(provisioning_profiles_paths, entitlements_paths, files_list, overrides, open_fd)
        if sign_overrides:
            overrides.update(sign_overrides)
        return run_task_action(api_key, team_id, SIGN_ACTION, task_id, overrides, files_list)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Initialize signing on Appdome')
    add_common_args(parser, add_task_id=True)
    add_signing_credentials_args(parser, True)
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_common_args(args)
    validate_trusted_fingerprint_list_args(args)

    overrides = init_overrides(args.sign_overrides)

    if args.keystore_alias:
        r = sign_android(args.api_key, args.team_id, args.task_id, android_keystore(args), android_keystore_pass(args),
                         android_keystore_alias(args), android_key_pass(args), args.signing_fingerprint, overrides,
                         args.signing_fingerprint_upgrade, args.signing_fingerprint_list)
    else:
        r = sign_ios(args.api_key, args.team_id, args.task_id, ios_p12(args), ios_p12_password(args),
                     ios_provisioning_profiles(args), args.entitlements, overrides)

    validate_response(r)
    logging.info(f"On Appdome signing for Build id: {r.json()[TASK_ID_KEY]} started")


if __name__ == '__main__':
    main()
