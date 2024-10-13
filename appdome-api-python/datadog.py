import zipfile
import os
import logging
import subprocess
import tempfile
from contextlib import contextmanager
from shutil import rmtree
import json
import requests
from crash_analytics import CrashAnalytics
from CustomMultipartEncoder import CustomMultipartEncoder

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


class DataDog(CrashAnalytics):

    def upload_deobfuscation_map(self, deobfuscation_script_output, dd_api_key):
        if not os.path.exists(deobfuscation_script_output):
            logging.warning(
                "Missing deobfuscation script. Skipping code deobfuscation mapping file upload to Crashlytics.")
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

            mappingfileid_file = os.path.join(tmpdir, "data_dog_metadata.json")
            if not os.path.exists(mappingfileid_file):
                logging.warning("Missing datadog_mapping file."
                                " Skipping code deobfuscation mapping file upload to DataDog.")
                return
            build_id, service_name, version = self.load_json(mappingfileid_file)
            self.api_call_upload_mapping_file(api_key=dd_api_key, build_id=build_id, version_name=version,
                                              service_name=service_name, mapping_file_path=mapping_file)

    def load_json(self, file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)

            # Extract fields into variables
            build_id = data.get("build_id")
            service_name = data.get("service_name")
            version = data.get("version")

            return build_id, service_name, version

    def api_call_upload_mapping_file(self, api_key, build_id, version_name, service_name, mapping_file_path):
        url = "https://sourcemap-intake.datadoghq.com/api/v2/srcmap"

        # Set environment variables (if needed)
        os.environ["DD_SITE"] = "datadoghq.com"
        os.environ["DD_API_KEY"] = api_key
        event_data = {
            "build_id": build_id,
            "service": service_name,
            "type": "jvm_mapping_file",
            "version": version_name
        }
        event_json = json.dumps(event_data)
        fields = {
            "event": ("event.json", event_json.encode('utf-8'), "application/json; charset=utf-8"),
            "jvm_mapping_file": ("jvm_mapping", open(mapping_file_path, "rb").read(), "text/plain")
        }

        # Use custom multipart encoder
        encoder = CustomMultipartEncoder(fields)

        headers = {
            "dd-evp-origin": "dd-sdk-android-gradle-plugin",
            "dd-evp-origin-version": "1.13.0",
            "dd-api-key": api_key,
            "Content-Type": encoder.content_type,
            "Accept-Encoding": "gzip"
        }

        # Send the POST request to Datadog
        response = requests.post(url, headers=headers, data=encoder.to_string())

        if response.status_code == 202:
            logging.info("Mapping file uploaded successfully!")
        else:
            logging.info(f"Failed to upload mapping file. Status code: {response.status_code}")
            logging.info(f"Response: {response.text}")
