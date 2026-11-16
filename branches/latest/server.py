"""Loopback same-origin static + campus API server. Run: python server.py --mock."""
import argparse
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from ai_gateway import Gateway, AIError
from campus_backend import Campus, APIError

MAX_BODY = 32768


def make_server(campus, host='127.0.0.1', port=8780, dist=None):
    root = Path(dist or Path(__file__).parent / 'dist').resolve()
    # Snapshot allowlist: never expose project files, dotfiles or symlink escapes.
    allowed = {}
    if root.is_dir():
        for path in root.rglob('*'):
            relative = path.relative_to(root)
            if any(part.startswith('.') for part in relative.parts):
                continue
            if path.is_file() and path.resolve().is_relative_to(root) and (relative.as_posix() in {'index.html', 'app.js', 'style.css', 'SourceHanSansSC-Regular.otf'} or relative.parts[0] == 'assets'):
                allowed['/' + relative.as_posix()] = path.resolve()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def handle(self):
            # Navigation can close a connection while a large font is sent.
            try:
                super().handle()
            except (ConnectionError, TimeoutError):
                self.close_connection = True

        def log_message(self, fmt, *args):
            pass  # Never log player text, query strings or provider errors.

        def _headers(self, status, size, mime):
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(size))
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','same-origin')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; font-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
            self.send_header('Cache-Control','no-store')
            self.send_header('Connection','close')
            self.end_headers()
            self.close_connection = True

        def _json(self,status,data):
            raw = json.dumps(data,ensure_ascii=False).encode('utf-8')
            self._headers(status,len(raw),'application/json; charset=utf-8')
            self.wfile.write(raw)

        def _guard(self):
            hosts = self.headers.get_all('Host',[])
            actual_port = self.server.server_address[1]
            expected = {f'127.0.0.1:{actual_port}', f'localhost:{actual_port}'}
            if len(hosts) != 1 or hosts[0] not in expected:
                raise APIError(403,'Host rejected')
            origins = self.headers.get_all('Origin',[])
            if origins and (len(origins) != 1 or origins[0] != 'http://' + hosts[0]):
                raise APIError(403,'Origin rejected')
            if self.headers.get('Sec-Fetch-Site') in ('cross-site','same-site'):
                raise APIError(403,'Cross-origin request rejected')

        def do_GET(self):
            try:
                self._guard()
                parsed = urlsplit(self.path)
                if parsed.path == '/api/health':
                    return self._json(200,{'ok':True,'ai_configured':campus.gateway.configured,'mock':campus.gateway.mock})
                if parsed.path == '/api/campus':
                    query = parse_qs(parsed.query,keep_blank_values=True)
                    if set(query) != {'session_id'} or len(query['session_id']) != 1:
                        raise APIError(400,'Expected one session_id')
                    return self._json(200,campus.snapshot(query['session_id'][0]))
                path = unquote(parsed.path)
                if path == '/':
                    path = '/index.html'
                target = allowed.get(path)
                if not target or not target.resolve().is_relative_to(root):
                    raise APIError(404,'Not found')
                raw = target.read_bytes()
                self._headers(200,len(raw),mimetypes.guess_type(str(target))[0] or 'application/octet-stream')
                self.wfile.write(raw)
            except APIError as exc:
                self._json(exc.status,{'error':exc.message})
            except (ConnectionError, TimeoutError):
                self.close_connection = True
            except (OSError,ValueError):
                self._json(500,{'error':'Request failed'})

        def do_POST(self):
            try:
                self._guard()
                parsed = urlsplit(self.path)
                if parsed.query or not parsed.path.startswith('/api/campus/'):
                    raise APIError(404,'Not found')
                if self.headers.get('Transfer-Encoding'):
                    raise APIError(400,'Transfer-Encoding is not supported')
                lengths = self.headers.get_all('Content-Length',[])
                if len(lengths) != 1 or not lengths[0].isdigit():
                    raise APIError(411,'Content-Length required')
                length = int(lengths[0])
                if length > MAX_BODY:
                    raise APIError(413,'Body too large')
                if self.headers.get('Content-Type','').split(';')[0].strip().lower() != 'application/json':
                    raise APIError(415,'Expected application/json')
                self.connection.settimeout(10)
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise APIError(400,'Incomplete body')
                try:
                    data = json.loads(raw)
                except (ValueError,UnicodeError):
                    raise APIError(400,'Invalid JSON') from None
                status,result = campus.post(parsed.path.removeprefix('/api/campus/'),data)
                self._json(status,result)
            except APIError as exc:
                self._json(exc.status,{'error':exc.message})
            except (OSError,ValueError):
                self._json(400,{'error':'Invalid request'})
            except Exception:
                self._json(500,{'error':'Request failed'})

        def do_OPTIONS(self):
            self._json(405,{'error':'Method not allowed; CORS is not supported'})

    class Server(ThreadingHTTPServer):
        daemon_threads = True
        def get_request(self):
            connection,address = super().get_request()
            connection.settimeout(10)
            return connection,address

    return Server((host,port),Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='127.0.0.1',choices=['127.0.0.1','localhost'])
    parser.add_argument('--port',type=int,default=8780)
    parser.add_argument('--config',help='Explicit JSON config, or ANY_AWARD_AI_CONFIG')
    parser.add_argument('--mock',action='store_true',help='MOCK only: no real AI requests')
    parser.add_argument('--db',default=str(Path(__file__).parent / 'runtime' / 'campus.sqlite3'))
    args = parser.parse_args()
    try:
        gateway = Gateway(args.config,args.mock)
    except AIError as exc:
        parser.error(str(exc))
    campus = Campus(args.db,gateway)
    server = make_server(campus,args.host,args.port)
    print(f'Campus: http://{args.host}:{server.server_address[1]} | mock={gateway.mock} | ai_configured={gateway.configured}',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        campus.close()


if __name__ == '__main__':
    main()
