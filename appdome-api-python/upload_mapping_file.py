import argparse
import logging
import sys
from crashlytics import Crashlytics
from datadog import DataDog
from utils import init_logging


def sanitize_input(file_path):
    """
    Removes leading/trailing whitespaces from the file path and handles spaces by wrapping in quotes.
    """
    return file_path.strip().strip('"').strip("'")  # Wrap the path in quotes if there are spaces


def main():
    parser = argparse.ArgumentParser(description="Upload Deobfuscation Mapping File to Datadog/Crashlytics")
    parser.add_argument("--mapping", required=False, help="Path to the mapping.txt file")
    parser.add_argument("-faid", '--firebase_app_id', metavar='firebase_app_id',
                        help="Firebase App ID (for Crashlytics)")
    parser.add_argument('--mapping_files', '-dso', required=True, metavar='mapping_files',
                        help='Output zip file deobfuscation scripts when building with "Obfuscate App Logic"')
    parser.add_argument("--crashlytics_mappingfileid",
                        help="Crashlytics mapping file ID (com_google_firebase_crashlytics_mappingfileid.xml)")
    parser.add_argument("--datadog_mappingfileid", help="Datadog metadata file (data_dog_metadata.json)")
    parser.add_argument('-dd_api_key', '--datadog_api_key', metavar='datadog_api_key', help="Datadog API key")

    args = parser.parse_args()
    init_logging()
    args.mapping_files = sanitize_input(args.mapping_files)
    if args.mapping_files:
        if args.firebase_app_id:
            logging.info("Uploading to Crashlytics...")
            crashlytics = Crashlytics(deobfuscation_script_output=args.mapping_files,
                                      faid=args.firebase_app_id)
            crashlytics.upload_deobfuscation_map()
        if args.datadog_api_key:
            logging.info("Uploading to Data Dog...")
            datadog = DataDog(deobfuscation_script_output=args.mapping_files,
                              dd_api_key=args.datadog_api_key)
            datadog.upload_deobfuscation_map()
        else:
            logging.error(
                "Invalid arguments! You must provide the correct combination of arguments depending on the upload "
                "target.")
            sys.exit(1)
    else:
        logging.warning("mapping_files zip is missing")


if __name__ == "__main__":
    main()
