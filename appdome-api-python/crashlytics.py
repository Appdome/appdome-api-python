import os
import logging
import subprocess
from crash_analytics import CrashAnalytics


class Crashlytics(CrashAnalytics):
    def __init__(self, deobfuscation_script_output, faid):
        super().__init__(deobfuscation_script_output, faid)

    def upload_mappingfileid_file(self, tmpdir):
        mappingfileid_file = os.path.join(tmpdir, "com_google_firebase_crashlytics_mappingfileid.xml")

        if not os.path.exists(mappingfileid_file):
            logging.warning("Missing com_google_firebase_crashlytics_mappingfileid.xml file. "
                            "Skipping code deobfuscation mapping file upload to Crashlytics.")
            return

        subprocess.call(
            f"firebase crashlytics:mappingfile:upload --app={self.faid_or_dd_api_key} --resource-file={mappingfileid_file} "
            f"{os.path.join(tmpdir, 'mapping.txt')}", shell=True)




