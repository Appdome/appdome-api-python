import base64
import json
import logging
import sys
import unittest
from os import remove
from unittest import mock

from pwa_test_utils import (API_KEY, TEAM_ID, APP_ID, TASK_ID, PWA_UPLOAD_RESPONSE, PWA_UPLOAD_ONLY_RESPONSE,
                            PWA_CONFIG, fake_response, write_json_file, write_binary_file)

import pwa_upload  # noqa: E402
from utils import SERVER_API_V1_URL  # noqa: E402


class TestPwaConfig(unittest.TestCase):

    def load(self, content):
        path = write_json_file(content)
        self.addCleanup(remove, path)
        return pwa_upload.init_pwa_config(path)

    def test_valid_config(self):
        config = dict(PWA_CONFIG, overrides={'some_key': True})
        self.assertEqual(self.load(config), config)

    def test_missing_required_keys(self):
        with self.assertRaises(Exception) as ctx:
            self.load({'pwa_app_name': 'My PWA'})
        self.assertIn('pwa_address, pwa_platform', str(ctx.exception))

    def test_unknown_keys(self):
        with self.assertRaises(Exception) as ctx:
            self.load(dict(PWA_CONFIG, fusion_set_id='x'))
        self.assertIn('Unknown keys in PWA config file: fusion_set_id', str(ctx.exception))

    def test_invalid_json(self):
        with self.assertRaises(Exception) as ctx:
            self.load('{not json')
        self.assertIn('invalid JSON', str(ctx.exception))

    def test_platform_limited_to_aab_or_ipa(self):
        self.assertEqual(self.load(dict(PWA_CONFIG, pwa_platform='IPA'))['pwa_platform'], 'ipa')
        for value in ('android', 'ios', 'both'):
            with self.subTest(value=value), self.assertRaises(Exception) as ctx:
                self.load(dict(PWA_CONFIG, pwa_platform=value))
            self.assertIn('Supported values: aab, ipa', str(ctx.exception))

    def test_non_object_json(self):
        with self.assertRaises(Exception):
            self.load([PWA_CONFIG])


class TestPwaUploadRequest(unittest.TestCase):

    def test_url_points_to_pwappload(self):
        self.assertEqual(pwa_upload.PWA_UPLOAD_URL, f"{SERVER_API_V1_URL}/pwappload")

    @mock.patch('pwa_upload.requests.post')
    def test_posts_json_payload_with_team_and_auth(self, mock_post):
        mock_post.return_value = fake_response(json_body=PWA_UPLOAD_RESPONSE)
        pwa_upload.pwa_upload(API_KEY, TEAM_ID, dict(PWA_CONFIG, overrides={'some_key': True}))

        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], pwa_upload.PWA_UPLOAD_URL)
        self.assertEqual(kwargs['params'], {'team_id': TEAM_ID})
        self.assertEqual(kwargs['headers']['Authorization'], API_KEY)
        self.assertEqual(kwargs['headers']['Content-Type'], 'application/json')
        self.assertEqual(kwargs['json'], dict(PWA_CONFIG, overrides={'some_key': True}))
        self.assertNotIn('files', kwargs)

    @mock.patch('pwa_upload.requests.post')
    def test_empty_fields_omitted_and_string_overrides_sent_as_object(self, mock_post):
        mock_post.return_value = fake_response(json_body=PWA_UPLOAD_RESPONSE)
        pwa_upload.pwa_upload(API_KEY, None, dict(PWA_CONFIG, pwa_app_name='', overrides='{"a": 1}'))

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json'], {'pwa_address': 'https://example.com', 'pwa_platform': 'aab',
                                          'overrides': {'a': 1}})
        self.assertEqual(kwargs['params'], {})

    @mock.patch('pwa_upload.requests.post')
    def test_empty_overrides_not_sent(self, mock_post):
        mock_post.return_value = fake_response(json_body=PWA_UPLOAD_RESPONSE)
        pwa_upload.pwa_upload(API_KEY, TEAM_ID, dict(PWA_CONFIG, overrides={}))
        self.assertNotIn('overrides', mock_post.call_args[1]['json'])

    @mock.patch('pwa_upload.requests.post')
    def test_invalid_string_overrides_raise(self, mock_post):
        with self.assertRaises(Exception) as ctx:
            pwa_upload.pwa_upload(API_KEY, TEAM_ID, dict(PWA_CONFIG, overrides='{bad'))
        self.assertIn("'overrides' is not valid JSON", str(ctx.exception))
        mock_post.assert_not_called()


