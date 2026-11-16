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
        self.assertEqual(p['calls'], 12)
        self.assertEqual([x['task']['agent'] for x in p['logs'] if x['kind'] == 'request'], ['Chronos','C_Chronos','Icelos','C_Icelos','Icelos','C_Icelos','Muse','C_Muse','Icelos','C_Icelos','Icelos','C_Icelos'])
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

    def test_dates_and_registration_states(self):
        p = self.create(); t = a.task(p); baseline = a.demo(p, t)
        for invalid in ('2025-04-23', '2025-05-05', '2025-04-31', '2025-5-03'):
            value = copy.deepcopy(baseline); value['registration']['submitted_on'] = invalid
            with self.assertRaises(ValueError): a.validate_chronos(value, p)
        for mutate in (lambda v: v['people']['s1'].update(consent=False), lambda v: v['people']['s1']['form'].update(status='partial', completed_on=None), lambda v: v['people']['s1']['form'].update(completed_on='2025-05-04'), lambda v: v['registration'].update(withdrawn_on='2025-05-04')):
            value = copy.deepcopy(baseline); mutate(value)
            with self.assertRaises(ValueError): a.validate_chronos(value, p)
        for status in ('not_submitted', 'withdrawn'):
            value = copy.deepcopy(baseline)
            value['registration'] = {'status': status, 'submitted_on': '2025-05-03' if status == 'withdrawn' else None, 'withdrawn_on': '2025-05-04' if status == 'withdrawn' else None}
            a.validate_chronos(value, p)
        for form in ({'status':'not_filled','filled':False,'started_on':None,'completed_on':None,'text':''}, {'status':'partial','filled':True,'started_on':'2025-04-24','completed_on':None,'text':'实际不完整正文'}, {'status':'complete','filled':True,'started_on':'2025-04-24','completed_on':'2025-04-24','text':'截止前任意日完成'}):
            value = copy.deepcopy(baseline); value['people']['s1']['form'] = form
            value['registration'] = {'status':'not_submitted','submitted_on':None,'withdrawn_on':None}
            a.validate_chronos(value, p)

    def test_unsubmitted_and_external_gate(self):
        p = self.create(api=True); pid = p['project_id']; value = a.demo(p, a.task(p))
        value['registration'] = {'status': 'not_submitted', 'submitted_on': None, 'withdrawn_on': None}
        p = self.engine.step(pid, lambda _: value)
        p = self.engine.step(pid, lambda _: {'approved': True, 'summary': 'mock独立审查', 'issues': []})
        self.assertIsNone(p['game_snapshot'])
        for kind in ('game','preparation'):
            with self.assertRaises(ValueError): self.engine.export(pid, kind)
        with self.assertRaises(ValueError): self.nominate(p)
        with self.assertRaises(ValueError): self.engine.step(pid, lambda _: self.fail('不可调用'))
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
        p['reviews'][-1]['candidate_digest'] = p['locks']['chronos']
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
        p['results']['disclosure']['s1']['items'][0]['may_perform'] = False
        script = a.demo(p, a.task(p)); script['scenes'][0]['beats'][0]['source_refs'] = ['disclosure.s1.d1']
        with self.assertRaises(ValueError): a.validate_script(script, p)

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
                for _ in range(2): self.assertEqual(request('step', {'project_id': pid})[0], 200)
                self.assertEqual(request('step', {'project_id': pid})[0], 400)
                self.assertEqual(request('nominate', {'project_id': pid, 'event': '玩家已决定入围', 'event_date': '2025-05-05', 'confirmed': True})[0], 200)
                for _ in range(10): self.assertEqual(request('step', {'project_id': pid})[0], 200)
                self.assertEqual(request('export', {'project_id': pid, 'kind': 'preparation'})[0], 200)
                code, exported = request('export', {'project_id': pid, 'kind': 'project'})
                self.assertEqual(code, 200)
                self.assertEqual(request('import', {'project': exported})[0], 200)
                config.read_text.assert_not_called()
            finally:
                app.shutdown(); app.server_close(); worker.join()

    def test_pure_romance_and_basic_mapping(self):
        p = self.create(award=False)
        self.assertIsNone(p['announcement']); self.assertIsNone(a.task(p))
        self.assertNotIn('registration', self.engine.view(p)['results'])
        self.assertEqual(self.engine.export(p['project_id'], 'background'), r.validate_setting(self.fixture))
        with self.assertRaises(ValueError): self.engine.step(p['project_id'], lambda _: self.fail('纯恋爱不得调用'))
        p = self.advance(self.create()); page = p['game_snapshot']['player_visible']['application']['pages'][0]
        self.assertEqual(page['fields']['姓名'], self.fixture['students'][0]['name'])
        self.assertEqual(page['fields']['学号'], '待补充')
        p['results']['chronos']['people']['s1']['form']['text'] = '篡改锁定'
        with self.assertRaises(ValueError): self.engine.import_project(p)


if __name__ == '__main__': unittest.main()
