import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from ai_gateway import Gateway, AIError, parse_response, load_prompts
from campus_backend import Campus, APIError
from server import make_server


class CampusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'campus.sqlite3'
        self.gateway = Gateway(mock=True)
        self.campus = Campus(self.path, self.gateway, start_worker=False)

    def tearDown(self):
        self.campus.close()
        self.tmp.cleanup()

    def notice(self, sid='one'):
        return self.campus.post('notice', {'session_id': sid, 'school': '测试大学', 'player': '测试者', 'award_id': 'couple'})

    def test_notice_contract_and_idempotency(self):
        _, job = self.notice()
        self.assertEqual(self.notice()[1]['job_id'], job['job_id'])
        snap = self.campus.snapshot('one')
        self.assertEqual(snap['award_id'], 'couple')
        for term in ('2025', '个人学业', '专业实践', '参评理由', '5月4日', '5月10日'):
            self.assertIn(term, snap['announcement']['body'])
        self.assertEqual(snap['history'], [])
        self.campus.run_one()
        self.assertEqual(len(self.campus.snapshot('one')['threads']), 3)
        self.assertEqual(self.campus.snapshot('two')['threads'], [])

    def test_result_disabled_and_unknown_award_rejected(self):
        with self.assertRaises(APIError) as error:
            self.campus.post('result', {'session_id': 'one'})
        self.assertEqual(error.exception.status, 409)
        with self.assertRaises(APIError):
            self.campus.post('notice', {'session_id': 'one', 'school': '本校', 'player': '我', 'award_id': 'removed'})

    def test_daily_job_atomic_retry(self):
        _, job = self.campus.post('off-topic', {'session_id': 'one'})
        with patch.object(self.gateway, 'generate', return_value={'threads': []}):
            self.campus.run_one()
        snap = self.campus.snapshot('one')
        self.assertEqual(snap['threads'], [])
        self.assertEqual(snap['jobs'][0]['status'], 'failed')
        self.assertFalse(self.campus.run_one())
        self.campus.post('retry', {'session_id': 'one', 'job_id': job['job_id']})
        self.campus.run_one()
        self.assertEqual(len(self.campus.snapshot('one')['threads']), 3)

    def test_persistence_and_player_isolation(self):
        self.notice()
        self.campus.post('threads', {'session_id': 'one', 'nickname': '玩家', 'title': '问题', 'body': '请问日程？'})
        self.assertEqual(self.campus.snapshot('two')['threads'], [])
        self.campus.close()
        self.campus = Campus(self.path, self.gateway, start_worker=False)
        self.assertEqual(self.campus.snapshot('one')['threads'][0]['body'], '请问日程？')
        self.assertIsNotNone(self.campus.snapshot('one')['announcement'])

    def test_mock_never_reads_config_and_prompt_contract(self):
        with patch.object(Path, 'read_text', side_effect=AssertionError('不得读配置')):
            self.assertTrue(Gateway('不存在.json', mock=True).configured)
        self.assertEqual(set(load_prompts()['system']), {'notice', 'result', 'off_topic', 'thread', 'comment'})

    def test_transport_parser(self):
        envelope = {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"threads":[]}'}}]}
        self.assertEqual(parse_response(json.dumps(envelope)), {'threads': []})
        envelope['choices'][0]['finish_reason'] = 'length'
        with self.assertRaises(AIError):
            parse_response(json.dumps(envelope))

    def test_http_shared_security_and_removed_endpoint(self):
        app = make_server(self.campus, port=0, dist=self.tmp.name)
        worker = threading.Thread(target=app.serve_forever)
        worker.start()
        try:
            def request(method, path, body=None, headers=None):
                conn = http.client.HTTPConnection('127.0.0.1', app.server_port)
                conn.request(method, path, body, headers or {})
                res = conn.getresponse()
                result = res.status, json.loads(res.read())
                conn.close()
                return result
            self.assertEqual(request('GET', '/api/health')[0], 200)
            self.assertEqual(request('GET', '/api/health', headers={'Origin': 'http://invalid.test'})[0], 403)
            self.assertEqual(request('GET', '/api/defense?session_id=one&candidate_id=x')[0], 404)
            self.assertEqual(request('GET', '/ai_prompts.json')[0], 404)
            payload = json.dumps({'session_id': 'one', 'school': '测试大学', 'player': '我', 'award_id': 'couple'})
            self.assertEqual(request('POST', '/api/campus/notice', payload, {'Content-Type': 'application/json'})[0], 202)
        finally:
            app.shutdown()
            app.server_close()
            worker.join()


if __name__ == '__main__':
    unittest.main()
