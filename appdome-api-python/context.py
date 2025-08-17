import argparse
import logging

from utils import run_task_action, cleaned_fd_list, validate_response, add_common_args, init_common_args, TASK_ID_KEY


def context(api_key, team_id, task_id, new_bundle_id=None, new_version=None,
            new_build_num=None, new_display_name=None, app_icon_path=None, icon_overlay_path=None, context_overrides=None):

    overrides = {}
    if new_bundle_id:
        overrides['app_customization_pack_bundle_identifier'] = new_bundle_id
    if new_version:
        overrides['app_customization_pack_bundle_version'] = new_version
    if new_build_num:
        overrides['app_customization_pack_bundle_build_number'] = new_build_num
    if new_display_name:
        overrides['app_customization_pack_bundle_display_name'] = new_display_name
    if context_overrides:
        overrides.update(context_overrides)
    files = {}
    with cleaned_fd_list() as open_fd:
        if app_icon_path:
            f = open(app_icon_path, 'rb')
            open_fd.append(f)
            files['app_customization_application_icon'] = (app_icon_path, f)
        if icon_overlay_path:
            overrides['icon_overlay'] = True
            f = open(icon_overlay_path, 'rb')
            open_fd.append(f)
            files['icon_overlay_s3'] = (icon_overlay_path, f)

        return run_task_action(api_key, team_id, 'context', task_id, overrides, files)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Initialize Context on Appdome')
    add_common_args(parser, add_task_id=True)
    add_context_args(parser)
    return parser.parse_args()

def add_context_args(parser):
    parser.add_argument('--new_bundle_id', metavar='bundle_id_value', help='Change App identifier')
    parser.add_argument('--new_version', metavar='version_value', help='Change App version')
    parser.add_argument('--new_build_num', metavar='bundle_value', help='Change App build number')
    parser.add_argument('--new_display_name', metavar='display_name_value', help='Change App display name')
    parser.add_argument('--app_icon', metavar='icon_file', help='Path to new App icon file')
    parser.add_argument('--icon_overlay', metavar='icon_file', help='Path to App overlay icon file')


def main():
    args = parse_arguments()
    init_common_args(args)

    r = context(args.api_key, args.team_id, args.task_id, args.new_bundle_id, args.new_version, args.new_build_num,
                args.new_display_name, args.app_icon, args.icon_overlay)
    validate_response(r)
    logging.info(f"Context for Build id: {r.json()[TASK_ID_KEY]} started")


if __name__ == '__main__':
    main()
