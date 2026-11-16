"""The only AI transport in this application. Python standard library only."""
import json
import os
import socket
import sys
import threading
import uuid

_CONSOLE_LOCK = threading.Lock()
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class AIError(Exception):
    """Safe public error: never contains upstream bodies, URLs or credentials."""



PROMPTS_PATH = Path(__file__).resolve().with_name('ai_prompts.json')
PROMPT_KINDS = {'notice', 'result', 'off_topic', 'thread', 'comment'}
EXAMPLE_KEYS = {'prefix', 'daily_title', 'daily_body', 'announcement_title', 'announcement_body',
                'reply_to_thread', 'reply_to_first', 'reply_to_target', 'reply_to_new_comment'}


def load_prompts():
    """Read per real request so edits apply without restart; never fall back silently."""
    try:
        prompts = json.loads(PROMPTS_PATH.read_text(encoding='utf-8-sig'))
        if not isinstance(prompts, dict) or set(prompts) != {'system', 'example_text'}:
            raise ValueError()
        for section, keys in [('system', PROMPT_KINDS), ('example_text', EXAMPLE_KEYS)]:
            values = prompts[section]
            if not isinstance(values, dict) or set(values) != keys:
                raise ValueError()
            if any(not isinstance(value, str) or not value.strip() for value in values.values()):
                raise ValueError()
        return prompts
    except (OSError, ValueError, TypeError):
        raise AIError('Invalid AI prompts configuration (ai_prompts.json)') from None


def parse_response(raw):
    """Parse transport envelope separately from model JSON; never expose raw text."""
    try:
        envelope = json.loads(raw)
        choice = envelope['choices'][0]
        if choice.get('finish_reason') == 'length':
            raise AIError('AI output truncated (finish_reason=length)')
        if choice.get('finish_reason') in ('content_filter', 'refusal'):
            raise AIError('AI response refused or filtered')
        message = choice['message']
        if not isinstance(message, dict):
            raise AIError('AI response envelope invalid')
        content = message.get('content')
        # Some compatible providers put the final object in reasoning_content.
        # Only use it for absent/blank content; never override a malformed answer.
        if content is None or (isinstance(content, str) and not content.strip()):
            reasoning = message.get('reasoning_content')
            if isinstance(reasoning, str) and reasoning.strip():
                candidate = reasoning.strip().lstrip('\ufeff')
                try:
                    fallback = json.loads(candidate)
                except json.JSONDecodeError:
                    fallback = None
                if isinstance(fallback, dict):
                    return fallback
    except (ValueError, KeyError, IndexError, TypeError):
        raise AIError('AI response envelope invalid') from None
    if not isinstance(content, str) or not content.strip():
        raise AIError('AI response content empty or not text')
    content = content.strip().lstrip('\ufeff')
    # Accept only a whole fenced JSON document, never extract arbitrary substrings.
    if content.startswith('```'):
        lines = content.splitlines()
        if len(lines) >= 3 and lines[0].strip().lower() in ('```', '```json') and lines[-1].strip() == '```':
            content = '\n'.join(lines[1:-1]).strip()
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AIError(f'AI JSON syntax invalid (line={exc.lineno}, column={exc.colno})') from None
    if not isinstance(value, dict):
        raise AIError('AI JSON root must be an object')
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fp.close()
        raise AIError('AI redirect refused')


