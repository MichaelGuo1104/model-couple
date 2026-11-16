"""只在临时目录与临时端口验证日志，不接触用户配置。"""
import concurrent.futures
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from http.server import ThreadingHTTPServer
import student_server as app


class LogTests(unittest.TestCase):
    def test_isolated_routes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / 'config.json'
            config.write_text('隔离配置哨兵', encoding='utf-8')
            with patch.object(app, 'ROOT', root), patch.object(app, 'CONFIG', config), patch.object(app, 'LOG_RUNS', {}):
                server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                port = server.server_port

                def request(path, data, origin=None, host=None):
                    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
                    headers = {'Content-Type': 'application/json', 'Origin': origin or f'http://127.0.0.1:{port}', 'Host': host or f'127.0.0.1:{port}'}
                    conn.request('POST', path, json.dumps(data), headers)
                    response = conn.getresponse()
                    result = response.status, json.loads(response.read())
                    conn.close()
                    return result

                try:
                    self.assertEqual(request('/api/log/start', {}, origin='https://external.invalid')[0], 403)
                    self.assertEqual(request('/api/log/start', {}, origin=f'http://localhost:{port}')[0], 403)
                    self.assertEqual(request('/api/log/start', {}, host='evil.invalid')[0], 403)
                    self.assertEqual(request('/api/log/start', {'path': '../config.json'})[0], 400)
                    code, first = request('/api/log/start', {})
                    self.assertEqual(code, 200)
                    second = request('/api/log/start', {})[1]
                    self.assertNotEqual(first['run_id'], second['run_id'])
                    path = root / 'logs' / Path(first['path']).name
                    self.assertRegex(path.name, r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_\d{6}_[a-f0-9]{32}\.log$')
                    entry = {'role': 'Prometheus', 'phase': 'students', 'event': 'raw_model_output', 'data': '原始坏JSON'}
                    data = {'run_id': first['run_id'], 'entry': entry}
                    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                        codes = list(pool.map(lambda _: request('/api/log/append', data)[0], range(24)))
                    self.assertEqual(codes, [200] * 24)
                    records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
                    self.assertEqual(len(records), 25)
                    self.assertTrue(all('time' in row and 'role' in row and 'phase' in row for row in records))
                    self.assertEqual(records[1]['data'], '原始坏JSON')
                    self.assertEqual(request('/api/log/append', {'run_id': '../config.json', 'entry': entry})[0], 404)
                    self.assertEqual(request('/api/log/append', {**data, 'path': '../config.json'})[0], 400)
                    self.assertEqual(request('/api/log/append', {'run_id': first['run_id'], 'entry': {}})[0], 400)
                    self.assertEqual(request('/api/log/append', {'run_id': first['run_id'], 'entry': {**entry, 'data': 'a' * app.MAX_LOG_ENTRY}})[0], 413)
                    with patch.object(app, 'append_log', side_effect=OSError('模拟磁盘失败')):
                        self.assertEqual(request('/api/log/append', data)[0], 500)
                        self.assertEqual(request('/api/log/start', {})[0], 500)
                    self.assertEqual(config.read_text(encoding='utf-8'), '隔离配置哨兵')
                    self.assertEqual(request('/api/unknown', {})[0], 404)
                finally:
                    server.shutdown()
                    server.server_close()
                    worker.join()


class SharedConfigTests(unittest.TestCase):
    def test_migration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'creation.json'
            target = root / 'common' / 'config.json'
            self.assertEqual(app.migrate_legacy_config(source, target), 'source_missing')
            source.write_bytes(b'{broken')
            self.assertEqual(app.migrate_legacy_config(source, target), 'source_invalid')
            source.write_text('{}', encoding='utf-8')
            self.assertEqual(app.migrate_legacy_config(source, target), 'source_invalid')
            raw = b'{ "base": "https://offline.invalid/v1", "key": "offline", "model": "mock" }\r\n'
            source.write_bytes(raw)
            self.assertEqual(app.migrate_legacy_config(source, target), 'copied')
            self.assertEqual(target.read_bytes(), raw)
            self.assertEqual(source.read_bytes(), raw)
            source.write_bytes(b'{}')
            self.assertEqual(app.migrate_legacy_config(source, target), 'target_exists')
            self.assertEqual(target.read_bytes(), raw)
            target.unlink()
            source.write_bytes(raw)
            with patch.object(app.os, 'open', side_effect=FileExistsError):
                self.assertEqual(app.migrate_legacy_config(source, target), 'target_exists')

    def test_shared_config_routes_and_call(self):
        self.assertEqual(app.CONFIG, app.ROOT.parent / 'common' / 'config.json')
        with tempfile.TemporaryDirectory() as temp, patch.object(app, 'CONFIG', Path(temp) / 'common' / 'config.json'):
            server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            def request(path, data=None, origin=True):
                conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                headers = {'Content-Type': 'application/json'}
                if origin:
                    headers['Origin'] = f'http://127.0.0.1:{server.server_port}'
                conn.request('GET' if data is None else 'POST', path, None if data is None else json.dumps(data), headers)
                response = conn.getresponse()
                result = response.status, json.loads(response.read())
                conn.close()
                return result
            try:
                self.assertEqual(request('/api/config/load', {})[1], dict(base='', key='', model=''))
                config = {'base': 'https://offline.invalid/v1', 'key': 'offline-secret', 'model': 'mock-shared'}
                self.assertEqual(request('/api/config/save', config, origin=False)[0], 403)
                self.assertEqual(request('/api/config/save', config)[0], 200)
                self.assertEqual(request('/api/config/load', {})[1], config)
                with patch.object(app.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('8.8.8.8', 443))]), patch.object(app.urllib.request, 'build_opener') as build:
                    build.return_value.open.return_value.__enter__.return_value.read.return_value = b'{"choices":[{"message":{"content":"{}"}}]}'
                    self.assertEqual(app.simulation_call([]), {})
                    upstream = build.return_value.open.call_args.args[0]
                    self.assertEqual(json.loads(upstream.data)['model'], config['model'])
                    self.assertEqual(upstream.get_header('Authorization'), 'Bearer ' + config['key'])
                for route in ('/common/config.json', '/tools/common/config.json', '/creation/config.json', '/simulation/../common/config.json', '/%63ommon/config.json'):
                    self.assertEqual(request(route)[0], 404)
                self.assertEqual(request('/api/config/save', {'base': 1})[0], 400)
                self.assertEqual(request('/api/config/load', {})[1], config)
            finally:
                server.shutdown()
                server.server_close()
                worker.join()


