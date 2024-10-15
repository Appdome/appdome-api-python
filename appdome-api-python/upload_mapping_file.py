import argparse
import logging
from crashlytics import Crashlytics
from datadog import DataDog
from utils import init_logging


def sanitize_input(file_path):
    """
    Removes leading/trailing whitespaces from the file path and handles spaces by wrapping in quotes.
    """
    return file_path.strip().strip('"').strip("'")  # Wrap the path in quotes if there are spaces


def upload_mapping_file(deobfuscation_mapping_file, fire_base_app_id, data_dog_api_key):
    """
    Upload deobfuscation mapping files to either Crashlytics or DataDog, depending on the provided API keys.

    :param deobfuscation_mapping_file: Path to the deobfuscation mapping file
    :param fire_base_app_id: Firebase App ID for Crashlytics (optional)
    :param data_dog_api_key: Datadog API key (optional)
    :return: None
    """
    uploaded = False  # This will track whether any upload has started
    if fire_base_app_id:
        logging.info("Uploading deobfuscation mapping file to Crashlytics...")
        crashlytics = Crashlytics(deobfuscation_script_output=deobfuscation_mapping_file,
                                  firebase_app_id=fire_base_app_id)
        crashlytics.upload_deobfuscation_map()
        uploaded = True
    if data_dog_api_key:
        logging.info("Uploading deobfuscation mapping file to Data Dog...")
        datadog = DataDog(deobfuscation_script_output=deobfuscation_mapping_file,
                          dd_api_key=data_dog_api_key)
        datadog.upload_deobfuscation_map()
        uploaded = True

    if not uploaded:
        logging.warning("Invalid arguments! You must provide the correct combination of arguments depending on "
                        "the upload: firebase_app_id or datadog_api_key are mandatory inputs.")


def parse_arguments():
    """
    Parse command-line arguments for uploading deobfuscation mapping files.

    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Upload Deobfuscation Mapping Files to Datadog/Crashlytics")
    parser.add_argument('--mapping_files', '-dso', required=True, metavar='mapping_files',
                        help='deobfuscation zip file when building with "Obfuscate App Logic"')
    parser.add_argument("-faid", '--firebase_app_id', metavar='firebase_app_id',
                        help="Firebase App ID (for Crashlytics)")
    parser.add_argument('-dd_api_key', '--datadog_api_key', metavar='datadog_api_key', help="Datadog API key")
    return parser.parse_args()


def main():
    """
    Main function that initializes logging, parses arguments, and uploads mapping files.

    :return: None
    """
    args = parse_arguments()
    init_logging()
    args.mapping_files = sanitize_input(args.mapping_files)
    upload_mapping_file(deobfuscation_mapping_file=args.mapping_files, fire_base_app_id=args.firebase_app_id,
                        data_dog_api_key=args.datadog_api_key)


if __name__ == "__main__":
    main()
