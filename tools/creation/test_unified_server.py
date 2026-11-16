"""统一静态装配路由仅运行临时测试服务，禁止读取真实配置。"""
import http.client
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
import student_server as app


class UnifiedRoutes(unittest.TestCase):
    def test_assets_redirect_and_no_config_access(self):
        with patch.object(app, 'CONFIG') as config:
            config.read_text.side_effect = AssertionError('禁止读取真实配置')
            server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            def get(path):
                conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                conn.request('GET', path)
                response = conn.getresponse()
                result = response.status, response.getheader('Location'), response.read().decode('utf-8')
                conn.close()
                return result
            try:
                for path in ('/simulation', '/simulation/', '/tools/simulation/', '/simulation/index.html'):
                    code, location, _ = get(path)
                    self.assertEqual((code, location), (302, '/creation/#chronos'))
                code, _, html = get('/creation/')
                self.assertEqual(code, 200)
                self.assertIn('/creation/unified.js', html)
                self.assertNotIn('<iframe', html)
                code, _, script = get('/creation/author-engine.js')
                self.assertEqual(code, 200)
                self.assertIn("getElementById('author-'+id)", script)
                self.assertIn("article.id='author-trace-'", script)
                self.assertIn('window.authorUI=', script)
                self.assertNotIn('/api/config/', script)
                for path in ('/creation/author-fragment', '/creation/unified.js', '/creation/legacy'):
                    self.assertEqual(get(path)[0], 200)
                for path in ('/creation/data/sessions/a.json', '/creation/author.py', '/creation/author-panel.html', '/static/simulation/config.json'):
                    self.assertEqual(get(path)[0], 404)
                config.read_text.assert_not_called()
            finally:
                server.shutdown()
                server.server_close()
                worker.join()