class TimeoutTests(unittest.TestCase):
    def test_mock_relay_timeouts(self):
        # 临时端口只服务测试；所有上游连接与DNS均替换，禁止读取真实配置。
        original_getaddrinfo = app.socket.getaddrinfo
        def resolve(host, port, *args, **kwargs):
            if host == '127.0.0.1':
                return original_getaddrinfo(host, port, *args, **kwargs)
            return [(2, 1, 6, '', ('8.8.8.8', 443))]
        with tempfile.TemporaryDirectory() as temp, patch.object(app, 'CONFIG', Path(temp) / 'unused.json'), patch.object(app.socket, 'getaddrinfo', side_effect=resolve), patch.object(app.urllib.request, 'build_opener') as build:
            opener = build.return_value
            opener.open.return_value.__enter__.return_value.read.return_value = b'{"choices":[]}'
            server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            def request(extra):
                conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                data = {'url': 'https://offline.invalid/v1/chat/completions', 'key': 'offline', 'payload': {}, **extra}
                conn.request('POST', '/api/chat', json.dumps(data), {'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{server.server_port}'})
                response = conn.getresponse()
                result = response.status, json.loads(response.read())
                conn.close()
                return result
            try:
                self.assertEqual(request({})[0], 200)
                self.assertEqual(opener.open.call_args.kwargs['timeout'], 300)
                server.upstream_timeout = 450
                self.assertEqual(request({})[0], 200)
                self.assertEqual(opener.open.call_args.kwargs['timeout'], 450)
                for value in (30, 300, 720, 1800):
                    self.assertEqual(request({'timeout_seconds': value})[0], 200)
                    self.assertEqual(opener.open.call_args.kwargs['timeout'], value)
                for value in (True, False, None, '300', 300.0, 30.5, 29, 1801, [], {}):
                    opener.open.reset_mock()
                    code, result = request({'timeout_seconds': value})
                    self.assertEqual(code, 400)
                    self.assertIn('timeout_seconds', result['error'])
                    opener.open.assert_not_called()
                server.upstream_timeout = True
                self.assertEqual(request({})[0], 400)
                self.assertEqual(request({'timeout_seconds': 300})[0], 200)
                for error in (TimeoutError(), app.urllib.error.URLError(TimeoutError())):
                    opener.open.side_effect = error
                    code, result = request({'timeout_seconds': 720})
                    self.assertEqual(code, 504)
                    self.assertEqual(result['timeout_source'], 'backend')
                    self.assertIn('720秒', result['error'])
                opener.open.side_effect = app.urllib.error.HTTPError('https://offline.invalid', 504, 'gateway', {}, None)
                code, result = request({'timeout_seconds': 300})
                self.assertEqual(code, 502)
                self.assertEqual(result['upstream_status'], 504)
                self.assertNotIn('timeout_source', result)
                self.assertIn('延长本地等待不能保证解决', result['error'])
            finally:
                server.shutdown()
                server.server_close()
                worker.join()

    def test_simulation_default(self):
        config = MagicMock()
        config.read_text.return_value = json.dumps({'base': 'https://offline.invalid/v1', 'key': 'offline-key', 'model': 'offline'})
        with patch.object(app, 'CONFIG', config), patch.object(app.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('8.8.8.8', 443))]), patch.object(app.urllib.request, 'build_opener') as build:
            build.return_value.open.return_value.__enter__.return_value.read.return_value = b'{"choices":[{"message":{"content":"{}"}}]}'
            self.assertEqual(app.simulation_call([]), {})
            self.assertEqual(build.return_value.open.call_args.kwargs['timeout'], 300)


if __name__ == '__main__':
    unittest.main()
