"""提示词加载、同步路由及全部作者分支；不读取配置、不访问模型。"""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import author
import prompt_catalog as catalog
import student_server


class PromptCatalogTests(unittest.TestCase):
    def test_valid_and_live_reload(self):
        data = catalog.load_catalog()
        self.assertEqual(len(data['foundry']['schemas']), 11)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'prompts.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            with patch.object(catalog, 'CATALOG_PATH', path):
                first = catalog.load_catalog()
                data['author']['templates']['rule_1'] = '已修改的规则'
                path.write_text(json.dumps(data), encoding='utf-8')
                self.assertNotEqual(first, catalog.load_catalog())

    def test_invalid_catalogs_fail_explicitly(self):
        data = catalog.load_catalog()
        mutations = []
        value = copy.deepcopy(data); del value['foundry']['templates']['calendar']; mutations.append(value)
        value = copy.deepcopy(data); value['foundry']['templates']['cupidPrompt_0'] = '{{unknown}}'; mutations.append(value)
        value = copy.deepcopy(data); del value['author']['schemas']['SCRIPT_SCHEMA']['scenes']; mutations.append(value)
        value = copy.deepcopy(data); value['author']['schemas']['REVIEW_SCHEMA']['approved'] = 'false'; mutations.append(value)
        value = copy.deepcopy(data); value['author']['templates']['rule_0'] = ''; mutations.append(value)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'prompts.json'
            with self.assertRaisesRegex(ValueError, 'prompts.json 加载失败'):
                catalog.load_catalog(path)
            for text in ['{', '{"foundry":{},"foundry":{}}', *[json.dumps(x) for x in mutations]]:
                path.write_text(text, encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'prompts.json 加载失败'):
                    catalog.load_catalog(path)

    def test_fixed_route_bootstrap_and_error(self):
        # 直接调用handler，不启动服务，不读取任何API配置。
        handler = student_server.Handler.__new__(student_server.Handler)
        handler.server = SimpleNamespace(server_port=8765)
        handler.headers = {'Host': '127.0.0.1:8765'}
        handler.path = '/creation/prompts.js'
        replies = []
        handler.reply = lambda *args: replies.append(args)
        handler.do_GET()
        self.assertEqual(replies[-1][0], 200)
        self.assertEqual(replies[-1][2], 'text/javascript; charset=utf-8')
        self.assertTrue(replies[-1][1].startswith(b'globalThis.CREATION_PROMPTS='))
        with patch.object(catalog, 'CATALOG_PATH', Path('missing-prompts-test.json')):
            handler.do_GET()
        self.assertEqual(replies[-1][0], 200)
        self.assertEqual(replies[-1][2], 'text/javascript; charset=utf-8')
        self.assertIn(b'CREATION_PROMPTS_ERROR=', replies[-1][1])
        self.assertIn(b'prompts.json', replies[-1][1])
        handler.do_GET()
        self.assertTrue(replies[-1][1].startswith(b'globalThis.CREATION_PROMPTS='))
        self.assertNotIn(b'CREATION_PROMPTS_ERROR', replies[-1][1])
        handler.headers = {'Host': 'evil.invalid'}
        handler.do_GET(); self.assertEqual(replies[-1][0], 403)
        html = Path(__file__).with_name('student-foundry.html').read_text(encoding='utf-8')
        self.assertLess(html.index('<script src="/creation/prompts.js">'), html.index('<script>'))

    def test_bootstrap_escapes_script_data(self):
        data = catalog.load_catalog()
        data['foundry']['templates']['calendar'] = '</script><script>恶意文本</script>\u2028'
        with patch.object(catalog, 'load_catalog', return_value=data):
            script = catalog.javascript_bootstrap()
        self.assertNotIn(b'</script>', script)
        self.assertIn(b'\\u003c', script)
        self.assertIn(b'\\u2028', script)

    def test_muse_defense_not_couple_scoring(self):
        templates = catalog.load_catalog()['author']['templates']
        for phrase in ('高校优秀情侣奖答辩', '双人陈述', '学业、科研、竞赛、社会工作、志愿、文体', '不强制所有指标', '不套全能模板', '不制定评分框架', '评价交给玩家', '编造宣传情节', 'allowed_source_refs'):
            self.assertIn(phrase, templates['rule_5'])
        for phrase in ('答辩可用性', '台词分工', '不给情侣评分', '不得把其他阶段的事实审查标准套用到剧本'):
            self.assertIn(phrase, templates['rule_2'])
        self.assertIn('现场未来只有学生，不存在Critic', templates['rule_6'])

    def test_all_author_branches_and_revision_context(self):
        data = catalog.load_catalog()
        p = {'setting': {'students': []}, 'members': ['s1', 's2'], 'announcement': {}, 'game_snapshot': {'player_visible': {'application': {}}}, 'results': {'chronos': {}, 'script': {'title': '标题', 'characters': [], 'scenes': []}}, 'draft': None}
        with patch.object(author, 'own_sources', side_effect=lambda p, sid: {'own.initial_memories.0': sid}), patch.object(author, 'muse_sources', return_value={'safe': {'text': '获准内容', 'may_write': True, 'may_perform': True}}):
            for stage in author.STAGES:
                for reviewing in (False, True):
                    for revision in (False, True):
                        current = copy.deepcopy(p)
                        if revision:
                            current.update(draft={'revision': True}, last_review={'issues': ['补充']}, failure={'message': '本地校验反馈'})
                        t = {'stage': stage, 'student_id': 's1' if stage in ('disclosure', 'attitude') else None, 'agent': ('C_' if reviewing else '') + author.AGENTS[stage], 'reviewing': reviewing}
                        messages = author.messages(current, t)
                        system, payload = messages[0]['content'], json.loads(messages[1]['content'])
                        self.assertIn(t['agent'], system)
                        expected = data['author']['schemas']['REVIEW_SCHEMA' if reviewing else stage.upper() + '_SCHEMA']
                        self.assertTrue(system.endswith(json.dumps(expected, ensure_ascii=False)))
                        if reviewing: self.assertEqual(payload['candidate'], current['draft'])
                        elif revision: self.assertEqual(payload['revision_requests'], current['last_review'])
                        if revision: self.assertEqual(payload['validation_feedback'], '本地校验反馈')
                        if stage in ('disclosure', 'attitude'): self.assertEqual(payload['sources']['own.initial_memories.0'], 's1')


if __name__ == '__main__':
    unittest.main()
