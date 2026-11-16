"""全链路固定mock；不读取配置、不启动长期服务、不访问模型。"""
import copy
import json
import subprocess
import tempfile
import threading
import unittest
import http.client
from http.server import ThreadingHTTPServer
from unittest.mock import patch
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'creation'))
import student_server as server
from pathlib import Path

import author as a
import runtime as r


class AuthorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(['node', str(Path(__file__).with_name('test_runtime.cjs')), '--fixture'], capture_output=True, text=True, encoding='utf-8', check=True)
        cls.fixture = json.loads(result.stdout)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = a.Engine(Path(self.temp.name) / 'projects')

    def tearDown(self):
        self.temp.cleanup()

    def create(self, api=False, award=True):
        setting = copy.deepcopy(self.fixture)
        if api: setting['mode'] = 'api'
        return self.engine.create(setting, 'c1', 'api' if api else 'demo', award)

    def advance(self, p, stage=None):
        for _ in range(60):
            if a.task(p) is None or stage and a.current_stage(p) != stage: return p
            p = self.engine.step(p['project_id'], lambda messages: self.fail('示例不得调用真实通路'))
            self.assertNotEqual(p['status'], 'failed', p.get('failure'))
        self.fail('流程未停止')

    def nominate(self, p):
        return self.engine.nominate(p['project_id'], '玩家已决定入围', '2025-05-05', True)

    def test_full_chain_snapshot_and_package(self):
        p = self.advance(self.create()); pid = p['project_id']
        self.assertEqual(a.current_stage(p), 'disclosure'); self.assertIsNone(a.task(p))
        snapshot = copy.deepcopy(p['game_snapshot'])
        self.assertEqual(snapshot['submission']['submitted_at_story'], '2025-05-03')
        r.validate_game_package(snapshot)
        p = self.advance(self.nominate(p))
        self.assertEqual(a.current_stage(p), 'done')
        self.assertEqual(p['calls'], 14)
        self.assertEqual([x['task']['agent'] for x in p['logs'] if x['kind'] == 'request'], ['Chronos','C_Chronos','Muse','C_Muse','Icelos','C_Icelos','Icelos','C_Icelos','Muse','C_Muse','Icelos','C_Icelos','Icelos','C_Icelos'])
        self.assertEqual(self.engine.export(pid, 'game'), snapshot)
        package = self.engine.export(pid, 'preparation')
        raw = json.dumps(package, ensure_ascii=False)
        for name in ('C_Icelos', 'C_Muse', 'C_Chronos', 'role_instructions', 'backstage', 'reviews', 'source_refs'):
            # 共同剧本保留其合法公开来源引用；审核和提示不得进入包。
            if name != 'source_refs': self.assertNotIn(name, raw)
        self.assertEqual(set(package['role_private_by_student_id']), set(p['members']))
        self.assertNotIn('role_private_by_student_id', package['common_script'])
        self.assertEqual(p['game_snapshot'], snapshot)
        self.engine.validate_project(p)
        restored = self.engine.import_project(self.engine.export(pid, 'project'))
        self.assertNotEqual(restored['project_id'], pid)
        self.assertEqual(restored['status'], 'paused')
        self.assertEqual(restored['game_snapshot'], snapshot)
        self.assertEqual(a.current_stage(restored), 'done')

    def test_application_is_separate_and_review_responsibilities(self):
        p = self.advance(self.create(), 'chronos')
        self.assertEqual(a.current_stage(p), 'application')
        self.assertIsNone(p['game_snapshot'])
        self.assertIsNone(p['nomination'])
        self.assertNotIn('form', p['results']['chronos']['people']['s1'])
        t = a.task(p)
        self.assertEqual(t['agent'], 'Muse')
        writer = a.messages(p, t)[0]['content']
        critic = a.messages(p, {**t, 'reviewing': True, 'agent': 'C_Muse'})[0]['content']
        self.assertIn('报名填表Muse', writer)
        self.assertNotIn('编造宣传情节', writer)
        self.assertIn('不适用后续Muse虚构宣传豁免', critic)
        p = self.advance(p, 'application')
        self.assertIsNotNone(p['game_snapshot'])
        self.assertIsNone(a.task(p))
        self.assertEqual(r.extracted_rank({'grades':'本科毕业绩点3.8/4.0，专业前5%；研究生课程85分', 'year':'研一'}), '本科：专业前5%')
        self.assertEqual(r.extracted_rank({'grades':'绩点3.2/4.0，年级排名中游', 'year':'大二'}), '本科：年级排名中游')
        self.assertEqual(r.extracted_rank({'grades':'绩点3.9/4.0', 'year':'研一'}), '待补充')

    def test_dates_and_registration_states(self):
        p = self.create(); t = a.task(p); baseline = a.demo(p, t)
        for invalid in ('2025-04-23', '2025-05-05', '2025-04-31', '2025-5-03'):
            value = copy.deepcopy(baseline); value['registration']['submitted_on'] = invalid
            with self.assertRaises(ValueError): a.validate_chronos(value, p)
        for mutate in (lambda v: v['people']['s1'].update(consent=False), lambda v: v['people']['s1'].update(form={'text':'禁止正文'}), lambda v: v['registration'].update(status='not_submitted'), lambda v: v['registration'].update(withdrawn_on='2025-05-04')):
            value = copy.deepcopy(baseline); mutate(value)
            with self.assertRaises(ValueError): a.validate_chronos(value, p)
        for status in ('not_submitted', 'withdrawn'):
            value = copy.deepcopy(baseline)
            value['registration'] = {'status': status, 'submitted_on': '2025-05-03' if status == 'withdrawn' else None, 'withdrawn_on': '2025-05-04' if status == 'withdrawn' else None}
            with self.assertRaises(ValueError): a.validate_chronos(value, p)
        for form in ({'status':'not_filled','filled':False,'started_on':None,'completed_on':None,'text':''}, {'status':'partial','filled':True,'started_on':'2025-04-24','completed_on':None,'text':'实际不完整正文'}, {'status':'complete','filled':True,'started_on':'2025-04-24','completed_on':'2025-04-24','text':'截止前任意日完成'}):
            value = copy.deepcopy(baseline); value['people']['s1']['form'] = form
            value['registration'] = {'status':'not_submitted','submitted_on':None,'withdrawn_on':None}
            with self.assertRaises(ValueError): a.validate_chronos(value, p)

    def test_unsubmitted_and_external_gate(self):
        p = self.create(api=True); pid = p['project_id']; value = a.demo(p, a.task(p))
        value['registration'] = {'status': 'not_submitted', 'submitted_on': None, 'withdrawn_on': None}
        p = self.engine.step(pid, lambda _: value)
        p = self.engine.step(pid, lambda _: {'approved': True, 'summary': 'mock独立审查', 'issues': []})
        self.assertIsNone(p['game_snapshot'])
        for kind in ('game','preparation'):
            with self.assertRaises(ValueError): self.engine.export(pid, kind)
        with self.assertRaises(ValueError): self.nominate(p)
        self.assertEqual(p['status'], 'failed')
        submitted = self.advance(self.create())
        for event, day, confirmation in [('模型推荐入围','2025-05-05',True),('玩家已决定入围','2025-05-04',True),('玩家已决定入围','2025-05-05',False)]:
            with self.assertRaises(ValueError): self.engine.nominate(submitted['project_id'], event, day, confirmation)
        self.nominate(submitted)
        with self.assertRaises(ValueError): self.nominate(submitted)

    def test_person_isolation_and_muse_permissions(self):
        p = self.advance(self.create()); p = self.nominate(p)
        for i, pack in enumerate(p['setting']['takeover_packages']): pack['private_information'][0]['text'] = f'秘密哨兵{i}'
        p['reviews'][0]['response']['summary'] = '审核哨兵'
        p['results']['chronos']['people']['s2']['attitude'] = '乙私有态度哨兵'
        p['locks']['chronos'] = r.digest(p['results']['chronos'])
        next(x for x in p['reviews'] if x['stage'] == 'chronos')['candidate_digest'] = p['locks']['chronos']
        t = a.task(p); first = json.dumps(a.messages(p, t), ensure_ascii=False)
        self.assertIn('秘密哨兵0', first); self.assertNotIn('秘密哨兵1', first); self.assertNotIn('乙私有态度哨兵', first)
        value = a.demo(p, t)
        for change in (lambda v: v.update(student_id='s2'), lambda v: v['items'][0].update(source_refs=['own.private_information.0']), lambda v: v['items'][0].update(text='秘密哨兵0'), lambda v: v['items'][0].update(may_write=False, may_perform=True)):
            bad = copy.deepcopy(value); change(bad)
            with self.assertRaises(ValueError): a.validate_disclosure(bad, p, 's1')
        self.engine.save(p); p = self.advance(p, 'disclosure')
        muse = json.dumps(a.messages(p, a.task(p)), ensure_ascii=False)
        for secret in ('秘密哨兵0','秘密哨兵1','审核哨兵','乙私有态度哨兵','private_information','initial_memories'):
            self.assertNotIn(secret, muse)
        script = a.demo(p, a.task(p)); a.validate_script(script, p)
        script['scenes'][0]['beats'][0]['source_refs'] = ['own.private_information.0']
        with self.assertRaises(ValueError): a.validate_script(script, p)
        for item in p['results']['disclosure']['s1']['items']:
            item.update(teacher_knows=False, may_write=False, may_perform=False)
        script = a.demo(p, a.task(p)); script['scenes'][0]['beats'][0].update(source_refs=['disclosure.s1.d1'], framing='interpretation')
        a.validate_script(script, p)

    def test_public_profile_projection_and_profile_only_defense(self):
        p = self.advance(self.nominate(self.advance(self.create())), 'disclosure')
        original = copy.deepcopy(p)
        profiles = a.public_profiles(p)
        self.assertEqual(set(profiles), set(p['members']))
        for sid, profile in profiles.items():
            self.assertEqual(set(profile), {'name', 'major', 'year', 'grades'})
            self.assertNotIn('school', profile)
            self.assertNotIn('research', profile)
        student = p['setting']['students'][0]
        for key in ('background', 'independent_life', 'desire', 'fear', 'current_intentions', 'personality', 'voice', 'contradiction'):
            student[key] = '未披露混合字段哨兵'
        student['cognition']['Se']['evidence'] = '认知哨兵'
        for sid in p['members']:
            p['results']['disclosure'][sid]['items'] = []
        self.assertFalse(a.script_feasibility(p)['blocked'])
        payload = json.loads(a.messages(p, a.task(p))[1]['content'])
        raw = json.dumps(payload, ensure_ascii=False)
        self.assertEqual(payload['profile'], profiles)
        for marker in ('未披露混合字段哨兵', '认知哨兵', 'cognition', 'private_information', 'initial_memories'):
            self.assertNotIn(marker, raw)
        self.assertIn('profile.s1.grades', payload['allowed_source_refs'])
        script = a.demo(p, a.task(p))
        a.validate_script(script, p)
        self.assertEqual(len(script['scenes'][0]['beats']), 3)
        for sid in p['members']:
            self.assertTrue(any(beat['performers'] == [sid] for beat in script['scenes'][0]['beats']))
        self.assertIn('问答准备', script['scenes'][0]['title'])
        bad = copy.deepcopy(script)
        bad['scenes'][0]['beats'][0]['source_refs'] = ['profile.s1.cognition']
        with self.assertRaises(ValueError): a.validate_script(bad, p)
        self.assertEqual(p['game_snapshot'], original['game_snapshot'])
        self.assertEqual(p['locks'], original['locks'])
        profiles['s1']['name'] = '投影不可回写'
        self.assertNotEqual(student['name'], profiles['s1']['name'])

    def test_review_revision_no_muse_return(self):
        p = self.advance(self.nominate(self.advance(self.create())), 'disclosure')
        p = self.advance(p, 'script'); frozen = r.digest(p['results']['script']); pid = p['project_id']
        p['mode'] = 'api'; p['setting']['mode'] = 'api'; self.engine.save(p)
        for _ in range(2):
            t = a.task(p); response = a.demo(p, t)
            p = self.engine.step(pid, lambda _, value=response: value)
            p = self.engine.step(pid, lambda _: {'approved': False, 'summary': 'mock拒绝', 'issues': ['理由须具体']})
            self.assertEqual(a.current_stage(p), 'attitude'); self.assertFalse(p['reviewing']); self.assertEqual(r.digest(p['results']['script']), frozen)
        self.assertEqual([x['agent'] for x in p['reviews'] if x['stage'] == 'script'], ['C_Muse'])

    def test_failure_pause_stop_restart_import(self):
        p = self.create(api=True); pid = p['project_id']
        p = self.engine.step(pid, lambda _: {'bad': '响应'})
        self.assertEqual(p['status'], 'failed'); self.assertIsNone(p['draft'])
        p = self.engine.step(pid, lambda _: a.demo(p, a.task(p)))
        self.assertTrue(p['reviewing'])
        review = {'approved': True, 'summary': 'mock', 'issues': []}
        def pause(_):
            self.engine.control(pid, 'pause'); return review
        p = self.engine.step(pid, pause)
        self.assertEqual(p['status'], 'paused'); self.assertTrue(p['reviewing']); self.assertEqual(p['reviews'], [])
        p = self.engine.control(pid, 'resume')
        def stop(_):
            self.engine.control(pid, 'stop'); return review
        p = self.engine.step(pid, stop)
        self.assertEqual(p['status'], 'stopped'); self.assertEqual(p['reviews'], [])
        with self.assertRaises(ValueError): self.engine.step(pid, lambda _: self.fail('停止不能调用'))
        p['status'] = 'running'; self.engine.save(p)
        restarted = a.Engine(self.engine.directory).load(pid)
        self.assertEqual(restarted['status'], 'paused')
        restored = self.engine.import_project(restarted)
        self.assertTrue(restored['reviewing']); self.assertIsNotNone(restored['draft'])
        forged = copy.deepcopy(restored); forged['locks']['chronos'] = 'fake'
        with self.assertRaises(ValueError): self.engine.import_project(forged)

    def test_http_author_routes_and_no_config_access(self):
        with patch.object(a, 'ENGINE', self.engine), patch.object(server, 'simulation_call', side_effect=AssertionError('禁止真实调用')), patch.object(server, 'CONFIG') as config:
            config.read_text.side_effect = AssertionError('禁止读取配置')
            app = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
            worker = threading.Thread(target=app.serve_forever); worker.start()
            def request(action, data):
                conn = http.client.HTTPConnection('127.0.0.1', app.server_port, timeout=5)
                conn.request('POST', '/api/author/' + action, json.dumps(data), {'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{app.server_port}'})
                response = conn.getresponse(); result = response.status, json.loads(response.read()); conn.close(); return result
            try:
                code, p = request('create', {'setting': self.fixture, 'couple_id': 'c1', 'mode': 'demo', 'award_enabled': True})
                self.assertEqual(code, 200); pid = p['project_id']
                for _ in range(4): self.assertEqual(request('step', {'project_id': pid})[0], 200)
                self.assertEqual(request('step', {'project_id': pid})[0], 400)
                self.assertEqual(request('nominate', {'project_id': pid, 'event': '玩家已决定入围', 'event_date': '2025-05-05', 'confirmed': True})[0], 200)
                for _ in range(4): self.assertEqual(request('step', {'project_id': pid})[0], 200)
                self.assertEqual(request('replan_disclosure', {'project_id': pid, 'confirmed': False})[0], 400)
                code, replanned = request('replan_disclosure', {'project_id': pid, 'confirmed': True})
                self.assertEqual(code, 200); self.assertEqual(replanned['stage'], 'disclosure')
                self.assertEqual(replanned['status'], 'paused')
                for _ in range(10): self.assertEqual(request('step', {'project_id': pid})[0], 200)
                self.assertEqual(request('export', {'project_id': pid, 'kind': 'preparation'})[0], 200)
                code, exported = request('export', {'project_id': pid, 'kind': 'project'})
                self.assertEqual(code, 200)
                self.assertEqual(request('import', {'project': exported})[0], 200)
                config.read_text.assert_not_called()
            finally:
                app.shutdown(); app.server_close(); worker.join()

    def denied_project(self):
        p = self.nominate(self.advance(self.create()))
        p['mode'] = p['setting']['mode'] = 'api'; self.engine.save(p)
        for _ in range(4):
            response = a.demo(p, a.task(p))
            if not p['reviewing']:
                response['items'] = []
            p = self.engine.step(p['project_id'], lambda _, response=response: response)
        return p

    @patch.object(a, 'public_profiles', return_value={})
    def test_authorization_gate_replan_and_compatibility(self, _profiles):
        p = self.denied_project(); pid = p['project_id']
        frozen = {key: copy.deepcopy(p[key]) for key in ('game_snapshot', 'nomination')}
        chronos = copy.deepcopy(p['results']['chronos']); calls = p['calls']
        view = self.engine.view(p)
        self.assertTrue(view['script_feasibility']['blocked']); self.assertTrue(view['can_replan_disclosure'])
        for _ in range(2):
            p = self.engine.step(pid, lambda _: self.fail('没有授权不得调用模型'))
        self.assertEqual(p['calls'], calls); self.assertFalse(p['failure']['retryable'])
        self.assertEqual(p['failure']['code'], 'no_disclosed_material')
        with self.assertRaises(ValueError): self.engine.replan_disclosure(pid, False)
        old = copy.deepcopy(p['results']['disclosure'])
        view = self.engine.dispatch('replan_disclosure', {'project_id': pid, 'confirmed': True}, lambda _: self.fail('重规划不得调用模型'))
        self.assertEqual(view['stage'], 'disclosure'); self.assertEqual(view['status'], 'paused')
        p = self.engine.load(pid)
        self.assertEqual(p['calls'], calls); self.assertIsNone(p['failure'])
        self.assertEqual(p['logs'][-1]['detail']['disclosure'], old)
        self.assertTrue(p['logs'][-1]['detail']['reviews'])
        self.assertFalse(any(row.get('stage') == 'disclosure' for row in p['reviews']))
        self.assertTrue(p['logs'][-1]['detail']['versions'])
        self.assertFalse(any(row.get('task', {}).get('stage') == 'disclosure' for row in p['versions']))
        stale = copy.deepcopy(p)
        stale['results']['disclosure'] = old
        stale['locks']['disclosure'] = r.digest(old)
        with self.assertRaisesRegex(ValueError, '缺少独立审查记录'):
            self.engine.validate_project(stale)
        with self.assertRaisesRegex(ValueError, '缺少独立审查记录'):
            self.engine.import_project(stale)
        self.assertEqual(p['results']['chronos'], chronos)
        for key, value in frozen.items(): self.assertEqual(p[key], value)
        imported = self.engine.import_project(self.engine.export(pid, 'project'))
        self.engine.validate_project(imported)
        self.assertEqual(imported['logs'][-2]['detail']['disclosure'], old)
        for _ in range(4):
            response = a.demo(p, a.task(p))
            p = self.engine.step(pid, lambda _, response=response: response)
        payload = json.loads(a.messages(p, a.task(p))[1]['content'])
        self.assertIn('application.s1', payload['allowed_source_refs'])
        bad = a.demo(p, a.task(p)); bad['scenes'][0]['beats'][0]['source_refs'] = ['missing.ref']
        p = self.engine.step(pid, lambda _: bad)
        self.assertTrue(p['failure']['retryable'])
        self.assertIn('scene1', p['failure']['message']); self.assertIn('beat1', p['failure']['message'])
        response = a.demo(p, a.task(p)); p = self.engine.step(pid, lambda _: response)
        self.assertTrue(p['reviewing'])
        p = self.engine.step(pid, lambda _: a.demo(p, a.task(p)))
        with self.assertRaises(ValueError): self.engine.replan_disclosure(pid, True)

    def test_replan_archives_pending_script_without_changing_snapshot(self):
        p = self.advance(self.nominate(self.advance(self.create())), 'disclosure')
        p = self.engine.step(p['project_id'], lambda _: self.fail('示例不调用'))
        self.assertTrue(p['reviewing']); draft = copy.deepcopy(p['draft'])
        snapshot = copy.deepcopy(p['game_snapshot']); chronos_lock = p['locks']['chronos']
        p = self.engine.replan_disclosure(p['project_id'], True)
        self.assertEqual(p['logs'][-1]['detail']['draft'], draft)
        self.assertEqual(p['game_snapshot'], snapshot); self.assertEqual(p['locks']['chronos'], chronos_lock)
        self.assertIsNone(p['draft']); self.assertFalse(p['reviewing'])
        self.engine.validate_project(self.engine.import_project(p))

    def test_disclosure_permission_combinations_and_retry(self):
        p = self.nominate(self.advance(self.create()))
        p['mode'] = p['setting']['mode'] = 'api'; self.engine.save(p)
        for knows in (False, True):
            for write in (False, True):
                for perform in (False, True):
                    candidate = a.demo(p, a.task(p))
                    for item in candidate['items']:
                        item.update(teacher_knows=knows, may_write=write, may_perform=perform)
                    original = copy.deepcopy(candidate)
                    a.validate_disclosure(candidate, p, 's1', legacy=True)
                    self.assertEqual(candidate, original)
                    with self.assertRaises(ValueError):
                        a.validate_disclosure(candidate, p, 's1')
        bad = a.demo(p, a.task(p))
        bad['items'][0].update(teacher_knows=False, may_write=True, may_perform=False)
        failed = self.engine.step(p['project_id'], lambda _: bad)
        self.assertEqual(failed['status'], 'failed'); self.assertIsNone(failed['draft'])
        self.assertIn('未知字段', failed['failure']['message'])
        self.assertNotIn(bad['items'][0]['text'], failed['failure']['message'])
        def repair(messages):
            self.assertIn('每项仅含id、text、source_refs', messages[0]['content'])
            self.assertIn('未知字段', json.loads(messages[1]['content'])['validation_feedback'])
            return a.demo(p, a.task(p))
        recovered = self.engine.step(p['project_id'], repair)
        self.assertTrue(recovered['reviewing'])
        self.assertTrue(all(set(item) == {'id', 'text', 'source_refs'} for item in recovered['draft']['items']))

    def test_read_only_disclosure_permission_failure(self):
        path = Path(__file__).parent / 'data/author_projects/2026-11-16_1c8a6590d8864d0ea59a5796c6cf4b17.json'
        if not path.exists(): self.skipTest('实际工程不在本机')
        original = path.read_bytes(); p = json.loads(original)
        with self.assertRaisesRegex(ValueError, '工程版本'):
            self.engine.validate_project(p)
        self.assertEqual(path.read_bytes(), original)

    def test_script_list_shapes_and_precise_retry_feedback(self):
        p = self.advance(self.nominate(self.advance(self.create())), 'disclosure')
        p['mode'] = p['setting']['mode'] = 'api'; self.engine.save(p)
        valid = a.demo(p, a.task(p))
        for field, malformed, expected in [
            ('backstage', 'PRIVATE_SENTINEL', 'script.backstage'),
            ('backstage', {'note': 'PRIVATE_SENTINEL'}, 'script.backstage'),
            ('backstage', [None], 'script.backstage[0]'),
            ('backstage', [' '], 'script.backstage[0]'),
            ('source_refs', [], 'script.scenes[0].beats[0].source_refs'),
            ('source_refs', 'application.s1', 'script.scenes[0].beats[0].source_refs'),
            ('source_refs', [{'ref': 'PRIVATE_SENTINEL'}], 'script.scenes[0].beats[0].source_refs[0]'),
        ]:
            with self.subTest(field=field, malformed=malformed):
                bad = copy.deepcopy(valid)
                if field == 'backstage': bad[field] = malformed
                else: bad['scenes'][0]['beats'][0][field] = malformed
                failed = self.engine.step(p['project_id'], lambda _, bad=bad: bad)
                self.assertEqual(failed['status'], 'failed')
                self.assertIn(expected, failed['failure']['message'])
                self.assertNotIn('PRIVATE_SENTINEL', failed['failure']['message'])
                self.assertIsNone(failed['draft']); self.assertNotIn('script', failed['locks'])
                payload = json.loads(a.messages(failed, a.task(failed))[1]['content'])
                self.assertEqual(payload['validation_feedback'], failed['failure']['message'])
        valid['backstage'] = []
        recovered = self.engine.step(p['project_id'], lambda _: valid)
        self.assertTrue(recovered['reviewing']); self.assertIsNone(recovered['failure'])

    def test_read_only_text_list_failure_project(self):
        path = Path(__file__).parent / 'data/author_projects/2026-11-16_79b882d540eb4aa59acb0551582af643.json'
        if not path.exists(): self.skipTest('实际工程不在本机')
        original = path.read_bytes(); p = json.loads(original)
        with self.assertRaisesRegex(ValueError, '工程版本'):
            self.engine.validate_project(p)
        self.assertEqual(path.read_bytes(), original)

    def test_read_only_original_project(self):
        path = Path(__file__).resolve().parent / 'data/author_projects/2026-11-16_3b21efcdf21f4497a458a60211a514da.json'
        if not path.exists(): self.skipTest('实际工程不在本机')
        original = path.read_bytes()
        p = json.loads(original)
        with self.assertRaisesRegex(ValueError, '工程版本'):
            self.engine.import_project(p)
        self.assertEqual(path.read_bytes(), original)

    def test_legacy_locked_results_and_pending_draft_keep_digests(self):
        p = self.advance(self.nominate(self.advance(self.create())))
        for sid, value in p['results']['disclosure'].items():
            for item in value['items']:
                item.update(teacher_knows=False, may_write=False, may_perform=False)
            for review in p['reviews']:
                if review['stage'] == 'disclosure' and review['student_id'] == sid:
                    review['candidate_digest'] = r.digest(value)
        p['locks']['disclosure'] = r.digest(p['results']['disclosure'])
        original = copy.deepcopy(p)
        self.engine.validate_project(p)
        self.assertEqual(p, original)
        restored = self.engine.import_project(p)
        for key in ('results', 'locks', 'reviews', 'versions', 'calls'):
            self.assertEqual(restored[key], original[key])
        forged = copy.deepcopy(p); forged['results']['disclosure']['s1']['items'][0]['may_write'] = True
        with self.assertRaisesRegex(ValueError, '已锁定阶段被修改'):
            self.engine.validate_project(forged)
        pending = self.nominate(self.advance(self.create()))
        pending['draft'] = a.demo(pending, a.task(pending)); pending['reviewing'] = True
        for item in pending['draft']['items']:
            item.update(teacher_knows=False, may_write=True, may_perform=False)
        imported = self.engine.import_project(pending)
        self.assertEqual(imported['draft'], pending['draft'])
        self.assertEqual(imported['calls'], pending['calls'])
        reviewed = self.engine.step(imported['project_id'], lambda _: self.fail('示例不调用真实模型'))
        self.assertEqual(reviewed['results']['disclosure']['s1'], pending['draft'])

    def test_partial_application_stays_context_only_and_one_empty_person(self):
        p = self.advance(self.nominate(self.advance(self.create())), 'disclosure')
        p['results']['disclosure']['s1']['items'] = []
        form = p['results']['disclosure']['s2']['items'][-1]
        form['text'] = form['text'][:4]
        sources = a.muse_sources(p)
        self.assertNotIn('application.s1', sources)
        self.assertNotIn('application.s2', sources)
        self.assertIn('disclosure.s2.form', sources)
        self.assertFalse(a.script_feasibility(p)['blocked'])
        payload = json.loads(a.messages(p, a.task(p))[1]['content'])
        self.assertEqual(set(payload['context_only_refs']), {'application.s1', 'application.s2'})
        script = a.demo(self.advance(self.nominate(self.advance(self.create())), 'disclosure'), {'stage': 'script', 'student_id': None, 'reviewing': False})
        script['scenes'][0]['beats'][0]['source_refs'] = ['application.s1']
        with self.assertRaisesRegex(ValueError, '不在已披露素材'):
            a.validate_script(script, p)
        a.validate_script(a.demo(p, {'stage': 'script', 'student_id': None, 'reviewing': False}), p)

    def test_demo_script_uses_disclosure_without_full_application(self):
        p = self.advance(self.nominate(self.advance(self.create())), 'disclosure')
        for sid in p['members']:
            p['results']['disclosure'][sid]['items'] = [item for item in p['results']['disclosure'][sid]['items'] if 'own.form_text' not in item['source_refs']]
        p['results']['disclosure'][p['members'][1]]['items'] = []
        self.assertFalse(a.script_feasibility(p)['blocked'])
        result = a.demo(p, a.task(p))
        a.validate_script(result, p)
        self.assertEqual(len(result['scenes'][0]['beats']), 4)
        refs = [ref for beat in result['scenes'][0]['beats'] for ref in beat['source_refs']]
        self.assertTrue(any(ref.startswith('disclosure.') for ref in refs))
        self.assertTrue(any(ref.startswith('profile.s2.') for ref in refs))

    def test_stage_fiction_all_framings_reach_independent_review(self):
        for framing in ('fact', 'interpretation', 'staging'):
            with self.subTest(framing=framing):
                p = self.advance(self.nominate(self.advance(self.create())), 'disclosure')
                frozen = {key: copy.deepcopy(p[key]) for key in ('game_snapshot', 'nomination')}
                chronos = copy.deepcopy(p['results']['chronos'])
                p['mode'] = p['setting']['mode'] = 'api'; self.engine.save(p)
                script = a.demo(p, a.task(p))
                script['scenes'][0]['beats'][0].update(framing=framing, text='我们在月亮上搭起一座桥，让全场听见两颗心的回声！')
                p = self.engine.step(p['project_id'], lambda _: script)
                self.assertTrue(p['reviewing']); self.assertNotIn('script', p['locks'])
                self.assertEqual(a.task(p)['agent'], 'C_Muse')
                rejection = {'approved': False, 'summary': '宣传主题不够突出', 'issues': ['增强双人动作配合']}
                p = self.engine.step(p['project_id'], lambda _: rejection)
                self.assertFalse(p['reviewing']); self.assertNotIn('script', p['locks'])
                p = self.engine.step(p['project_id'], lambda _: script)
                p = self.engine.step(p['project_id'], lambda _: {'approved': True, 'summary': '固定mock：宣传与表演效果通过', 'issues': []})
                self.assertIn('script', p['locks'])
                self.assertEqual(p['results']['chronos'], chronos)
                for key, value in frozen.items(): self.assertEqual(p[key], value)
                restored = self.engine.import_project(p)
                for key in ('results', 'reviews', 'locks', 'game_snapshot', 'nomination'):
                    self.assertEqual(restored[key], p[key])

    def test_stage_fiction_keeps_structure_sources_secrets_and_external_boundaries(self):
        p = self.advance(self.nominate(self.advance(self.create())), 'disclosure')
        script = a.demo(p, a.task(p))
        secret = p['setting']['takeover_packages'][0]['private_information'][0]['text']
        for change in (
            lambda v: v['scenes'][0]['beats'][0].update(framing='fiction'),
            lambda v: v['scenes'][0]['beats'][0].update(source_refs=['own.private_information.0']),
            lambda v: v['scenes'][0]['beats'][0].update(source_refs=['missing.ref']),
            lambda v: v['scenes'][0]['beats'][0].update(source_refs=[]),
            lambda v: v['scenes'][0]['beats'][0].update(text=secret),
            lambda v: v.update(backstage=[secret]),
            lambda v: v['scenes'][0]['beats'][0].update(performers=['unknown']),
        ):
            bad = copy.deepcopy(script); change(bad)
            with self.assertRaises(ValueError): a.validate_script(bad, p)

    def test_obsolete_fact_failure_and_critic_feedback_restoration(self):
        p = self.advance(self.nominate(self.advance(self.create())), 'disclosure')
        p['mode'] = p['setting']['mode'] = 'api'
        p['failure'] = {'task': a.task(p), 'message': '事实台词须引用原文，改写须标记interpretation/staging并审核', 'retryable': True}
        p['draft'] = a.demo(p, a.task(p))
        p['draft']['scenes'][0]['beats'][0].update(framing='fact', text='两人在云端交换一整片星河。')
        p['last_review'] = {'approved': False, 'summary': '旧版事实审查', 'issues': ['必须事实准确，不得编造，台词须逐字引用来源']}
        p['reviews'].append({'stage': 'script', 'student_id': None, 'agent': 'C_Muse', 'candidate_digest': r.digest(p['draft']), 'response': copy.deepcopy(p['last_review']), 'time': a.now()})
        self.engine.save(p)
        original = self.engine.path(p['project_id']).read_bytes()
        restored = self.engine.import_project(p)
        for key in ('failure', 'last_review', 'draft', 'reviews', 'locks', 'game_snapshot'):
            self.assertEqual(restored[key], p[key])
        for reviewing in (False, True):
            t = {**a.task(restored), 'reviewing': reviewing, 'agent': 'C_Muse' if reviewing else 'Muse'}
            messages = a.messages(restored, t); payload = json.loads(messages[1]['content'])
            self.assertNotIn('validation_feedback', payload)
            self.assertIn('不因夸张虚构否决', messages[0]['content'])
            self.assertIn('由本规则显式覆盖', messages[0]['content'])
            if reviewing:
                self.assertIn('不得把其他阶段的事实审查标准套用到剧本', messages[0]['content'])
            else:
                self.assertEqual(payload['revision_requests'], p['last_review'])
        recovered = self.engine.step(restored['project_id'], lambda _: copy.deepcopy(p['draft']))
        self.assertTrue(recovered['reviewing']); self.assertIsNone(recovered['failure'])
        self.assertEqual(recovered['game_snapshot'], p['game_snapshot'])
        self.assertEqual(self.engine.path(p['project_id']).read_bytes(), original)

    def test_stage_award_fantasy_does_not_establish_real_result(self):
        p = self.advance(self.nominate(self.advance(self.create())), 'disclosure')
        snapshot = copy.deepcopy(p['game_snapshot']); nomination = copy.deepcopy(p['nomination'])
        script = a.demo(p, a.task(p))
        script['scenes'][0]['beats'][0].update(text='灯光亮起，我们梦见荣获优秀情侣奖，已经获奖的欢呼响彻舞台。', framing='fact')
        a.validate_script(script, p)
        self.assertEqual(p['game_snapshot'], snapshot)
        self.assertEqual(p['nomination'], nomination)
        bogus = copy.deepcopy(p['results']['chronos'])
        bogus['summary'] = '已经获奖'
        with self.assertRaisesRegex(ValueError, '不得创作既定'):
            a.validate_chronos(bogus, p)

    def test_personal_resume_is_available_for_voluntary_disclosure_only(self):
        p = self.nominate(self.advance(self.create()))
        student = next(x for x in p['setting']['students'] if x['id'] == 's1')
        student['independent_life'] = '科研项目中负责数据整理，参加社区志愿服务。'
        sources = a.own_sources(p, 's1')
        self.assertEqual(sources['own.profile.independent_life'], student['independent_life'])
        self.assertNotIn('independent_life', a.public_profiles(p)['s1'])
        candidate = {'student_id': 's1', 'items': [{'id': 'resume', 'text': student['independent_life'], 'source_refs': ['own.profile.independent_life']}], 'stance': '愿意说明自己的具体贡献'}
        a.validate_disclosure(candidate, p, 's1')
        self.assertNotEqual(a.own_sources(p, 's2').get('own.profile.independent_life'), student['independent_life'])

    def test_pure_romance_and_basic_mapping(self):
        p = self.create(award=False)
        self.assertIsNone(p['announcement']); self.assertIsNone(a.task(p))
        self.assertNotIn('registration', self.engine.view(p)['results'])
        self.assertEqual(self.engine.export(p['project_id'], 'background'), r.validate_setting(self.fixture))
        with self.assertRaises(ValueError): self.engine.step(p['project_id'], lambda _: self.fail('纯恋爱不得调用'))
        p = self.advance(self.create()); page = p['game_snapshot']['player_visible']['application']['pages'][0]
        self.assertEqual(page['fields']['姓名'], self.fixture['students'][0]['name'])
        self.assertEqual(page['fields']['学号'], '待补充')
        p['results']['application']['statements']['s1'] = '篡改锁定'
        with self.assertRaises(ValueError): self.engine.import_project(p)


if __name__ == '__main__': unittest.main()
