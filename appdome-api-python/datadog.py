import os
import logging
import json
import requests
from crash_analytics import CrashAnalytics
from CustomMultipartEncoder import CustomMultipartEncoder



class DataDog(CrashAnalytics):
    def __init__(self, deobfuscation_script_output, dd_api_key):
        super().__init__(deobfuscation_script_output, dd_api_key)

    def upload_mappingfileid_file(self, tmpdir):
        mappingfileid_file = os.path.join(tmpdir, "data_dog_metadata.json")

        if not os.path.exists(mappingfileid_file):
            logging.warning("Missing datadog_mapping file. Skipping code deobfuscation mapping file upload to DataDog.")
            return

        build_id, service_name, version = self.load_json(mappingfileid_file)
        self.api_call_upload_mapping_file(api_key=self.faid_or_dd_api_key, build_id=build_id, version_name=version,
                                          service_name=service_name,
                                          mapping_file_path=os.path.join(tmpdir, "mapping.txt"))

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
            logging.info("Mapping file uploaded successfully to Data Dog!")
        else:
            logging.info(f"Failed to upload mapping file to DataDog. Status code: {response.status_code}")
            logging.info(f"Response: {response.text}")
