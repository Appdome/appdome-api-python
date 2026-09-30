import base64
import sys
import unittest
from os import remove
from unittest import mock

from pwa_test_utils import API_KEY, TEAM_ID, APP_ID, TASK_ID, PWA_CONFIG, write_json_file, write_binary_file

import appdome_api  # noqa: E402
from appdome_api import Platform  # noqa: E402

BUILD = [{'app_id': APP_ID, 'task_id': TASK_ID, 'pack_type': 'aab', 'status': 'active'}]
UPLOAD_ONLY = [{'app_id': APP_ID, 'task_id': None, 'pack_type': 'aab', 'status': 'active'}]
BUILT_TASK_ID = 'cccccccc-0000-0000-0000-000000000003'
FUSION_SET_ID = '22222222-3333-4444-5555-666666666666'
ANDROID_SIGNING = ['--sign_on_appdome', '--keystore', 'k.keystore', '--keystore_pass', 'kp',
                   '--keystore_alias', 'alias', '--key_pass', 'keyp']


class AppdomeApiTestCase(unittest.TestCase):

    def config(self, **changes):
        path = write_json_file(dict(PWA_CONFIG, **changes))
        self.addCleanup(remove, path)
        return path

    def run_main(self, argv):
        full_argv = ['appdome_api.py', '--api_key', API_KEY, '--team_id', TEAM_ID] + argv
        with mock.patch.object(sys, 'argv', full_argv), mock.patch.dict('os.environ', {}, clear=False):
            appdome_api.main()

    def patch_steps(self):
        steps = {}
        for name in ('pwa_build', '_upload', '_build', '_context', '_sign', '_download_file', 'download_action',
                     '_get_obfuscation_map_status'):
            patcher = mock.patch(f'appdome_api.{name}')
            steps[name] = patcher.start()
            self.addCleanup(patcher.stop)
        steps['pwa_build'].return_value = BUILD
        steps['_build'].return_value = TASK_ID
        steps['_get_obfuscation_map_status'].return_value = False
        return steps


