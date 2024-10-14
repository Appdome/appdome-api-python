import logging
import zipfile
import os
from abc import ABC, abstractmethod
import tempfile
from contextlib import contextmanager
from shutil import rmtree


class CrashAnalytics(ABC):
    def __init__(self, deobfuscation_script_output, faid_or_dd_api_key):
        self.deobfuscation_script_output = deobfuscation_script_output
        self.faid_or_dd_api_key = faid_or_dd_api_key

    @abstractmethod
    def upload_mappingfileid_file(self, tmpdir):
        """Each class should implement the logic to upload its specific mappingfileid_file"""
        pass

    def upload_deobfuscation_map(self):
        if not os.path.exists(self.deobfuscation_script_output):
            logging.warning("Missing deobfuscation script. Skipping code deobfuscation mapping file upload.")
            return
        if not self.faid_or_dd_api_key:
            logging.warning("Missing API key or ID. Skipping code deobfuscation mapping file upload.")
            return
        try:
            with self.erased_temp_dir() as tmpdir:
                with zipfile.ZipFile(self.deobfuscation_script_output, "r") as zip_file:
                    zip_file.extractall(tmpdir)

                mapping_file = os.path.join(tmpdir, "mapping.txt")
                if not os.path.exists(mapping_file):
                    logging.warning("Missing mapping.txt file. Skipping code deobfuscation mapping file upload.")
                    return

                # Delegate to subclass for specific mappingfileid_file handling
                self.upload_mappingfileid_file(tmpdir)
        except Exception as e:
            logging.error(f"An error occurred during file extraction or mapping file processing: {e}")

    @contextmanager
    def erased_temp_dir(self):
        tempDir = tempfile.mkdtemp()
        try:
            yield tempDir
        except Exception as e:
            raise e
        finally:
            if tempDir and os.path.exists(tempDir):
                rmtree(tempDir, ignore_errors=True)
