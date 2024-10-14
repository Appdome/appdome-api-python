import os
import logging
import subprocess
from crash_analytics import CrashAnalytics


class Crashlytics(CrashAnalytics):
    """
    Crashlytics service for uploading deobfuscation mapping files to Firebase Crashlytics.
    """
    def __init__(self, deobfuscation_script_output, firebase_app_id):
        """
        Initialize Crashlytics with the deobfuscation script output path and Firebase App ID.

        :param deobfuscation_script_output: Path to the deobfuscation script output file
        :param firebase_app_id: Firebase App ID for Crashlytics
        """
        super().__init__(deobfuscation_script_output, firebase_app_id)

    def upload_mappingfileid_file(self, tmpdir):
        """
        Upload the Crashlytics mapping file to Firebase using the provided Firebase App ID.

        :param tmpdir: Temporary directory where files are extracted
        :return: None
        """
        mappingfileid_file = os.path.join(tmpdir, "com_google_firebase_crashlytics_mappingfileid.xml")

        if not os.path.exists(mappingfileid_file):
            logging.warning("Missing com_google_firebase_crashlytics_mappingfileid.xml file. "
                            "Skipping code deobfuscation mapping file upload to Crashlytics.")
            return

        subprocess.call(
            f"firebase crashlytics:mappingfile:upload --app={self.faid_or_dd_api_key} --resource-file={mappingfileid_file} "
            f"{os.path.join(tmpdir, 'mapping.txt')}", shell=True)