class TestPwaOption(AppdomeApiTestCase):

    def test_pwa_flow_replaces_upload_and_build(self):
        steps = self.patch_steps()
        order = mock.Mock()
        for name in ('pwa_build', '_context', '_sign', '_download_file'):
            order.attach_mock(steps[name], name)

        self.run_main(['--pwa', self.config()] + ANDROID_SIGNING +
                      ['--new_version', '2.0', '--output', 'out.aab', '--certificate_output', 'cert.pdf'])

        self.assertEqual([c[0] for c in order.mock_calls],
                         ['pwa_build', '_context', '_sign', '_download_file', '_download_file'])
        steps['pwa_build'].assert_called_once_with(API_KEY, TEAM_ID, PWA_CONFIG, wait=True, workflow_output_logs=None)
        steps['_upload'].assert_not_called()
        steps['_build'].assert_not_called()
        self.assertEqual(steps['_context'].call_args[0][2], TASK_ID)
        self.assertEqual(steps['_context'].call_args[0][5], '2.0')
        self.assertEqual(steps['_sign'].call_args[0][1:3], (Platform.ANDROID, TASK_ID))
        self.assertEqual(steps['_download_file'].call_args_list[0][0][2:4], (TASK_ID, 'out.aab'))

    def test_ipa_maps_to_ios_signing_and_sends_profile(self):
        steps = self.patch_steps()
        profile = write_binary_file(b'profile')
        self.addCleanup(remove, profile)
        self.run_main(['--pwa', self.config(pwa_platform='ipa'), '--sign_on_appdome', '--keystore', 'c.p12',
                       '--keystore_pass', 'p', '--provisioning_profiles', profile])
        self.assertEqual(steps['_sign'].call_args[0][1], Platform.IOS)
        sent = steps['pwa_build'].call_args[0][2]['overrides']['provisioning_profile']
        self.assertEqual(sent, [{'filename': profile.split('/')[-1], 'content': base64.b64encode(b'profile').decode()}])

    def test_ipa_without_profiles_rejected_before_upload(self):
        steps = self.patch_steps()
        with mock.patch.dict('os.environ', {'IOS_MOBILEPROVISION_1': ''}):
            with self.assertRaises(Exception) as ctx:
                self.run_main(['--pwa', self.config(pwa_platform='ipa'), '--sign_on_appdome', '--keystore', 'c.p12',
                               '--keystore_pass', 'p'])
        self.assertIn('Provisioning profiles must be specified', str(ctx.exception))
        steps['pwa_build'].assert_not_called()

    def test_pwa_does_not_require_fusion_set(self):
        steps = self.patch_steps()
        with mock.patch.dict('os.environ', {'APPDOME_ANDROID_FS_ID': ''}):
            self.run_main(['--pwa', self.config()] + ANDROID_SIGNING)
        steps['pwa_build'].assert_called_once()

    def test_build_args_rejected_with_pwa(self):
        steps = self.patch_steps()
        with self.assertRaises(Exception) as ctx:
            self.run_main(['--pwa', self.config(), '--baseline_profile', 'b.txt', '--direct_upload']
                          + ANDROID_SIGNING)
        self.assertIn('--baseline_profile, --direct_upload cannot be used with --pwa', str(ctx.exception))
        steps['pwa_build'].assert_not_called()

    def test_diagnostic_logs_flag_sets_extended_logs(self):
        steps = self.patch_steps()
        self.run_main(['--pwa', self.config(), '-bl'] + ANDROID_SIGNING)
        sent_config = steps['pwa_build'].call_args[0][2]
        self.assertEqual(sent_config['overrides'], {'extended_logs': True})

    def test_build_overrides_merged_into_pwa_overrides(self):
        steps = self.patch_steps()
        overrides_path = write_json_file({'from_file': 1, 'shared': 'file'})
        self.addCleanup(remove, overrides_path)
        self.run_main(['--pwa', self.config(overrides={'from_config': 1, 'shared': 'config'}),
                       '--build_overrides', overrides_path, '--diagnostic_logs'] + ANDROID_SIGNING)
        sent_config = steps['pwa_build'].call_args[0][2]
        self.assertEqual(sent_config['overrides'],
                         {'from_config': 1, 'from_file': 1, 'shared': 'file', 'extended_logs': True})

    def test_no_overrides_sent_when_none_given(self):
        steps = self.patch_steps()
        self.run_main(['--pwa', self.config()] + ANDROID_SIGNING)
        self.assertNotIn('overrides', steps['pwa_build'].call_args[0][2])

    def test_both_platform_rejected_before_upload(self):
        steps = self.patch_steps()
        with self.assertRaises(Exception) as ctx:
            self.run_main(['--pwa', self.config(pwa_platform='both')] + ANDROID_SIGNING)
        self.assertIn('Supported values: aab, ipa', str(ctx.exception))
        steps['pwa_build'].assert_not_called()

    def test_missing_signing_credentials_rejected_before_upload(self):
        steps = self.patch_steps()
        with mock.patch.dict('os.environ', {'ANDROID_KEYSTORE_ALIAS': '', 'ANDROID_KEY_PASS': ''}):
            with self.assertRaises(Exception) as ctx:
                self.run_main(['--pwa', self.config(), '--sign_on_appdome', '--keystore', 'k.keystore',
                               '--keystore_pass', 'kp'])
        self.assertIn('All Android signing credentials', str(ctx.exception))
        steps['pwa_build'].assert_not_called()

    def test_pwa_and_app_are_mutually_exclusive(self):
        with mock.patch('sys.stderr'), self.assertRaises(SystemExit):
            self.run_main(['--pwa', self.config(), '--app', 'app.aab'] + ANDROID_SIGNING)

    def test_multiple_builds_rejected(self):
        steps = self.patch_steps()
        steps['pwa_build'].return_value = BUILD * 2
        with self.assertRaises(Exception) as ctx:
            self.run_main(['--pwa', self.config()] + ANDROID_SIGNING)
        self.assertIn('Expected a single PWA upload', str(ctx.exception))
        steps['_context'].assert_not_called()


