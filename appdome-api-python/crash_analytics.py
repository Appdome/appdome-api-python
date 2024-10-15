import logging
import zipfile
import os
from abc import ABC, abstractmethod
from utils import erased_temp_dir


class CrashAnalytics(ABC):
    """
    Abstract base class for crash analytics services (e.g., Crashlytics, DataDog).
    """
    def __init__(self, deobfuscation_script_output, faid_or_dd_api_key):
        """
        Initialize CrashAnalytics with the deobfuscation script output path and API key.

        :param deobfuscation_script_output: Path to the deobfuscation script output zip file
        :param faid_or_dd_api_key: Data Dig API key or Firebase App ID depending on the service
        """
        self.deobfuscation_script_output = deobfuscation_script_output
        self.faid_or_dd_api_key = faid_or_dd_api_key

    @abstractmethod
    def upload_mappingfileid_file(self, tmpdir):
        """
        Abstract method to be implemented by subclasses to upload mapping file to their respective services.

        :param tmpdir: Temporary directory where files are extracted
        """
        pass

    def upload_deobfuscation_map(self):
        """
        Upload the deobfuscation mapping file to the specified service after extracting the contents.

        :return: None
        """
        if not os.path.exists(self.deobfuscation_script_output):
            logging.warning("Missing deobfuscation script. Skipping code deobfuscation mapping file upload.")
            return
        if not self.faid_or_dd_api_key:
            logging.warning("Missing API key or ID. Skipping code deobfuscation mapping file upload.")
            return
        try:
            with erased_temp_dir() as tmpdir:
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


