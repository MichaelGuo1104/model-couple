"""仅临时目录、临时HTTP端口和固定模拟，不访问真实模型或写用户配置。"""
import copy
import hashlib
import http.client
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/'creation'))
import runtime
import student_server as server


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result=subprocess.run(['node',str(HERE/'test_runtime.cjs'),'--fixture'],capture_output=True,text=True,encoding='utf-8',check=True)
        cls.fixture=json.loads(result.stdout)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.engine=runtime.Engine(Path(self.temp.name)/'sessions')

    def tearDown(self):
        self.temp.cleanup()

    def create(self,api=False,rounds=2):
        setting=copy.deepcopy(self.fixture)
        if api: setting['mode']='api'
        return self.engine.create(setting,'c1','api' if api else 'demo',rounds)

    def submitted_ready(self):
        s = self.counseling()
        self.teacher(s['session_id'])
        self.engine.step(s['session_id'], lambda _: self.draft_output('share_draft', '甲已分享提交正文'))
        return self.engine.step(s['session_id'], lambda _: self.draft_output('share_draft', '乙已分享提交正文'))

    def submit(self, s):
        return self.engine.dispatch('submit_application', {'session_id': s['session_id'],
            'candidate_token': self.engine.view(s)['application_candidate_token'], 'both_authorized': True}, None)

    def test_submission_gate_and_payload(self):
        s = self.create()
        for version in (1, True, '1', 0):
            with self.assertRaises(ValueError): self.engine.export_game(s['session_id'], version)
        with self.assertRaises(ValueError): self.submit(s)
        s = self.counseling()
        with self.assertRaises(ValueError): self.submit(s)
        self.teacher(s['session_id'])
        s = self.engine.step(s['session_id'], lambda _: self.draft_output('share_draft'))
        with self.assertRaises(ValueError): self.submit(s)
        s = self.engine.step(s['session_id'], lambda _: self.draft_output())
        with self.assertRaises(ValueError): self.submit(s)
        s = self.submitted_ready()
        token = self.engine.view(s)['application_candidate_token']
        for mutate in (lambda d: d.update(both_authorized=False), lambda d: d.update(actor='student'),
                       lambda d: d.update(candidate_token='stale'), lambda d: d.update(both_authorized='true')):
            data = {'session_id': s['session_id'], 'candidate_token': token, 'both_authorized': True}; mutate(data)
            with self.assertRaises(ValueError): self.engine.dispatch('submit_application', data, None)
        self.assertEqual(self.engine.load(s['session_id'])['submitted_versions'], [])
        original = copy.deepcopy(s)
        s['statements']['s1']['text'] = '并发改稿'
        s['statements']['s1']['versions'].append({'version': 2, 'text': '并发改稿', 'shared': True})
        self.engine.save(s)
        with self.assertRaisesRegex(ValueError, '已变化'):
            self.engine.submit_application(s['session_id'], token, True)
        s = original
        s['conversation'][-1]['decision_confirmation'] = 'withdraw'; self.engine.save(s)
        with self.assertRaises(ValueError): self.submit(s)
        s = original; s['status'] = 'stopped'; self.engine.save(s)
        with self.assertRaises(ValueError): self.submit(s)

    def test_submission_snapshot_versions_and_privacy(self):
        s = self.submitted_ready(); sid = s['session_id']
        s['private_states']['s1']['reason'] = '私有意愿不导出哨兵'
        s['conversation'][-1]['speech'] = '完整会话不导出哨兵'
        s['statements']['s1']['versions'].insert(0, {'version': 0, 'text': '旧未分享稿不导出哨兵'})
        s['setting']['takeover_packages'][0]['private_information'][0]['text'] = '本人扮演秘密'
        s['config'] = {'key': '密钥不导出哨兵'}
        self.engine.save(s)
        first = self.submit(s)
        self.assertEqual(len(first['submitted_versions']), 1)
        self.assertNotIn('role_private', json.dumps(first))
        exported = self.engine.dispatch('export_game', {'session_id': sid, 'version': 1}, None)
        self.assertEqual(exported['submission']['actor'], 'operator')
        self.assertEqual(exported['submission']['submitted_at_story'], '2025-04-24')
        self.assertEqual(set(exported['role_private']['takeover_by_student_id']), {'s1', 's2'})
        raw = json.dumps(exported, ensure_ascii=False)
        for secret in ('私有意愿不导出哨兵', '完整会话不导出哨兵', '旧未分享稿不导出哨兵', '密钥不导出哨兵', 'review_status', 'source_refs'):
            self.assertNotIn(secret, raw)
        self.assertIn('本人扮演秘密', raw)
        self.assertNotIn('本人扮演秘密', json.dumps(exported['player_visible'], ensure_ascii=False))
        self.assertEqual(exported['player_visible']['application']['pages'][0]['fields']['学号'], '待补充')
        stored = self.engine.load(sid)
        stored['statements']['s1']['text'] = '后来未分享新稿'
        stored['setting']['students'][0]['name'] = '后来改人设'
        self.engine.save(stored)
        self.assertEqual(self.engine.export_game(sid, 1), exported)
        with self.assertRaises(ValueError): self.submit(stored)
        stored['statements']['s1']['versions'].append({'version': 2, 'text': '后来未分享新稿', 'shared': True})
        self.engine.save(stored)
        second = self.submit(stored)
        self.assertEqual([v['version'] for v in second['submitted_versions']], [1, 2])
        self.assertEqual(self.engine.export_game(sid, 1), exported)
        self.assertEqual(self.engine.export_game(sid, 2)['player_visible']['application']['pages'][0]['个人陈述（300字左右）'], '后来未分享新稿')
        self.assertEqual(runtime.Engine(self.engine.directory).export_game(sid, 1), exported)
        exported['player_visible']['application']['pages'][0]['fields']['姓名'] = '篡改返回副本'
        self.assertNotEqual(self.engine.export_game(sid, 1), exported)

    def test_submission_old_session_and_other_students(self):
        s = self.submitted_ready()
        setting = s['setting']
        # 构造额外一对，来源索引随新增学生与关系重映射。
        for old, new in [('s1', 's3'), ('s2', 's4')]:
            i = int(old[1]) - 1
            student = copy.deepcopy(setting['students'][i]); student.update(id=new, name='其他学生不导出'+new)
            setting['students'].append(student)
            pack = copy.deepcopy(setting['takeover_packages'][i]); pack['student_id'] = new
            for key in ('initial_memories', 'private_information'):
                for item in pack[key]:
                    item['source_refs'] = [ref.replace(f'$.students[{i}]', f'$.students[{i+2}]').replace('$.couples[0]', '$.couples[1]') for ref in item['source_refs']]
            setting['takeover_packages'].append(pack)
            setting['review_status']['takeover'][new] = copy.deepcopy(setting['review_status']['takeover'][old])
        relation = json.loads(json.dumps(setting['couples'][0]).replace('s1', 's3').replace('s2', 's4'))
        relation['id'] = 'c2'; setting['couples'].append(relation)
        runtime.validate_setting(setting)
        del s['submitted_versions']; self.engine.save(s)
        loaded = self.engine.load(s['session_id'])
        self.assertEqual(loaded['submitted_versions'], [])
        with self.assertRaises(ValueError): self.engine.export_game(s['session_id'], 1)
        self.submit(loaded)
        pack = self.engine.export_game(s['session_id'], 1)
        self.assertNotIn('其他学生不导出', json.dumps(pack, ensure_ascii=False))
        for mutate in (lambda p: p.update(config={}), lambda p: p['player_visible'].update(private_states={}),
                       lambda p: p['role_private']['takeover_by_student_id'].update(s3={}),
                       lambda p: p['submission'].update(actor='student')):
            bad = copy.deepcopy(pack); mutate(bad)
            with self.assertRaises(ValueError): runtime.validate_game_package(bad)

    def test_project_conversion_strict_admission(self):
        f = copy.deepcopy(self.fixture)
        project = {'schema_version': 'model-couple-project-v1', 'state': {
            'phase': 'done', 'done': True, 'waiting': None, 'personAcceptance': 'review_approved',
            'unresolved': [], 'interventions': [], 'runtimeSettingId': f['setting_id'],
            'config': {'mode': f['mode'], 'count': len(f['students']), 'pairs': len(f['couples']), 'api_key': '密钥哨兵'},
            'metadata': {'date': f['date'], 'calendar': f['calendar'], 'takeover': f['review_status']['takeover']},
            'students': f['students'], 'couples': f['couples'], 'takeover_packages': f['takeover_packages'],
            'reviews': [f['review_status'][k] for k in ('person', 'couple', 'detail')]}}
        script = "const fs=require('fs'),vm=require('vm');const html=fs.readFileSync(process.argv[1],'utf8');const code=html.slice(html.indexOf('function importSetting('),html.indexOf(\"$('file').onchange=\"));const ctx=vm.createContext({crypto:require('crypto').webcrypto});vm.runInContext(code,ctx);process.stdout.write(JSON.stringify(ctx.importSetting(JSON.parse(fs.readFileSync(0,'utf8')))));"
        result = subprocess.run(['node', '-e', script, str(HERE/'legacy'/'legacy-chat.html')], input=json.dumps(project), capture_output=True, text=True, encoding='utf-8', check=True)
        setting = json.loads(result.stdout)
        self.assertEqual(runtime.validate_setting(setting), f)
        self.assertNotIn('密钥哨兵', result.stdout)
        self.assertEqual(self.engine.dispatch('validate', {'setting': setting}, None)['setting_id'], f['setting_id'])
        for mutate in (
            lambda s: s.update(setting_id='不合法'),
            lambda s: s['takeover_packages'][0]['initial_memories'][0].update(source_refs=['$.students[999].name']),
            lambda s: s['review_status'].update(manual_acceptance=True),
            lambda s: s['review_status']['detail'].update(approved=False),
            lambda s: s.update(date='2026-04-23'),
        ):
            invalid = copy.deepcopy(setting)
            mutate(invalid)
            with self.assertRaises(ValueError):
                self.engine.dispatch('validate', {'setting': invalid}, None)

    def output(self):
        return {'speech':'我们先讨论是否愿意参评。','willingness':{'choice':'犹豫','reason':'需要核对授权','conditions':['分别同意'],'pending':['提交时间']}}

    def draft_output(self, action='save_draft', body='本人具体经历草稿哨兵', refs=None):
        return {**self.output(), 'author_intent': '愿意起草', 'statement_update': {
            'action': action, 'text': body, 'source_refs': refs or ['own.pack.initial_memories[0]']}}

    def counseling(self, rounds=4):
        s = self.create(api=True, rounds=rounds)
        for _ in range(2):
            s = self.engine.step(s['session_id'], lambda _: self.confirm_output())
        return self.engine.enter_counseling(s['session_id'])

    def confirm_output(self):
        return {'speech': runtime.CONFIRMATION, 'decision_confirmation': 'confirm', 'willingness': {
            'choice': '愿意', 'reason': '本人确认', 'conditions': ['保留真实经历'], 'pending': []}}

    def natural_confirm_output(self, speech='那就一起参加吧，我愿意，咱们说好的边界也都没问题了。'):
        return {**self.confirm_output(), 'speech': speech, 'public_confirmation': speech}

    def test_natural_confirmation_and_latest_attitude(self):
        s = self.create(api=True, rounds=4); sid = s['session_id']
        first = self.engine.step(sid, lambda _: self.natural_confirm_output())
        self.assertEqual(first['status'], 'ready')
        self.assertEqual(runtime.admission(first), {'s1': True, 's2': False})
        value = self.natural_confirm_output('我也愿意参加，之前担心的事说清楚了。')
        second = self.engine.step(sid, lambda _: value)
        self.assertEqual(second['status'], 'paused')
        self.assertTrue(self.engine.view(second)['can_enter_counseling'])
        self.assertEqual(second['phase'], 'private_decision')
        self.assertEqual(self.engine.control(sid, 'resume')['status'], 'paused')
        refused = self.engine.step(sid, lambda _: {**self.output(), 'speech': '想了想，我还是不参加。',
            'willingness': {'choice': '不愿意', 'reason': '改变态度', 'conditions': [], 'pending': []}})
        self.assertFalse(runtime.admission(refused)['s1'])
        self.assertFalse(self.engine.view(refused)['can_enter_counseling'])
        with self.assertRaises(ValueError): self.engine.enter_counseling(sid)
        self.engine.step(sid, lambda _: self.natural_confirm_output())
        value = self.natural_confirm_output()
        value['speech'] = '仅限私聊的前缀哨兵。' + value['speech']
        final = self.engine.step(sid, lambda _: value)
        expected = [runtime.confirmation_speech(next(r for r in reversed(final['conversation']) if r['student_id'] == student)) for student in final['members']]
        entered = self.engine.enter_counseling(sid)
        self.assertEqual([r['speech'] for r in entered['public_confirmations']], expected)
        self.assertNotIn('仅限私聊的前缀哨兵', json.dumps(runtime.counselor_context(entered), ensure_ascii=False))
        self.assertFalse(any(r['student_id'] == 'Counselor' for r in entered['conversation']))

    def test_natural_confirmation_contract(self):
        s = self.create(api=True); sid = s['session_id']
        for mutate in (
            lambda v: v.update(speech='我先考虑一下'),
            lambda v: v.update(public_confirmation=''),
            lambda v: v.update(public_confirmation={'speech': '愿意'}),
            lambda v: v.update(decision_confirmation='none'),
            lambda v: v['willingness'].update(pending=['条件尚未满足']),
            lambda v: v['willingness'].update(choice='不愿意'),
        ):
            value = self.natural_confirm_output(); mutate(value)
            failed = self.engine.step(sid, lambda _: value)
            self.assertEqual(failed['status'], 'failed')
            self.assertEqual(failed['conversation'], [])
            self.assertEqual(failed['private_states'], s['private_states'])
        for _ in range(2):
            value = self.natural_confirm_output(); value.pop('public_confirmation'); value.pop('decision_confirmation')
            current = self.engine.step(sid, lambda _: value)
        self.assertFalse(any(runtime.admission(current).values()))
        with self.assertRaises(ValueError): self.engine.enter_counseling(sid)

    def test_private_prompt_scope_and_natural_voice(self):
        prompt = runtime.context(self.create(api=True), 's1')[0]['content']
        for phrase in ('只回应上一句最重要的一点', '不强迫甜言蜜语、昵称', '不列材料目录、不分工、不逐条核对证据',
                       '不起草个人陈述', '一两段本人确知的共同回忆', '信息依据留在后台', 'public_confirmation', '尚未满足的条件必须列入pending'):
            self.assertIn(phrase, prompt)
        self.assertNotIn(runtime.CONFIRMATION, prompt)
        self.assertNotIn('逐字包含', prompt)
        s = self.create(api=True, rounds=1)
        for _ in range(2): s = self.engine.step(s['session_id'], lambda _: self.confirm_output())
        self.assertEqual(s['status'], 'paused')
        history = copy.deepcopy(s['conversation'])
        restored = self.engine.load(s['session_id'])
        self.assertEqual(restored['conversation'], history)
        self.assertTrue(self.engine.view(restored)['can_enter_counseling'])
        entered = self.engine.enter_counseling(s['session_id'])
        self.assertEqual([r['speech'] for r in entered['public_confirmations']], [runtime.CONFIRMATION] * 2)

    def teacher(self, sid):
        return self.engine.step(sid, lambda _: {'speech': '请分享真实经历，可以拒绝我的建议。'})

    def test_statement_lifecycle_and_isolation(self):
        s = self.counseling(); sid = s['session_id']
        self.teacher(sid)
        first = self.engine.step(sid, lambda _: self.draft_output())
        self.assertEqual(first['statements']['s1']['text'], '本人具体经历草稿哨兵')
        self.assertNotIn('statement_attachment', first['conversation'][0])
        other = json.dumps(runtime.context(first, 's2'), ensure_ascii=False)
        self.assertNotIn('本人具体经历草稿哨兵', other)
        self.assertIn('本人具体经历草稿哨兵', json.dumps(runtime.context(first, 's1'), ensure_ascii=False))
        self.engine.step(sid, lambda _: self.output())
        self.teacher(sid)
        shared = self.engine.step(sid, lambda _: self.draft_output('share_draft', '主动分享全文'))
        self.assertEqual(shared['conversation'][-1]['statement_attachment']['text'], '主动分享全文')
        self.assertIn('主动分享全文', json.dumps(runtime.context(shared, 's2'), ensure_ascii=False))
        runtime.validate_output(self.draft_output(refs=[f"public.conversation[{len(shared['conversation']) - 1}].statement_attachment.text"]), shared, 's2')
        own_sources = runtime.statement_sources(shared, 's2')
        cognitive_ref = next(ref for ref in own_sources if ref.startswith('own.cognition.'))
        runtime.validate_output(self.draft_output(refs=[cognitive_ref, 'own.current_intentions']), shared, 's2')
        self.assertNotIn('本人具体经历草稿哨兵', json.dumps(runtime.context(shared, 's2'), ensure_ascii=False))
        self.engine.step(sid, lambda _: {**self.output(), 'speech': '建议补充当时自己的感受。'})
        self.teacher(sid)
        revised = self.engine.step(sid, lambda _: self.draft_output(body='回应建议后的本人完整新稿'))
        self.assertEqual(len(revised['statements']['s1']['versions']), 3)
        self.assertEqual(revised['statements']['s2']['versions'], [])
        self.assertEqual(revised['statements']['s1']['versions'][0]['text'], '本人具体经历草稿哨兵')
        self.assertNotIn('回应建议后的本人完整新稿', json.dumps(runtime.context(revised, 's2'), ensure_ascii=False))
        view = self.engine.view(revised)
        self.assertEqual(view['application']['pages'][0]['个人陈述（300字左右）'], '回应建议后的本人完整新稿')
        self.assertEqual(len(view['application']['pages']), 2)
        self.assertEqual(revised['registration'], runtime.REGISTRATION)
        self.assertEqual(self.engine.load(sid)['statements'], revised['statements'])

    def test_statement_rejection_is_atomic(self):
        mutations = [
            lambda v: v.update(author_intent='不愿起草'),
            lambda v: v['statement_update'].update(student_id='s2'),
            lambda v: v['statement_update'].update(source_refs=['$.students[1].fear']),
            lambda v: v['statement_update'].update(source_refs=['other.private_states']),
            lambda v: v['statement_update'].update(source_refs=['other.draft']),
            lambda v: v['statement_update'].update(source_refs=['public.conversation[999].speech']),
            lambda v: v['statement_update'].update(source_refs=[{}]),
            lambda v: v['statement_update'].update(action='none'),
            lambda v: v['statement_update'].update(text='2026年经历'),
            lambda v: v.update(willingness={'choice': '愿意'}),
        ]
        for mutate in mutations:
            s = self.counseling(); sid = s['session_id']; s = self.teacher(sid); value = self.draft_output('share_draft')
            mutate(value)
            failed = self.engine.step(sid, lambda _: value)
            self.assertEqual(failed['status'], 'failed')
            for key in ('conversation', 'private_states', 'statements'):
                self.assertEqual(failed[key], s[key])
        s = self.create(api=True)
        def stop_then_return(_):
            self.engine.control(s['session_id'], 'stop')
            return self.draft_output('share_draft')
        stopped = self.engine.step(s['session_id'], stop_then_return)
        self.assertEqual(stopped['conversation'], [])
        self.assertEqual(stopped['statements'], s['statements'])

    def test_statement_compatibility_and_basic_fields(self):
        s = self.create(api=True); sid = s['session_id']
        del s['statements']; self.engine.save(s)
        restored = self.engine.load(sid)
        self.assertEqual(restored['statements'], runtime.empty_statements(s['members']))
        result = self.engine.step(sid, lambda _: self.output())
        self.assertEqual(result['statements'], restored['statements'])
        none = {**self.output(), 'author_intent': '不愿起草', 'statement_update': {'action': 'none', 'text': '', 'source_refs': []}}
        declined = self.engine.step(sid, lambda _: none)
        self.assertEqual(declined['statements'], restored['statements'])
        page = self.engine.view(result)['application']['pages'][0]
        student = self.fixture['students'][0]
        self.assertEqual(page['fields']['姓名'], student['name'])
        self.assertEqual(page['fields']['绩点'], student['grades'])
        for key in ('学号', '班级', '联系电话', '电子邮箱'):
            self.assertEqual(page['fields'][key], '待补充')
        setting = copy.deepcopy(self.fixture)
        setting['students'][0].update(student_number='2025001', class_name='一班', email='example@invalid', phone='自愿提供')
        current = self.engine.create(setting, 'c1', 'demo', 4)
        self.assertEqual(self.engine.view(current)['application']['pages'][0]['fields']['学号'], '2025001')
        for _ in range(2): current = self.engine.step(current['session_id'], None)
        self.assertEqual(current['phase'], 'private_decision')
        self.assertEqual(current['statements']['s1']['versions'], [])
        current = self.engine.enter_counseling(current['session_id'])
        for _ in range(12): current = self.engine.step(current['session_id'], None)
        self.assertEqual(current['status'], 'completed')
        self.assertEqual(len(current['statements']['s1']['versions']), 4)
        self.assertEqual([v['shared'] for v in current['statements']['s1']['versions']], [False, True, True, True])
        self.assertNotIn('setting', self.engine.view(current))
        self.assertNotIn('own.pack', json.dumps(current['conversation'], ensure_ascii=False))

    def test_public_gate_and_no_private_drafting(self):
        s = self.create(api=True, rounds=4); sid = s['session_id']
        with self.assertRaises(ValueError): self.engine.enter_counseling(sid)
        failed = self.engine.step(sid, lambda _: self.draft_output())
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(failed['conversation'], [])
        for choice in ('犹豫', '不愿意', '尚未决定'):
            value = self.confirm_output(); value['willingness']['choice'] = choice
            self.assertEqual(self.engine.step(sid, lambda _: value)['status'], 'failed')
        value = self.confirm_output(); value['willingness']['pending'] = ['本人尚未确认条件']
        self.assertEqual(self.engine.step(sid, lambda _: value)['status'], 'failed')
        value = self.confirm_output(); value['speech'] = '只是考虑写材料'
        self.assertEqual(self.engine.step(sid, lambda _: value)['status'], 'failed')
        value = self.draft_output('share_draft')
        self.assertEqual(self.engine.step(sid, lambda _: value)['status'], 'failed')
        value = self.confirm_output(); value.pop('decision_confirmation')
        self.engine.step(sid, lambda _: value)
        self.engine.step(sid, lambda _: self.confirm_output())
        with self.assertRaises(ValueError): self.engine.enter_counseling(sid)
        current = self.engine.step(sid, lambda _: self.confirm_output())
        self.assertEqual(current['phase'], 'private_decision')
        self.assertTrue(self.engine.view(current)['can_enter_counseling'])
        withdrawn = {**self.output(), 'decision_confirmation': 'withdraw', 'speech': '我撤回之前的确认。'}
        self.engine.step(sid, lambda _: withdrawn)
        with self.assertRaises(ValueError): self.engine.enter_counseling(sid)

    def test_counselor_permissions_order_refusal_retry_stop(self):
        s = self.create(api=True, rounds=4); sid = s['session_id']
        for _ in range(2): self.engine.step(sid, lambda _: {**self.confirm_output(), 'speech': '此前私聊哨兵 ' + runtime.CONFIRMATION})
        s = self.engine.enter_counseling(sid)
        s['statements']['s1']['text'] = '未分享稿哨兵'
        s['private_states']['s2']['reason'] = '私有意愿哨兵'
        s['setting']['takeover_packages'][1]['private_information'][0]['text'] = '乙秘密哨兵'
        self.engine.save(s)
        payload = json.dumps(runtime.counselor_context(s), ensure_ascii=False)
        for secret in ('此前私聊哨兵', '未分享稿哨兵', '私有意愿哨兵', '乙秘密哨兵', 'takeover_packages', 'review_status'):
            self.assertNotIn(secret, payload)
        self.assertNotIn('此前私聊哨兵', json.dumps(runtime.context(s, 's1'), ensure_ascii=False))
        self.assertNotIn('乙秘密哨兵', json.dumps(runtime.context(s, 's1'), ensure_ascii=False))
        failed = self.engine.step(sid, lambda _: {**self.output(), 'statement_update': {'action': 'none'}})
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(self.engine.view(failed)['current_speaker'], 'Counselor')
        self.assertEqual(failed['private_states'], s['private_states'])
        first = self.engine.step(sid, lambda _: {'speech': '你们最好这样写，因为别人都这样写，如果不这样就不能获奖。', 'suggestion_target': 'both'})
        refused = self.engine.step(sid, lambda _: {**self.output(), 'speech': '我拒绝这种包装，只接受梳理真实经历。'})
        self.assertEqual(refused['statements'], s['statements'])
        last = self.engine.step(sid, lambda _: self.draft_output('share_draft', '本人主动公开稿哨兵'))
        self.assertIn('本人主动公开稿哨兵', json.dumps(runtime.counselor_context(last), ensure_ascii=False))
        self.assertEqual([r['student_id'] for r in last['conversation'][2:]], ['Counselor', 's1', 's2'])
        self.assertEqual(self.engine.view(last)['current_speaker'], 'Counselor')
        def stop(_):
            self.engine.control(sid, 'stop')
            return {'speech': '不能提交的教师发言'}
        stopped = self.engine.step(sid, stop)
        self.assertEqual(stopped['conversation'], last['conversation'])
        self.assertEqual(self.engine.load(sid)['phase'], 'counseling')
        records = [json.loads(r) for r in self.engine.path(sid).with_suffix('.log').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(records[-1]['counselor'], runtime.COUNSELOR)
        self.assertEqual(records[-1]['public_history'], last['conversation'][2:])

    def test_counseling_pause_and_student_retry(self):
        s = self.counseling(rounds=2); sid = s['session_id']
        def pause(_):
            self.engine.control(sid, 'pause')
            return {'speech': '教师当前轮提交后暂停'}
        paused = self.engine.step(sid, pause)
        self.assertEqual(paused['status'], 'paused')
        self.assertEqual(self.engine.view(paused)['current_speaker'], 's1')
        self.engine.control(sid, 'resume')
        failed = self.engine.step(sid, lambda _: {'speech': '错误结构'})
        self.assertEqual(failed['conversation'], paused['conversation'])
        self.assertEqual(self.engine.view(failed)['current_speaker'], 's1')
        good = self.engine.step(sid, lambda _: self.output())
        self.assertEqual(self.engine.view(good)['current_speaker'], 's2')
        for output in (self.output(), {'speech': '第二轮教师'}, self.output(), self.output()):
            good = self.engine.step(sid, lambda _, value=output: value)
        self.assertEqual(good['status'], 'completed')
        self.assertEqual(len(runtime.phase_rows(good)), 6)
        with self.assertRaises(ValueError): self.engine.step(sid, None)

    def test_old_drafts_do_not_imply_consent(self):
        s = self.create(api=True); sid = s['session_id']
        for key in ('phase', 'schema_version', 'counselor', 'public_confirmations', 'counseling_start'): s.pop(key)
        s['statements']['s1'] = {'text': '旧稿保留', 'versions': [{'text': '旧版本'}]}
        s['private_states'] = {student: self.confirm_output()['willingness'] for student in s['members']}
        self.engine.save(s)
        loaded = self.engine.load(sid)
        self.assertEqual(loaded['schema_version'], runtime.SESSION_SCHEMA)
        self.assertEqual(loaded['statements'], s['statements'])
        self.assertFalse(any(runtime.admission(loaded).values()))
        with self.assertRaises(ValueError): self.engine.enter_counseling(sid)

    def test_strict_gate(self):
        self.assertEqual(runtime.validate_setting(self.fixture),self.fixture)
        mutations=[
            lambda s:s['review_status'].update(person_acceptance='manual'),
            lambda s:s['review_status'].update(manual_acceptance=True),
            lambda s:s['review_status'].update(completed=False),
            lambda s:s['review_status'].update(unresolved=['问题']),
            lambda s:s['review_status']['person'].update(approved=False),
            lambda s:s['review_status']['couple'].update(person_revision_requests=[{'student_id':'s1','reason':'问题'}]),
            lambda s:s['review_status']['takeover']['s1'].update(status='manual'),
            lambda s:s['review_status']['takeover']['s1']['review'].update(issues=[{'problem':'未解决'}]),
            lambda s:s['takeover_packages'].pop(),
            lambda s:s['takeover_packages'][0]['initial_memories'][0].update(source_refs=['$.students[1].fear']),
            lambda s:s['takeover_packages'][0]['initial_memories'][0].update(source_refs=['$.couples[0].perspectives[1].hidden']),
            lambda s:s['takeover_packages'][0]['initial_memories'][0].update(source_refs=['$.couples[0].facts[0]']),
            lambda s:s['takeover_packages'][0].update(debug='调试'),
            lambda s:s.update(date='2026-04-24'),
            lambda s:s['students'][0].update(age=17),
            lambda s:s['students'][0].update(background='x'*runtime.MAX_SETTING),
        ]
        for mutate in mutations:
            s=copy.deepcopy(self.fixture);mutate(s)
            with self.assertRaises(ValueError): runtime.validate_setting(s)
        with self.assertRaises(ValueError): self.engine.create(self.fixture,'c1','api',1)

    def test_legacy_metadata_and_sessions(self):
        for year in ('2025','2026'):
            old=copy.deepcopy(self.fixture);old.pop('calendar');old['date']=year+'-04-23'
            before=copy.deepcopy(old)
            self.assertEqual(runtime.validate_setting(old),self.fixture)
            summary=self.engine.dispatch('validate',{'setting':old},None)
            self.assertIn('仅迁移日期元数据',summary['compatibility_notice'])
            created=self.engine.create(old,'c1','demo',1)
            self.assertIn('历史发言和个人状态未改写',created['compatibility_notice'])
            self.assertEqual(old,before)
            self.assertEqual(created['migrations'][0]['version'], runtime.MIGRATION_VERSION)
            old['takeover_packages'][0]['role_instructions']=year+'年经历'
            if year == '2026':
                with self.assertRaisesRegex(ValueError,'重新生成'): runtime.validate_setting(old)
            else:
                self.assertEqual(runtime.validate_setting(old)['takeover_packages'][0]['role_instructions'], '2025年经历')
        for change in ('calendar','announcement','conversation'):
            s=self.create(api=True);sid=s['session_id']
            if change=='calendar': s['setting'].pop('calendar')
            elif change=='announcement': s['announcement']['body']='旧公告：暂不收表'
            else: s['conversation']=[{'date':'2025-04-24','speech':'旧文本'}]
            self.engine.save(s);before=self.engine.path(sid).read_bytes()
            with self.assertRaises(ValueError):self.engine.load(sid)
            with self.assertRaises(ValueError):self.engine.step(sid,lambda _:self.fail('不应调用模型'))
            with self.assertRaises(ValueError):self.engine.control(sid,'resume')
            self.assertEqual(self.engine.path(sid).read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'晚于2025年'):
            runtime.validate_output({**self.output(),'speech':'2026年经历'})

    def test_relative_session_metadata_migration(self):
        old = copy.deepcopy(self.fixture)
        old.update(date='04-23', calendar=copy.deepcopy(runtime.RELATIVE_CALENDAR))
        self.assertEqual(runtime.validate_setting(old), self.fixture)
        s = self.create(api=True)
        s.update(setting=old, date='04-24', calendar=copy.deepcopy(runtime.RELATIVE_CALENDAR), announcement=runtime.announcement(relative=True))
        s['conversation'] = [{'date':'04-24', 'calendar':copy.deepcopy(runtime.RELATIVE_CALENDAR), 'turn':1, 'student_id':'s1', 'speech':'去年认识，2025年想一起参加。'}]
        states = copy.deepcopy(s['private_states'])
        self.engine.save(s)
        migrated = self.engine.load(s['session_id'])
        self.assertEqual(migrated['conversation'][0]['speech'], s['conversation'][0]['speech'])
        self.assertEqual(migrated['private_states'], states)
        self.assertEqual(migrated['setting'], self.fixture)
        self.assertEqual(migrated['date'], '2025-04-24')
        self.assertEqual(migrated['conversation'][0]['calendar'], runtime.CALENDAR)
        self.assertFalse(migrated['migrations'][0]['text_rewritten'])
        before = self.engine.path(s['session_id']).read_bytes()
        self.engine.load(s['session_id'])
        self.assertEqual(self.engine.path(s['session_id']).read_bytes(), before)
        self.assertIn('calendar_metadata_migrated', self.engine.path(s['session_id']).with_suffix('.log').read_text())
        for mutation in ('speech', 'setting', 'notice', 'running'):
            bad = copy.deepcopy(s)
            if mutation == 'speech': bad['conversation'][0]['speech'] = '2026年旧文本'
            elif mutation == 'setting': bad['setting']['students'][0]['background'] = '二零二六年旧文本'
            elif mutation == 'notice': bad['announcement']['body'] += '旧公告'
            else: bad['status'] = 'running'
            self.engine.save(bad)
            before = self.engine.path(s['session_id']).read_bytes()
            with self.assertRaises(ValueError): self.engine.load(s['session_id'])
            self.assertEqual(self.engine.path(s['session_id']).read_bytes(), before)
        for speech in ('2025年经历', '2024年认识', '去年认识，三年前入学'):
            self.assertEqual(runtime.validate_output({**self.output(), 'speech':speech})['speech'], speech)

    def test_context_boundaries(self):
        s=self.create(api=True)
        a,b=s['members']
        s['setting']['students'][0]['background']='完整世界档案哨兵'
        s['setting']['couples'][0]['facts']=['全知关系哨兵']
        s['setting']['takeover_packages'][0]['private_information'][0]['text']='甲秘密哨兵'
        s['setting']['takeover_packages'][1]['private_information'][0]['text']='乙秘密哨兵'
        s['private_states'][a]['reason']='甲私有意愿哨兵';s['private_states'][b]['reason']='乙私有意愿哨兵'
        s['conversation']=[{'date':'04-24','turn':1,'student_id':a,'speech':'公开发言哨兵'}]
        for actor,own,other in [(a,'甲','乙'),(b,'乙','甲')]:
            payload=json.dumps(runtime.context(s,actor),ensure_ascii=False)
            self.assertIn(own+'秘密哨兵',payload);self.assertIn(own+'私有意愿哨兵',payload)
            self.assertNotIn(other+'秘密哨兵',payload);self.assertNotIn(other+'私有意愿哨兵',payload)
            for forbidden in ('完整世界档案哨兵','全知关系哨兵','source_mapping','review_status'):
                self.assertNotIn(forbidden,payload)
            self.assertIn('公开发言哨兵',payload)
            self.assertIn('2025年4月24日周四',payload)
            self.assertIn('2025-04-24',payload)
            self.assertIn('不混入晚于2025年的未来年份',payload)
            self.assertNotIn('2026',payload)
            for phrase in ('回答伴侣','具体理由','不要重复公告','允许拒绝'):
                self.assertIn(phrase,payload)
            self.assertIn('个人陈述',payload)

    def test_notice_authority(self):
        before=hashlib.sha256(runtime.LEGACY.read_bytes()).digest()
        notice=runtime.announcement()
        self.assertNotIn('暂不收表',notice['body']);self.assertIn('公开展示须另行取得双方自愿授权',notice['body'])
        self.assertEqual(notice['date'],'2025-04-24')
        for date in ('2025年4月24日周四','5月4日周日','5月5日周一','5月10日周六'):
            self.assertIn(date,notice['body'])
        self.assertEqual(len(notice['attachment']['applicants']),2)
        for applicant in notice['attachment']['applicants']:
            self.assertTrue(all(v=='' for v in applicant['fields'].values()))
        self.assertNotRegex(json.dumps(notice,ensure_ascii=False),r'2026|今年')
        from datetime import date
        for day, weekday in runtime.CALENDAR['weekdays'].items():
            self.assertEqual(('周一','周二','周三','周四','周五','周六','周日')[date.fromisoformat('2025-'+day).weekday()], weekday)
        self.assertEqual(hashlib.sha256(runtime.LEGACY.read_bytes()).digest(),before)

    def test_bounds_failure_retry_recovery(self):
        s=self.create(api=True,rounds=1);sid=s['session_id']
        def failure(messages): raise RuntimeError('不应被记录的secret')
        failed=self.engine.step(sid,failure)
        self.assertEqual(failed['status'],'failed');self.assertEqual(failed['conversation'],[])
        self.assertNotIn('secret',json.dumps(failed))
        bad=self.engine.step(sid,lambda _: {'speech':'坏结构'})
        self.assertEqual(bad['conversation'],[])
        contexts=[]
        def success(messages): contexts.append(messages);return self.output()
        first=self.engine.step(sid,success)
        self.assertEqual(len(first['conversation']),1);self.assertEqual(first['conversation'][0]['student_id'],'s1')
        restored=runtime.Engine(self.engine.directory)
        self.assertEqual(restored.load(sid)['conversation'],first['conversation'])
        end=restored.step(sid,success)
        self.assertEqual(end['status'],'completed');self.assertEqual(len(end['conversation']),2)
        self.assertEqual(end['registration'],runtime.REGISTRATION)
        with self.assertRaises(ValueError): restored.step(sid,success)
        logs=self.engine.path(sid).with_suffix('.log').read_text(encoding='utf-8')
        self.assertNotIn('secret',logs);self.assertIn('04-24',logs)
        record=json.loads(logs.splitlines()[0]);self.assertEqual(record['calendar'],runtime.CALENDAR)
        self.assertRegex(record['time'],r'^\d{4}-\d{2}-\d{2}T')
        self.assertNotIn('willingness',logs)
        s=self.create();s['status']='running';self.engine.save(s)
        recovered=restored.load(s['session_id']);self.assertEqual(recovered['status'],'paused')
        with self.assertRaises(ValueError): self.engine.load('../creation/config')

    def test_controls_and_concurrency(self):
        s=self.create(api=True);sid=s['session_id'];started=threading.Event();release=threading.Event()
        def call(_): started.set();self.assertTrue(release.wait(5));return self.output()
        worker=threading.Thread(target=lambda:self.engine.step(sid,call));worker.start();self.assertTrue(started.wait(5))
        with self.assertRaises(ValueError):self.engine.step(sid,call)
        self.engine.control(sid,'pause');release.set();worker.join(5)
        self.assertEqual(self.engine.load(sid)['status'],'paused')
        self.assertEqual(len(self.engine.load(sid)['conversation']),1)
        self.engine.control(sid,'resume');self.engine.control(sid,'stop')
        with self.assertRaises(ValueError):self.engine.step(sid,call)
        s=self.create(api=True);sid=s['session_id'];started.clear();release.clear()
        worker=threading.Thread(target=lambda:self.engine.step(sid,call));worker.start();self.assertTrue(started.wait(5))
        self.engine.control(sid,'stop');release.set();worker.join(5)
        self.assertEqual(self.engine.load(sid)['conversation'],[])

    def test_backend_shared_api_mock(self):
        config=Path(self.temp.name)/'api.json'
        config.write_text(json.dumps({'base':'https://provider.invalid/v1','key':'mock-private-key','model':'mock-model'}),encoding='utf-8')
        captured=[]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,limit):return json.dumps({'choices':[{'message':{'content':json.dumps(self_output)}}]}).encode()
        class Opener:
            def open(self,request,timeout):captured.append(request);return Response()
        self_output=self.output()
        before=config.read_bytes()
        with patch.object(server,'CONFIG',config),patch.object(server.socket,'getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443))]),patch.object(server.urllib.request,'build_opener',return_value=Opener()):
            result=server.simulation_call([{'role':'user','content':'隔离模拟上下文'}])
            self.assertEqual(result,self_output)
            request=captured[0]
            self.assertEqual(request.full_url,'https://provider.invalid/v1/chat/completions')
            self.assertEqual(request.get_header('Authorization'),'Bearer mock-private-key')
            self.assertEqual(json.loads(request.data)['model'],'mock-model')
            self_output={'speech':'mock-private-key','willingness':self.output()['willingness']}
            with self.assertRaises(ValueError):server.simulation_call([])
        self.assertEqual(config.read_bytes(),before)
        with patch.object(server,'CONFIG',config),patch.object(server.socket,'getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ValueError):server.simulation_call([])

    def test_http_whitelist_and_config_untouched(self):
        config=Path(self.temp.name)/'config.json';config.write_text(json.dumps({'base':'https://example.invalid/v1','key':'test-only-secret','model':'mock'}),encoding='utf-8');before=config.read_bytes()
        with patch.object(runtime,'ENGINE',self.engine),patch.object(server,'CONFIG',config),patch.object(server,'simulation_call',side_effect=AssertionError('严禁真实调用')):
            app=ThreadingHTTPServer(('127.0.0.1',0),server.Handler);worker=threading.Thread(target=app.serve_forever);worker.start();port=app.server_port
            def req(path,data=None,origin=None,host=None):
                conn=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
                headers={'Host':host or f'127.0.0.1:{port}','Origin':origin or f'http://127.0.0.1:{port}','Content-Type':'application/json'}
                # 跨源/错误Host会在读取正文前拒绝；不发送无关正文，避免Windows关闭未读连接时重置响应。
                body = None if data is None else json.dumps(data)
                if origin == 'https://evil.invalid' or host == 'evil.invalid':
                    body = None
                conn.request('GET' if data is None else 'POST',path,body,headers)
                response=conn.getresponse();result=response.status,response.read();conn.close();return result
            try:
                for route in ('/','/creation/','/student-foundry.html','/tools/creation/student-foundry.html','/simulation/','/tools/simulation/index.html'):
                    self.assertEqual(req(route)[0],302 if 'simulation' in route else 200)
                for route in ('/../creation/config.json','/simulation/../creation/config.json','/%2e%2e/config.json','/tools/creation/config.json','/simulation/runtime.py','/simulation/sessions/a.json'):
                    self.assertEqual(req(route)[0],404)
                self.assertEqual(req('/health',host='evil.invalid')[0],403)
                self.assertEqual(req('/api/simulation/validate',{'setting':self.fixture},origin='https://evil.invalid')[0],403)
                self.assertEqual(req('/api/simulation/create',{'setting':self.fixture,'couple_id':'c1','mode':'demo','max_rounds':1,'path':'../creation/a'})[0],400)
                code,raw=req('/api/simulation/create',{'setting':self.fixture,'couple_id':'c1','mode':'demo','max_rounds':1});self.assertEqual(code,200)
                sid=json.loads(raw)['session_id']
                self.assertEqual(req('/api/simulation/export_game', {'session_id': sid, 'version': 1})[0], 400)
                self.assertEqual(req('/api/simulation/submit_application', {'session_id': sid, 'candidate_token': 'x', 'both_authorized': True})[0], 400)
                for action, extra in [('export_game', {'version': 1}), ('submit_application', {'candidate_token': 'x', 'both_authorized': True})]:
                    self.assertEqual(req('/api/simulation/' + action, {'session_id': sid, **extra}, origin='https://evil.invalid')[0], 403)
                self.assertEqual(req('/api/simulation/enter_counseling', {'session_id': sid})[0], 400)
                self.assertEqual(req('/api/simulation/enter_counseling', {'session_id': sid}, origin='https://evil.invalid')[0], 403)
                for _ in range(2):self.assertEqual(req('/api/simulation/step',{'session_id':sid})[0],200)
                self.assertEqual(json.loads(req('/api/simulation/load',{'session_id':sid})[1])['status'],'paused')
                self.assertEqual(req('/api/simulation/load',{'session_id':sid},origin='https://evil.invalid')[0],403)
                snapshot = json.loads(req('/api/simulation/load',{'session_id':sid})[1])
                self.assertIn('statements', snapshot)
                self.assertEqual(len(snapshot['application']['pages']), 2)
                self.assertNotIn('setting', snapshot)
                self.assertNotIn('takeover_packages', snapshot)
                code, raw = req('/api/simulation/enter_counseling', {'session_id': sid})
                self.assertEqual(code, 200)
                self.assertEqual(json.loads(raw)['phase'], 'counseling')
                self.assertEqual(json.loads(raw)['current_speaker'], 'Counselor')
                self.assertEqual(req('/api/simulation/enter_counseling', {'session_id': sid})[0], 400)
                for _ in range(3): self.assertEqual(req('/api/simulation/step', {'session_id': sid})[0], 200)
                counseling = json.loads(req('/api/simulation/load', {'session_id': sid})[1])
                self.assertEqual([r['student_id'] for r in counseling['conversation'][2:]], ['Counselor', 's1', 's2'])
                self.assertEqual(counseling['status'], 'completed')
                # 本轮演示只保存未分享稿，提交必须拒绝。
                self.assertEqual(req('/api/simulation/submit_application', {'session_id': sid, 'candidate_token': counseling['application_candidate_token'], 'both_authorized': True})[0], 400)
                ready = self.submitted_ready()
                code, raw = req('/api/simulation/submit_application', {'session_id': ready['session_id'], 'candidate_token': self.engine.view(ready)['application_candidate_token'], 'both_authorized': True})
                self.assertEqual(code, 200)
                self.assertEqual(len(json.loads(raw)['submitted_versions']), 1)
                code, raw = req('/api/simulation/export_game', {'session_id': ready['session_id'], 'version': 1})
                self.assertEqual(code, 200)
                self.assertEqual(json.loads(raw)['schema_version'], runtime.GAME_SCHEMA)
                self.assertNotIn('test-only-secret', raw.decode())
                self.assertEqual(req('/api/simulation/load',{'session_id':'../config'})[0],400)
                oversized=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
                oversized.request('POST','/api/simulation/validate',b'',{'Host':f'127.0.0.1:{port}','Origin':f'http://127.0.0.1:{port}','Content-Type':'application/json','Content-Length':str(server.MAX_BODY+1)})
                response=oversized.getresponse();self.assertEqual(response.status,413);response.read();oversized.close()
                log=Path(self.temp.name)/'redaction.log';server.append_log(log,{'data':{'key':'anything','text':'prefix test-only-secret suffix'}})
                self.assertNotIn('test-only-secret',log.read_text(encoding='utf-8'));self.assertNotIn('anything',log.read_text(encoding='utf-8'))
                self.assertEqual(config.read_bytes(),before)
            finally:
                app.shutdown();app.server_close();worker.join()


if __name__=='__main__':unittest.main()