class TestPwaShortFlow(AppdomeApiTestCase):
    """Short Flow accounts build automatically; others upload only and build with a Fusion Set."""

    def test_short_flow_ignores_fusion_set_and_does_not_rebuild(self):
        steps = self.patch_steps()
        with self.assertLogs(level='WARNING') as logs:
            self.run_main(['--pwa', self.config(), '--fusion_set_id', FUSION_SET_ID] + ANDROID_SIGNING)
        steps['_build'].assert_not_called()
        self.assertEqual(steps['_sign'].call_args[0][2], TASK_ID)
        self.assertIn('was not used: Short Flow', '\n'.join(logs.output))

    def test_upload_only_builds_with_fusion_set(self):
        steps = self.patch_steps()
        steps['pwa_build'].return_value = UPLOAD_ONLY
        steps['_build'].return_value = BUILT_TASK_ID
        overrides_path = write_json_file({'k': 1})
        self.addCleanup(remove, overrides_path)
        self.run_main(['--pwa', self.config(), '--fusion_set_id', FUSION_SET_ID, '-bl',
                       '--build_overrides', overrides_path] + ANDROID_SIGNING)
        self.assertEqual(steps['_build'].call_args[0][2:6], (APP_ID, FUSION_SET_ID, overrides_path, True))
        self.assertEqual(steps['_context'].call_args[0][2], BUILT_TASK_ID)
        self.assertEqual(steps['_sign'].call_args[0][2], BUILT_TASK_ID)

    def test_upload_only_uses_platform_fusion_set_env(self):
        steps = self.patch_steps()
        steps['pwa_build'].return_value = UPLOAD_ONLY
        with mock.patch.dict('os.environ', {'APPDOME_ANDROID_FS_ID': FUSION_SET_ID}):
            self.run_main(['--pwa', self.config()] + ANDROID_SIGNING)
        self.assertEqual(steps['_build'].call_args[0][3], FUSION_SET_ID)

    def test_upload_only_without_fusion_set_reports_app_id(self):
        steps = self.patch_steps()
        steps['pwa_build'].return_value = UPLOAD_ONLY
        with mock.patch.dict('os.environ', {'APPDOME_ANDROID_FS_ID': ''}):
            with self.assertRaises(Exception) as ctx:
                self.run_main(['--pwa', self.config()] + ANDROID_SIGNING)
        self.assertIn(f'App ID: {APP_ID}', str(ctx.exception))
        self.assertIn(f'--app_id {APP_ID} --fusion_set_id', str(ctx.exception))
        steps['_build'].assert_not_called()
        steps['_sign'].assert_not_called()

    def test_invalid_fusion_set_rejected_before_upload(self):
        steps = self.patch_steps()
        with mock.patch('sys.stderr'), self.assertRaises((Exception, SystemExit)):
            self.run_main(['--pwa', self.config(), '--fusion_set_id', 'not-a-uuid'] + ANDROID_SIGNING)
        steps['pwa_build'].assert_not_called()


class TestMobileFlowUnchanged(AppdomeApiTestCase):

    def test_app_flow_still_uploads_and_builds(self):
        steps = self.patch_steps()
        steps['_upload'].return_value = APP_ID
        self.run_main(['--app', 'app.aab', '--fusion_set_id', FUSION_SET_ID] + ANDROID_SIGNING)
        steps['pwa_build'].assert_not_called()
        steps['_upload'].assert_called_once()
        self.assertEqual(steps['_build'].call_args[0][2:4], (APP_ID, FUSION_SET_ID))
        self.assertEqual(steps['_sign'].call_args[0][1:3], (Platform.ANDROID, TASK_ID))

    def test_app_flow_still_requires_fusion_set(self):
        self.patch_steps()
        with mock.patch.dict('os.environ', {'APPDOME_ANDROID_FS_ID': ''}):
            with self.assertRaises(Exception) as ctx:
                self.run_main(['--app', 'app.aab'] + ANDROID_SIGNING)
        self.assertIn('Fusion Set ID must be specified', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
