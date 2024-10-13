import zipfile
import os
import logging
import subprocess
import tempfile
from contextlib import contextmanager
from shutil import rmtree
from crash_analytics import CrashAnalytics


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


class Crashlytics(CrashAnalytics):
    def upload_deobfuscation_map(self, deobfuscation_script_output, faid):
        if not os.path.exists(deobfuscation_script_output):
            logging.warning(
                "Missing deobfuscation script. Skipping code deobfuscation mapping file upload to Crashlytics.")
            return
        if not faid:
            logging.warning("Missing Firebase project app ID. "
                            "Skipping code deobfuscation mapping file upload to Crashlytics.")
            return

        with erasedTempDir() as tmpdir:
            with zipfile.ZipFile(deobfuscation_script_output, "r") as zip_file:
                zip_file.extractall(tmpdir)

            mapping_file = os.path.join(tmpdir, "mapping.txt")
            if not os.path.exists(mapping_file):
                logging.warning(
                    "Missing mapping.txt file. Skipping code deobfuscation mapping file upload to Crashlytics.")
                return

            mappingfileid_file = os.path.join(tmpdir, "com_google_firebase_crashlytics_mappingfileid.xml")
            if not os.path.exists(mappingfileid_file):
                logging.warning("Missing com_google_firebase_crashlytics_mappingfileid.xml file."
                                " Skipping code deobfuscation mapping file upload to Crashlytics.")
                return

            subprocess.call(
                f"firebase crashlytics:mappingfile:upload --app={faid} --resource-file={mappingfileid_file} "
                f"{mapping_file}", shell=True)
