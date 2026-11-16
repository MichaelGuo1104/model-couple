"""External prompt configuration; no paid provider calls."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ai_gateway
from ai_gateway import AIError, Gateway, load_prompts


class PromptTests(unittest.TestCase):
    def test_all_tasks_use_json_and_reload_without_restart(self):
        original = load_prompts()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'prompts.json'
            config = Path(tmp) / 'config.json'
            config.write_text(json.dumps({'base_url': 'https://provider.example/v1',
                'model': 'test', 'api_key': 'test-key', 'timeout_seconds': 5}), encoding='utf-8')
            gateway = Gateway(config)
            for kind in sorted(ai_gateway.PROMPT_KINDS):
                prompts = json.loads(json.dumps(original))
                prompts['system'][kind] = 'external prompt: ' + kind
                prompts['example_text']['prefix'] = '\nexternal example: '
                prompts['example_text']['reply_to_target'] = 'external reply'
                path.write_text(json.dumps(prompts, ensure_ascii=False), encoding='utf-8-sig')
                task = {'kind': kind}
                if kind in {'notice', 'result', 'off_topic', 'thread', 'comment'}:
                    task['personas'] = [{'nickname': n} for n in ['甲', '乙', '丙']]
                raw = json.dumps({'choices': [{'message': {'content': '{}'}}]}).encode()
                with patch.object(ai_gateway, 'PROMPTS_PATH', path), patch('urllib.request.build_opener') as opener:
                    opener.return_value.open.return_value = io.BytesIO(raw)
                    with patch('sys.stdout', io.StringIO()):
                        self.assertEqual(gateway.generate(task), {})
                messages = json.loads(opener.return_value.open.call_args.args[0].data)['messages']
                self.assertTrue(messages[0]['content'].startswith('external prompt: ' + kind))
                self.assertEqual(json.loads(messages[1]['content']), task)
                if 'personas' in task:
                    self.assertIn('external example: ', messages[0]['content'])
                if kind in {'thread', 'comment'}:
                    self.assertIn('external reply', messages[0]['content'])

    def test_invalid_or_missing_prompts_fail_before_http(self):
        original = load_prompts()
        missing_kind = json.loads(json.dumps(original))
        missing_kind['system'].pop('notice')
        wrong_type = json.loads(json.dumps(original))
        wrong_type['example_text']['prefix'] = []
        empty = json.loads(json.dumps(original))
        empty['system']['notice'] = '  '
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'prompts.json'
            gateway = Gateway()
            gateway.config = {'api_key': 'test-key'}
            for value in [None, '{invalid-private-content', '[]', json.dumps(missing_kind),
                          json.dumps(wrong_type), json.dumps(empty)]:
                if value is not None:
                    path.write_text(value, encoding='utf-8')
                with patch.object(ai_gateway, 'PROMPTS_PATH', path), patch('urllib.request.build_opener') as opener:
                    with self.assertRaisesRegex(AIError, 'Invalid AI prompts configuration') as error:
                        gateway.generate({'kind': 'thread'})
                    opener.assert_not_called()
                    self.assertNotIn('private-content', str(error.exception))

    def test_couple_notice_prompt_respects_public_only_notification_stage(self):
        notice = load_prompts()['system']['notice']
        for phrase in ['优秀情侣奖', '2025年公告日程', '双方分别自愿', '公开展示另行授权', '个人学业', '参评理由']:
            self.assertIn(phrase, notice)

    def test_notice_prompt_distinguishes_empty_history_from_required_output(self):
        notice = load_prompts()['system']['notice']
        for phrase in ['恰好3个threads', '没有历史也必须新写', '恰好2条comments', '不得空数组']:
            self.assertIn(phrase, notice)
        self.assertNotIn('根字段仅threads（notice/result）或comments（其他）', notice)

    def test_mock_does_not_require_prompt_file(self):
        with patch.object(ai_gateway, 'PROMPTS_PATH', Path('missing-prompts.json')):
            result = Gateway(mock=True).generate({'kind': 'thread', 'personas': [{'nickname': '甲'}]})
            self.assertIn('comments', result)

    def test_default_path_does_not_depend_on_working_directory(self):
        self.assertEqual(ai_gateway.PROMPTS_PATH, Path(ai_gateway.__file__).resolve().with_name('ai_prompts.json'))
        self.assertEqual(set(load_prompts()['system']), ai_gateway.PROMPT_KINDS)


if __name__ == '__main__':
    unittest.main()
