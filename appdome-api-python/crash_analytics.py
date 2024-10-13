from abc import ABC, abstractmethod


class CrashAnalytics(ABC):
    @abstractmethod
    def upload_deobfuscation_map(self, deobfuscation_script_output, api_key):
        pass
