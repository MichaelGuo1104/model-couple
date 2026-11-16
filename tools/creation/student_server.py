"""Local-only web server and API relay for student-foundry.html."""
import argparse
import ipaddress
import json
import socket
import os
import threading
import uuid
import sys
from datetime import datetime, timezone
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import runtime
import author
from prompt_catalog import javascript_bootstrap


DEFAULT_TIMEOUT_SECONDS = 300


def validate_timeout(value):
    if type(value) is not int or not 30 <= value <= 1800:
        raise ValueError('timeout_seconds 必须是30–1800的整数，不能是布尔值')
    return value


def simulation_call(messages):
    # 模拟页不接收密钥；仅后端按需只读共享配置。
    with CONFIG_LOCK:
        config = json.loads(CONFIG.read_text(encoding='utf-8'))
    url = config['base'].rstrip('/')
    if not url.endswith('/chat/completions'):
        url += '/chat/completions'
    parts = urllib.parse.urlsplit(url)
    runtime.require(parts.scheme == 'https' and parts.hostname and not parts.username and not parts.password and not parts.query and not parts.fragment, 'API地址无效')
    addresses = socket.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
    runtime.require(addresses and all(ipaddress.ip_address(a[4][0]).is_global for a in addresses), '禁止内网API')
    key = config['key']
    runtime.require(isinstance(key, str) and key and '\n' not in key and '\r' not in key and runtime.text(config['model'], 200), 'API配置无效')
    request = urllib.request.Request(url, data=json.dumps({'model':config['model'],'messages':messages,'stream':False}).encode(), headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        raw = response.read(1024 * 1024 + 1)
        runtime.require(len(raw) <= 1024 * 1024, '响应过大')
        content = json.loads(raw)['choices'][0]['message']['content']
        # 上游不得将密钥回显至会话或页面。
        runtime.require(isinstance(content, str) and key not in content, '上游返回敏感内容')
        return json.loads(content)


def redact_log(value):
    secrets = []
    try:
        with CONFIG_LOCK:
            config = json.loads(CONFIG.read_text(encoding='utf-8'))
        if isinstance(config.get('key'), str) and config['key']:
            secrets.append(config['key'])
    except (OSError, ValueError, AttributeError):
        pass
    def visit(v):
        if isinstance(v, str):
            for secret in secrets:
                v = v.replace(secret, '[已过滤密钥]')
            return v
        if isinstance(v, list): return [visit(x) for x in v]
        if isinstance(v, dict): return {visit(k): ('[已过滤密钥]' if k.lower() in {'key','api_key','authorization'} else visit(x)) for k,x in v.items()}
        return v
    return visit(value)
MAX_BODY = 2 * 1024 * 1024
CONFIG = ROOT.parent / "common" / "config.json"


def migrate_legacy_config(source=None, target=None):
    source = Path(source) if source is not None else ROOT / 'config.json'
    target = Path(target) if target is not None else CONFIG
    if target.exists():
        return 'target_exists'
    if not source.exists():
        return 'source_missing'
    try:
        raw = source.read_bytes()
        config = json.loads(raw)
        if not isinstance(config, dict) or not all(isinstance(config.get(k), str) and config[k].strip() for k in ('base', 'key', 'model')):
            return 'source_invalid'
    except (ValueError, UnicodeError):
        return 'source_invalid'
    # 仅创建必要目录；排他创建防止覆盖另一进程或用户已有的配置。
    target.parent.mkdir(exist_ok=True)
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return 'target_exists'
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
    return 'copied'
CONFIG_LOCK = threading.Lock()
LOG_LOCK = threading.Lock()
LOG_RUNS = {}
MAX_LOG_ENTRY = 256 * 1024


def append_log(path, event):
    record = redact_log({"time": datetime.now(timezone.utc).isoformat(), **event})
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Never log request bodies, URLs, or credentials.

    def reply(self, code, data, content_type="application/json; charset=utf-8"):
        body = json.dumps(data, ensure_ascii=False).encode() if not isinstance(data, bytes) else data
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def valid_host(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def do_GET(self):
        if not self.valid_host():
            return self.reply(403, {"error": "Invalid local host"})
        path = urllib.parse.urlsplit(self.path).path
        if path == "/health":
            return self.reply(200, {"service": "student-foundry-relay", "ready": True, "config_api": True})
        pages = {p: ROOT / 'student-foundry.html' for p in ('/', '/creation', '/creation/', '/student-foundry.html', '/creation/student-foundry.html', '/tools/student-foundry.html', '/tools/creation', '/tools/creation/', '/tools/creation/student-foundry.html')}
        if path in ('/simulation', '/simulation/', '/simulation/index.html', '/tools/simulation', '/tools/simulation/', '/tools/simulation/index.html', '/static/simulation', '/static/simulation/', '/static/simulation/index.html'):
            self.send_response(302)
            self.send_header('Location', '/creation/#chronos')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        pages['/simulation/legacy'] = ROOT / 'legacy' / 'legacy-chat.html'
        pages['/creation/legacy'] = ROOT / 'legacy' / 'legacy-chat.html'
        if path == '/creation/author-fragment':
            return self.reply(200, (ROOT / 'author-panel.html').read_bytes(), 'text/html; charset=utf-8')
        if path == '/creation/prompts.js':
            try:
                return self.reply(200, javascript_bootstrap(), 'text/javascript; charset=utf-8')
            except ValueError as error:
                message = json.dumps(str(error), ensure_ascii=True).replace('<', r'\u003c').replace('>', r'\u003e').replace('&', r'\u0026')
                script = 'globalThis.CREATION_PROMPTS=undefined;globalThis.CREATION_PROMPTS_ERROR=' + message + ';\n'
                return self.reply(200, script.encode('utf-8'), 'text/javascript; charset=utf-8')
        if path == '/creation/unified.js':
            return self.reply(200, (ROOT / 'unified.js').read_bytes(), 'text/javascript; charset=utf-8')
        if path == '/creation/author-engine.js':
            source = (ROOT / 'author-panel.html').read_text(encoding='utf-8').split('<script>', 1)[1].split('</script>', 1)[0]
            source = source.replace('document.getElementById(id)', "document.getElementById('author-'+id)")
            source = source.replace("article.id='trace-'", "article.id='author-trace-'")
            bridge = "\nwindow.authorUI={api,run,render,cancelQueue,downloadLocal,importSetting,get project(){return project},set project(value){project=value},get inFlight(){return inFlight},get execution(){return execution}};\n"
            return self.reply(200, ('(()=>{' + source + bridge + '})();').encode(), 'text/javascript; charset=utf-8')
        if path in pages:
            return self.reply(200, pages[path].read_bytes(), 'text/html; charset=utf-8')
        self.reply(404, {"error": "Not found"})

    def do_POST(self):
        port = self.server.server_port
        if not self.valid_host() or self.headers.get("Origin") != f"http://{self.headers.get('Host')}":
            return self.reply(403, {"error": "仅允许本地网页的同源请求，请通过本地服务打开页面。"})
        simulation_routes = {'/api/simulation/' + action for action in ('validate','create','load','step','pause','stop','resume','enter_counseling','submit_application','export_game')}
        author_routes = {'/api/author/' + action for action in ('create','load','step','pause','stop','resume','nominate','export','import','replan_disclosure')}
        if self.path not in author_routes | {"/api/chat", "/api/config/load", "/api/config/save", "/api/log/start", "/api/log/append"} | simulation_routes:
            return self.reply(404, {"error": "Not found"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.reply(415, {"error": "需要 JSON 请求"})
        timeout_seconds = DEFAULT_TIMEOUT_SECONDS
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                return self.reply(413, {"error": "请求体为空或超过2MB"})
            body = self.rfile.read(length)
            if self.path.startswith("/api/log/") and length > MAX_LOG_ENTRY:
                return self.reply(413, {"error": "日志请求超过256KB，请分块提交。"})
            data = json.loads(body)
            if self.path in author_routes:
                try:
                    return self.reply(200, author.ENGINE.dispatch(self.path.rsplit('/', 1)[1], data, simulation_call))
                except (ValueError, TypeError, KeyError, RecursionError):
                    return self.reply(400, {'error': '作者工程请求校验失败，请检查阶段、日期、授权、锁定记录及外部入围条件。'})
                except OSError:
                    return self.reply(500, {'error': '作者工程读取或保存失败。'})
            if self.path in simulation_routes:
                try:
                    result = runtime.ENGINE.dispatch(self.path.rsplit('/', 1)[1], data, simulation_call)
                    return self.reply(200, result)
                except (ValueError, TypeError, KeyError, RecursionError):
                    return self.reply(400, {'error': '运行请求或设定无效：必须全部审查通过、无人工接受且每人接管包来源有效；检查会话状态与参数。'})
                except OSError:
                    return self.reply(500, {'error': '会话或公告读取/保存失败，未操作creation文件。'})
            if self.path.startswith("/api/log/"):
                if not isinstance(data, dict):
                    return self.reply(400, {"error": "日志请求必须是对象。"})
                try:
                    with LOG_LOCK:
                        if self.path == "/api/log/start":
                            if data:
                                return self.reply(400, {"error": "日志路径由服务生成，不接受参数。"})
                            directory = ROOT / "logs"
                            directory.mkdir(exist_ok=True)
                            if directory.is_symlink() or directory.resolve().parent != ROOT.resolve():
                                raise OSError("日志目录无效")
                            run_id = uuid.uuid4().hex
                            name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f") + "_" + run_id + ".log"
                            path = directory / name
                            with path.open("x", encoding="utf-8"):
                                pass
                            append_log(path, {"role": "System", "phase": "start", "event": "created", "data": {"run_id": run_id}})
                            LOG_RUNS[run_id] = path
                            return self.reply(200, {"run_id": run_id, "path": "tools/creation/logs/" + name})
                        if set(data) != {"run_id", "entry"} or not isinstance(data["run_id"], str):
                            return self.reply(400, {"error": "日志参数无效。"})
                        path = LOG_RUNS.get(data["run_id"])
                        if path is None:
                            return self.reply(404, {"error": "未知运行ID，请建立新日志。"})
                        entry = data["entry"]
                        if not isinstance(entry, dict) or set(entry) != {"role", "phase", "event", "data"} or any(not isinstance(entry[k], str) or len(entry[k]) > 120 for k in ("role", "phase", "event")):
                            return self.reply(400, {"error": "日志条目结构无效。"})
                        directory = ROOT / "logs"
                        if directory.is_symlink() or path.is_symlink() or path.resolve().parent != directory.resolve() or directory.resolve().parent != ROOT.resolve():
                            raise OSError("日志路径无效")
                        append_log(path, entry)
                        return self.reply(200, {"written": True})
                except OSError:
                    return self.reply(500, {"error": "日志写入失败，请检查tools/logs目录与权限。"})
            if self.path.startswith("/api/config/"):
                try:
                    with CONFIG_LOCK:
                        if self.path == "/api/config/load":
                            config = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
                            if not isinstance(config, dict) or any(not isinstance(config.get(k, ""), str) for k in ("base", "key", "model")):
                                raise ValueError("Invalid config")
                            return self.reply(200, {k: config.get(k, "") for k in ("base", "key", "model")})
                        if not isinstance(data, dict) or any(not isinstance(data.get(k), str) for k in ("base", "key", "model")):
                            return self.reply(400, {"error": "配置必须包含base、key、model三个文本字段。"})
                        config = {k: data[k].strip() for k in ("base", "key", "model")}
                        CONFIG.parent.mkdir(exist_ok=True)
                        temp = CONFIG.with_suffix(".json.tmp")
                        temp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
                        os.replace(temp, CONFIG)
                        return self.reply(200, {"saved": True})
                except (OSError, ValueError, TypeError):
                    return self.reply(500, {"error": "配置读写失败，请检查tools/common/config.json格式或目录写入权限。"})
            if not isinstance(data, dict):
                raise ValueError('请求必须是对象')
            try:
                # 显式请求优先；诊断覆盖仅用于未传参数的旧客户端，仍须通过范围校验。
                timeout_seconds = validate_timeout(data['timeout_seconds'] if 'timeout_seconds' in data else getattr(self.server, 'upstream_timeout', DEFAULT_TIMEOUT_SECONDS))
            except ValueError as error:
                return self.reply(400, {'error': str(error)})
            url = data["url"]
            parts = urllib.parse.urlsplit(url)
            if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
                raise ValueError("转发地址必须是无凭据和查询参数的 HTTPS 地址")
            if not parts.path.endswith("/chat/completions"):
                raise ValueError("地址必须指向 /chat/completions")
            addresses = socket.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
            if any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
                raise ValueError("安全限制：转发地址不能指向本机或内网")
            key = data["key"]
            if not isinstance(key, str) or not key or "\n" in key or "\r" in key:
                raise ValueError("密钥格式无效")
            payload = data["payload"]
            if not isinstance(payload, dict):
                raise ValueError("payload 必须是对象")
            request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + key, "User-Agent": "StudentFoundry/1.0"})
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None  # Do not forward credentials through redirects.
            opener = urllib.request.build_opener(NoRedirect())
            with opener.open(request, timeout=timeout_seconds) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
                if len(raw) > 8 * 1024 * 1024:
                    return self.reply(502, {"error": "上游响应超过8MB"})
                try:
                    result = json.loads(raw)
                except (ValueError, UnicodeDecodeError):
                    return self.reply(502, {"error": "上游返回的不是 JSON，请检查接口路径。"})
                self.reply(200, result)
        except urllib.error.HTTPError as error:
            self.reply(502, {"error": f"上游接口返回 HTTP {error.code}。上游408/504由服务商或网关超时产生，延长本地等待不能保证解决。请检查密钥、模型、额度和接口路径；3xx重定向不自动跟随。", "upstream_status": error.code})
        except (TimeoutError, socket.timeout):
            self.reply(504, {"error": f"后端连接上游或等待响应超时（等待设置{timeout_seconds}秒）；这不是上游HTTP 504。超时断开不保证上游停止，重试可能重复计费。", "timeout_source": "backend"})
        except urllib.error.URLError as error:
            reason = error.reason
            if isinstance(reason, (TimeoutError, socket.timeout)):
                return self.reply(504, {"error": f"后端连接上游或等待响应超时（等待设置{timeout_seconds}秒）；这不是上游HTTP 504。超时断开不保证上游停止，重试可能重复计费。", "timeout_source": "backend"})
            kind = "TLS证书验证失败" if "CERTIFICATE" in str(reason).upper() else "DNS、代理或网络连接失败"
            self.reply(502, {"error": f"本地服务连接上游失败：{kind}。这不是浏览器CORS错误。"})
        except (ValueError, KeyError, TypeError):
            self.reply(400, {"error": "请求配置无效：请检查 HTTPS 地址、密钥与模型配置；不允许转发到本机或内网。"})
        except OSError:
            self.reply(502, {"error": "本地服务无法连接上游，请检查网络、域名解析和系统代理。"})
        except Exception:
            self.reply(500, {"error": "本地转发处理失败；敏感请求内容未写入日志。"})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    class LocalServer(ThreadingHTTPServer):
        allow_reuse_address = False
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            def server_bind(self):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                super().server_bind()
    migration = migrate_legacy_config()
    if migration == 'source_invalid':
        print('旧配置无效，未迁移；请通过页面保存至tools/common/config.json。', flush=True)
    server = LocalServer(("127.0.0.1", args.port), Handler)
    print(f"Student Foundry: http://127.0.0.1:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