class TestParseResponse(unittest.TestCase):

    def test_observed_list_response(self):
        builds = pwa_upload.parse_pwa_upload_response(fake_response(json_body=PWA_UPLOAD_RESPONSE))
        self.assertEqual(builds, [{'app_id': APP_ID, 'task_id': TASK_ID, 'pack_type': 'aab', 'status': 'active'}])

    def test_upload_only_response_without_task(self):
        uploads = pwa_upload.parse_pwa_upload_response(fake_response(json_body=PWA_UPLOAD_ONLY_RESPONSE))
        self.assertEqual(uploads, [{'app_id': APP_ID, 'task_id': None, 'pack_type': 'aab', 'status': 'active'}])

    def test_multiple_platforms(self):
        second = {"app": {"id": "app-2", "pack_type": "ipa"}, "taskId": {"task_id": "task-2"}}
        builds = pwa_upload.parse_pwa_upload_response(fake_response(json_body=PWA_UPLOAD_RESPONSE + [second]))
        self.assertEqual([b['task_id'] for b in builds], [TASK_ID, 'task-2'])

    def test_documented_object_response(self):
        builds = pwa_upload.parse_pwa_upload_response(fake_response(json_body={'task_id': TASK_ID}))
        self.assertEqual(builds, [{'app_id': None, 'task_id': TASK_ID, 'pack_type': None, 'status': None}])

    def test_invalid_responses_raise(self):
        for body in ({'unexpected': 'value'}, [], [{'app': {}}], ['x']):
            with self.subTest(body=body):
                with self.assertRaises(Exception) as ctx:
                    pwa_upload.parse_pwa_upload_response(fake_response(json_body=body))
                self.assertIn('Error in PWA upload response', str(ctx.exception))

    def test_non_json_response_raises(self):
        with self.assertRaises(Exception) as ctx:
            pwa_upload.parse_pwa_upload_response(fake_response(text='<html>not json</html>'))
        self.assertIn('Error in PWA upload response', str(ctx.exception))


class TestPwaBuild(unittest.TestCase):

    @mock.patch('pwa_upload.wait_for_status_complete')
    @mock.patch('pwa_upload.requests.post')
    def test_returns_builds_without_waiting(self, mock_post, mock_wait):
        mock_post.return_value = fake_response(json_body=PWA_UPLOAD_RESPONSE)
        builds = pwa_upload.pwa_build(API_KEY, TEAM_ID, PWA_CONFIG)
        self.assertEqual(builds[0]['task_id'], TASK_ID)
        mock_wait.assert_not_called()

    @mock.patch('pwa_upload.wait_for_status_complete')
    @mock.patch('pwa_upload.requests.post')
    def test_wait_polls_build_task_status(self, mock_post, mock_wait):
        mock_post.return_value = fake_response(json_body=PWA_UPLOAD_RESPONSE)
        pwa_upload.pwa_build(API_KEY, TEAM_ID, PWA_CONFIG, wait=True, workflow_output_logs='logs.txt')
        mock_wait.assert_called_once_with(API_KEY, TEAM_ID, TASK_ID, operation='build',
                                          workflow_output_logs_path='logs.txt')

    @mock.patch('pwa_upload.wait_for_status_complete')
    @mock.patch('pwa_upload.requests.post')
    def test_upload_only_does_not_wait(self, mock_post, mock_wait):
        mock_post.return_value = fake_response(json_body=PWA_UPLOAD_ONLY_RESPONSE)
        uploads = pwa_upload.pwa_build(API_KEY, TEAM_ID, PWA_CONFIG, wait=True)
        self.assertEqual((uploads[0]['app_id'], uploads[0]['task_id']), (APP_ID, None))
        mock_wait.assert_not_called()

    @mock.patch('pwa_upload.wait_for_status_complete')
    @mock.patch('pwa_upload.requests.post')
    def test_error_status_code_raises(self, mock_post, mock_wait):
        for status_code in (400, 401, 415, 429, 500):
            with self.subTest(status_code=status_code):
                mock_post.return_value = fake_response(status_code, text='error')
                with self.assertRaises(Exception) as ctx:
                    pwa_upload.pwa_build(API_KEY, TEAM_ID, PWA_CONFIG)
                self.assertIn(f'Status Code: {status_code}', str(ctx.exception))
        mock_wait.assert_not_called()


