import zipfile
import os
import logging
import subprocess
import tempfile
from contextlib import contextmanager
from shutil import rmtree
import json
from datadog_api_client import ApiClient, Configuration
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

@contextmanager
def erasedTempDir():
    tempDir = tempfile.mkdtemp()
    try:
        yield tempDir
    except Exception as e:
        raise e
    finally:
        if tempDir and os.path.exists(tempDir):
            rmtree(tempDir, ignore_errors=True)


def upload_deobfuscation_map_datadog(deobfuscation_script_output, dd_api_key):
    if not os.path.exists(deobfuscation_script_output):
        logging.warning("Missing deobfuscation script. Skipping code deobfuscation mapping file upload to Crashlytics.")
        return
    if not dd_api_key:
        logging.warning("Missing Firebase project app ID. "
                        "Skipping code deobfuscation mapping file upload to Crashlytics.")
        return

    with erasedTempDir() as tmpdir:
        with zipfile.ZipFile(deobfuscation_script_output, "r") as zip_file:
            zip_file.extractall(tmpdir)

        mapping_file = os.path.join(tmpdir, "mapping.txt")
        if not os.path.exists(mapping_file):
            logging.warning("Missing mapping.txt file. Skipping code deobfuscation mapping file upload to DataDog.")
            return

        mappingfileid_file = os.path.join(tmpdir, "datadog_mapping.json")
        if not os.path.exists(mappingfileid_file):
            logging.warning("Missing com_google_firebase_crashlytics_mappingfileid.xml file."
                            " Skipping code deobfuscation mapping file upload to Crashlytics.")
            return
        build_id, service_name, version = load_json(mappingfileid_file)


        # subprocess.call(f"firebase crashlytics:mappingfile:upload --app={faid} --resource-file={mappingfileid_file} "
        #                 f"{mapping_file}", shell=True)


def load_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)

        # Extract fields into variables
        build_id = data.get("build_id")
        service_name = data.get("service_name")
        version = data.get("version")

        return build_id, service_name, version

def api_call_upload_mapping_file(api_key, build_id, version_name, service_name, mapping_file_path):
    url = "https://sourcemap-intake.datadoghq.com/api/v2/srcmap"

    # Set environment variables (if needed)
    os.environ["DD_SITE"] = "datadoghq.com"
    os.environ["DD_API_KEY"] = api_key
    configuration = Configuration()
    configuration.api_key = {'apiKeyAuth': api_key}
    configuration.verify_ssl = False
    # Event data for the JSON part of the multipart request
    # event_data = {
    #     "build_id": "954d5b4e-b3f4-4d26-bdbb-c0045e175dd3",
    #     "service": service_name,
    #     "variant": "",
    #     "version_code": app_version,
    #     "type": "jvm_mapping_file",
    #     "version": "Appdome_1.0"
    # }
    event_data = {
        "build_id": build_id,
        "service": service_name,
        "type": "jvm_mapping_file",
        "version": version_name
    }
    multipart_data = MultipartEncoder(
        fields={
            "event": ("event", json.dumps(event_data), "application/json; charset=utf-8"),
            "jvm_mapping_file": ("jvm_mapping", open(mapping_file_path, "rb"), "text/plain"),
        }
    )
    # Compress the mapping file
    # with open(mapping_file_path, "rb") as file:
    #     mapping_file_content = file.read()
    #     compressed_mapping = gzip.compress(mapping_file_content)
    #
    # # Prepare the multipart form data
    # multipart_data = MultipartEncoder(
    #     fields={
    #         "event": ("event", json.dumps(event_data), "application/json; charset=utf-8"),
    #         "jvm_mapping_file": ("jvm_mapping", compressed_mapping, "text/plain"),
    #     }
    # )

    headers = {
        "dd-evp-origin": "dd-sdk-android-gradle-plugin",
        "dd-evp-origin-version": "1.13.0",
        "dd-api-key": api_key,
        "Content-Type": multipart_data.content_type,
        "Accept-Encoding": "gzip",
        # "Content-Encoding": ""

    }

    # Send the POST request to Datadog
    response = requests.post(url, headers=headers, data=multipart_data)

    if response.status_code == 202:
        print("Mapping file uploaded successfully!")
    else:
        print(f"Failed to upload mapping file. Status code: {response.status_code}")
        print(f"Response: {response.text}")
