import json
import sys
import tempfile
from os.path import abspath, dirname

import requests

sys.path.insert(0, dirname(dirname(abspath(__file__))))

API_KEY = 'test-api-key'
TEAM_ID = '11111111-2222-3333-4444-555555555555'
APP_ID = 'aaaaaaaa-0000-0000-0000-000000000001'
TASK_ID = 'bbbbbbbb-0000-0000-0000-000000000002'

# Trimmed from a real /pwappload response (pwa_platform "aab"), with IDs anonymized.
PWA_UPLOAD_RESPONSE = [{
    "app": {"id": APP_ID, "type": "original", "pack_name": "My PWA.aab", "pack_type": "aab",
            "is_pwapp": True, "status": "active", "metadata": {"app_fused": False, "PWA": {"PWA_URL": "https://example.com"}}},
    "taskId": {"task_id": TASK_ID},
}]

# Team / no Short Flow: upload only, no automatic build.
PWA_UPLOAD_ONLY_RESPONSE = [{"app": PWA_UPLOAD_RESPONSE[0]["app"]}]

PWA_CONFIG = {"pwa_address": "https://example.com", "pwa_platform": "aab", "pwa_app_name": "My PWA"}


def fake_response(status_code=200, json_body=None, text=None, url='https://fusion.appdome.com/api/v1/pwappload'):
    response = requests.Response()
    response.status_code = status_code
    response._content = (json.dumps(json_body) if json_body is not None else (text or '')).encode()
    response.request = requests.Request('POST', url).prepare()
    return response


def write_json_file(content):
    f = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
    f.write(content if isinstance(content, str) else json.dumps(content))
    f.close()
    return f.name


def write_binary_file(content, suffix='.mobileprovision'):
    f = tempfile.NamedTemporaryFile('wb', suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return f.name