class TestIosProvisioningProfiles(unittest.TestCase):

    def profile(self, content=b'profile-bytes'):
        path = write_binary_file(content)
        self.addCleanup(remove, path)
        return path

    def test_ipa_adds_base64_profiles_to_overrides(self):
        path = self.profile()
        config = pwa_upload.add_pwa_provisioning_profiles(dict(PWA_CONFIG, pwa_platform='ipa'), [path])
        self.assertEqual(config['overrides'], {'provisioning_profile': [
            {'filename': path.split('/')[-1], 'content': base64.b64encode(b'profile-bytes').decode()}]})

    def test_ipa_keeps_existing_overrides_and_supports_multiple_profiles(self):
        paths = [self.profile(b'a'), self.profile(b'b')]
        config = dict(PWA_CONFIG, pwa_platform='ipa', overrides={'extended_logs': True})
        config = pwa_upload.add_pwa_provisioning_profiles(config, paths)
        self.assertTrue(config['overrides']['extended_logs'])
        self.assertEqual(len(config['overrides']['provisioning_profile']), 2)

    def test_ipa_accepts_profiles_already_in_config(self):
        profiles = [{'filename': 'X.mobileprovision', 'content': 'QUJD'}]
        config = dict(PWA_CONFIG, pwa_platform='ipa', overrides={'provisioning_profile': profiles})
        self.assertEqual(pwa_upload.add_pwa_provisioning_profiles(config, None)['overrides']['provisioning_profile'],
                         profiles)

    def test_ipa_without_profiles_rejected(self):
        with self.assertRaises(Exception) as ctx:
            pwa_upload.add_pwa_provisioning_profiles(dict(PWA_CONFIG, pwa_platform='ipa'), [])
        self.assertIn('requires provisioning profiles', str(ctx.exception))

    def test_aab_unchanged(self):
        self.assertEqual(pwa_upload.add_pwa_provisioning_profiles(dict(PWA_CONFIG), [self.profile()]), PWA_CONFIG)

    @mock.patch('pwa_upload.requests.post')
    def test_profile_sent_in_json_body_but_not_debug_logged(self, mock_post):
        mock_post.return_value = fake_response(json_body=PWA_UPLOAD_RESPONSE)
        config = pwa_upload.add_pwa_provisioning_profiles(dict(PWA_CONFIG, pwa_platform='ipa'),
                                                          [self.profile(b'x' * 300)])
        with self.assertLogs(level=logging.DEBUG) as logs:
            pwa_upload.pwa_upload(API_KEY, TEAM_ID, config)
        sent = mock_post.call_args.kwargs['json']['overrides']['provisioning_profile'][0]['content']
        self.assertEqual(sent, base64.b64encode(b'x' * 300).decode())
        self.assertNotIn(sent, '\n'.join(logs.output))


class TestPwaCli(unittest.TestCase):

    def test_pwa_config_is_required(self):
        with mock.patch.object(sys, 'argv', ['pwa_upload.py', '--api_key', API_KEY]):
            with self.assertRaises(SystemExit), mock.patch('sys.stderr'):
                pwa_upload.parse_arguments()

    @mock.patch('pwa_upload.download_action')
    @mock.patch('pwa_upload.pwa_build', return_value=[{'app_id': APP_ID, 'task_id': TASK_ID, 'pack_type': 'aab'}])
    def test_output_implies_wait_and_downloads(self, mock_build, mock_download):
        config_path = write_json_file(PWA_CONFIG)
        self.addCleanup(remove, config_path)
        argv = ['pwa_upload.py', '--api_key', API_KEY, '--team_id', TEAM_ID, '--pwa_config', config_path,
                '--output', 'out.aab']
        with mock.patch.object(sys, 'argv', argv), mock.patch('builtins.print'):
            pwa_upload.main()
        mock_build.assert_called_once_with(API_KEY, TEAM_ID, PWA_CONFIG, wait=True)
        mock_download.assert_called_once_with(API_KEY, TEAM_ID, TASK_ID, 'out.aab', None)

    @mock.patch('pwa_upload.download_action')
    @mock.patch('pwa_upload.pwa_build', return_value=[{'app_id': APP_ID, 'task_id': None, 'pack_type': 'aab'}])
    def test_output_without_automatic_build_explains_next_step(self, mock_build, mock_download):
        config_path = write_json_file(PWA_CONFIG)
        self.addCleanup(remove, config_path)
        argv = ['pwa_upload.py', '--api_key', API_KEY, '--pwa_config', config_path, '--output', 'out.aab']
        with mock.patch.object(sys, 'argv', argv), mock.patch('builtins.print'), \
                self.assertRaises(Exception) as ctx:
            pwa_upload.main()
        self.assertIn(f'Build App ID {APP_ID} with a Fusion Set', str(ctx.exception))
        mock_download.assert_not_called()


if __name__ == '__main__':
    unittest.main()