class Gateway:
    def __init__(self, config_path=None, mock=False):
        self.mock = mock
        self._request_lock = threading.Lock()
        self.config = None
        if mock:
            return  # Mock is entirely offline, even with an invalid ambient config.
        path = config_path or os.environ.get('ANY_AWARD_AI_CONFIG')
        if path:
            try:
                config = json.loads(Path(path).read_text(encoding='utf-8-sig'))
                required = {'base_url', 'model', 'timeout_seconds'}
                allowed = required | {'api_key', 'api_key_env', 'max_questions', 'university'}
                if not isinstance(config, dict) or not required <= set(config) or set(config) - allowed:
                    raise ValueError()
                url = urllib.parse.urlsplit(config['base_url'])
                if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment:
                    raise ValueError()
                if not isinstance(config['model'], str) or not config['model'].strip():
                    raise ValueError()
                key = config.get('api_key', '')
                env = config.get('api_key_env', '')
                if not isinstance(key, str) or any(ch in key for ch in '\r\n\x00'):
                    raise ValueError()
                if not isinstance(env, str) or (env and not env.replace('_', '').isalnum()):
                    raise ValueError()
                if not key.strip() and not env:
                    raise ValueError()
                # Legacy game metadata is accepted but never sent to the provider.
                config = {k: v for k, v in config.items() if k not in {'max_questions', 'university'}}
                timeout = config['timeout_seconds']
                if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not 1 <= timeout <= 120:
                    raise ValueError()
                self.config = config
            except (OSError, ValueError, TypeError, KeyError):
                raise AIError('Invalid AI configuration') from None

    def _api_key(self):
        if not self.config:
            return ''
        # Explicit file key wins; an empty file key falls back to the named env.
        return self.config.get('api_key', '').strip() or os.environ.get(self.config.get('api_key_env', ''), '').strip()

    @property
    def configured(self):
        return self.mock or bool(self._api_key())

    def _log_raw(self, call_id, status, raw):
        output = raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else str(raw)
        key = self._api_key()
        if key:
            output = output.replace(key, '[REDACTED_API_KEY]')
        block = f'\n[AI {call_id}] RAW RESPONSE BEGIN ({status})\n{output}\n[AI {call_id}] RAW RESPONSE END\n'
        # Console inspection is best-effort and must not turn a valid task into failure.
        try:
            with _CONSOLE_LOCK:
                encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'
                sys.stdout.write(block.encode(encoding, errors='backslashreplace').decode(encoding))
                sys.stdout.flush()
        except (OSError, ValueError):
            pass

    def generate(self, task):
        """Serialize all services through the application's sole HTTP transport."""
        with self._request_lock:
            return self._generate(task)

    def _generate(self, task):
        """Exactly one bounded HTTP request; no automatic retry or fallback provider."""
        call_id = uuid.uuid4().hex[:8]
        if self.mock:
            names = [p['nickname'] for p in task['personas']]
            if task['kind'] == 'off_topic':
                daily = [('食堂今天吃什么', '食堂的面条和米饭都想吃，大家午饭一般怎么选？', '我今天想吃面条。', '我也一样，配点蔬菜。'),
                         ('宿舍晾衣与天气', '宿舍衣服还没干，今天这天气适合开窗通风吗？', '先看看窗外有没有下雨。', '对，别让衣服又淋湿了。'),
                         ('选课和运动怎么安排', '想把选课时间和运动安排协调一下，大家喜欢跑步还是打球？', '我喜欢晚饭后散步。', '散步也不错，慢慢动起来。')]
                output = {'threads': [{'nickname': names[i], 'title': title, 'body': '【MOCK 非真实AI】' + body,
                    'comments': [{'nickname': names[(i + 1) % len(names)], 'body': '【MOCK 非真实AI】' + first, 'reply_to': None},
                                 {'nickname': names[(i + 2) % len(names)], 'body': '【MOCK 非真实AI】' + second, 'reply_to': 0}]}
                    for i, (title, body, first, second) in enumerate(daily)]}
            elif task['kind'] in ('notice', 'result'):
                result = task['kind'] == 'result'
                body = ('最终获奖者为' + task['announcement']['winner']['name'] + '，入围答辩不等于获奖。') if result else (
                    '看到了优秀情侣奖公开通知，双方分别自愿同意，公开展示另行授权；报名与答辩依2025年公开日程进行，入围由玩家决定。'
                    if task.get('award_id') == 'couple' else '看到了公开公告，期待公开说明评选办法。')
                output = {'threads': [{'nickname': names[i], 'title': ('模拟结果讨论：' if result else '模拟讨论：') + str(i + 1),
                    'body': '【MOCK 非真实AI】' + body,
                    'comments': [{'nickname': names[(i + 1) % len(names)], 'body': '【MOCK 非真实AI】以最终获奖公告为准。' if result else '【MOCK 非真实AI】蹲后续公开通知。', 'reply_to': None}]} for i in range(3)]}
            else:
                output = {'comments': [{'nickname': names[0], 'body': '【MOCK 非真实AI】看到了你的发言，先以公开信息为准。', 'reply_to': task.get('target_comment')}]}
            self._log_raw(call_id, 'MOCK - not a provider response', json.dumps(output, ensure_ascii=False))
            return output
        if not self.configured:
            raise AIError('AI is not configured')
        prompts = load_prompts()
        try:
            system = prompts['system'][task['kind']]
        except (KeyError, TypeError):
            raise AIError('Unsupported AI task kind') from None
        text = prompts['example_text']
        names = [p['nickname'] for p in task.get('personas', [])]
        if len(names) >= 3:
            if task.get('kind') in ('notice', 'result', 'off_topic'):
                daily = task.get('kind') == 'off_topic'
                example = {'threads': [{'nickname': names[i], 'title': text['daily_title'] if daily else text['announcement_title'], 'body': text['daily_body'] if daily else text['announcement_body'],
                    'comments': [{'nickname': names[(i+1)%len(names)], 'body': text['reply_to_thread'], 'reply_to': None},
                                 {'nickname': names[(i+2)%len(names)], 'body': text['reply_to_first'], 'reply_to': 0}]} for i in range(3)]}
            else:
                example = {'comments': [{'nickname': names[0], 'body': text['reply_to_target'], 'reply_to': task.get('target_comment')},
                                        {'nickname': names[1], 'body': text['reply_to_new_comment'], 'reply_to': 0}]}
            system += text['prefix'] + json.dumps(example, ensure_ascii=False)
        payload = {'model': self.config['model'], 'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': json.dumps(task, ensure_ascii=False)}],
            'response_format': {'type': 'json_object'}, 'max_tokens': 4000}
        request = urllib.request.Request(self.config['base_url'].rstrip('/') + '/chat/completions',
            data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self._api_key()}, method='POST')
        try:
            # An empty proxy handler prevents ambient proxy credentials being reused.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
            with opener.open(request, timeout=self.config['timeout_seconds']) as response:
                raw = response.read(262145)
                self._log_raw(call_id, 'HTTP success; capped at 262145 bytes', raw)
                if len(raw) > 262144:
                    raise AIError('AI response too large')
            return parse_response(raw)
        except AIError:
            raise
        except urllib.error.HTTPError as exc:
            status = exc.code
            try:
                raw = exc.read(262145)
                self._log_raw(call_id, f'HTTP {status}; capped at 262145 bytes', raw)
            except (OSError, ValueError):
                self._log_raw(call_id, f'HTTP {status}', '[response body could not be read]')
            finally:
                exc.close()
            raise AIError(f'AI upstream HTTP error (status={status})') from None
        except (urllib.error.URLError, OSError, socket.timeout):
            self._log_raw(call_id, 'transport failure', '[no response body: network failure or timeout]')
            raise AIError('AI request failed or timed out') from None
        except (ValueError, KeyError, IndexError, TypeError):
            raise AIError('AI returned invalid JSON') from None
