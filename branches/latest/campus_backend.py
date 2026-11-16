"""Persistent, session-isolated campus service. One worker, explicit retries."""
import json
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from ai_gateway import AIError


class APIError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def text(value, name, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or '\x00' in value:
        raise APIError(400, 'Invalid ' + name)
    return value.strip()


def session(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise APIError(400, 'Invalid session_id')
    return value


def uid():
    return uuid.uuid4().hex


def now():
    return datetime.now(timezone.utc).isoformat()


class Campus:
    def __init__(self, db_path, gateway, seed_dir=None, budget=20, start_worker=True):
        self.db_path, self.gateway, self.budget = str(db_path), gateway, budget
        if self.db_path != ':memory:':
            self.db_path = str(Path(self.db_path).expanduser().resolve())
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        seed = Path(seed_dir or Path(__file__).parent / 'campus_seed')
        self.personas = json.loads((seed / 'personas.json').read_text(encoding='utf-8'))['personas']
        self.history = json.loads((seed / 'history.json').read_text(encoding='utf-8'))
        self.names = {p['nickname'] for p in self.personas}
        self.lock = threading.RLock()
        self.wake, self.stop = threading.Event(), threading.Event()
        self.db = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;
        CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, announcement TEXT, calls INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS publications(session_id TEXT NOT NULL REFERENCES sessions(id), event TEXT NOT NULL, announcement TEXT NOT NULL, PRIMARY KEY(session_id,event));
        CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), title TEXT NOT NULL, body TEXT NOT NULL, nickname TEXT NOT NULL, kind TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS comments(id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), thread_id TEXT NOT NULL REFERENCES threads(id), body TEXT NOT NULL, nickname TEXT NOT NULL, kind TEXT NOT NULL, created_at TEXT NOT NULL, reply_to TEXT REFERENCES comments(id));
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), kind TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL, error TEXT, event TEXT, created_at TEXT NOT NULL, UNIQUE(session_id,event));
        CREATE INDEX IF NOT EXISTS thread_session ON threads(session_id);
        CREATE INDEX IF NOT EXISTS comment_session ON comments(session_id);
        CREATE INDEX IF NOT EXISTS job_session ON jobs(session_id);
        ''')
        # 保留现有数据库内容，只补充缺失列，不改写历史公告。
        if 'award_id' not in {column['name'] for column in self.db.execute('PRAGMA table_info(sessions)')}:
            self.db.execute("ALTER TABLE sessions ADD COLUMN award_id TEXT NOT NULL DEFAULT 'couple'")
        self.db.execute("UPDATE jobs SET status='failed',error='Interrupted by server restart; explicit retry required' WHERE status='running'")
        self.worker = None
        if start_worker:
            self.worker = threading.Thread(target=self._loop, name='campus-ai-worker', daemon=True)
            self.worker.start()
            self.wake.set()

    def close(self):
        self.stop.set()
        self.wake.set()
        if self.worker:
            self.worker.join(125)
        self.db.close()

    def _transaction(self, action):
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                result = action()
                self.db.execute('COMMIT')
                return result
            except BaseException:
                self.db.execute('ROLLBACK')
                raise

    def _ensure(self, sid):
        self.db.execute('INSERT OR IGNORE INTO sessions(id) VALUES(?)', (sid,))

    def _job(self, sid, kind, payload, event=None):
        jid = uid()
        self.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?)',
            (jid, sid, kind, 'queued', json.dumps(payload, ensure_ascii=False), None, event, now()))
        return {'job_id': jid, 'status': 'queued'}

    def snapshot(self, sid):
        sid = session(sid)
        with self.lock:
            row = self.db.execute('SELECT announcement,award_id FROM sessions WHERE id=?', (sid,)).fetchone()
            threads = []
            for t in self.db.execute('SELECT * FROM threads WHERE session_id=? ORDER BY created_at,rowid', (sid,)):
                comments = [self._public(c, comment=True) for c in self.db.execute('SELECT * FROM comments WHERE session_id=? AND thread_id=? ORDER BY created_at,rowid', (sid,t['id']))]
                threads.append(dict(self._public(t), comments=comments))
            jobs = [{'id': j['id'], 'status': j['status'], 'kind': j['kind'], **({'error': j['error']} if j['error'] else {})} for j in self.db.execute('SELECT * FROM jobs WHERE session_id=? ORDER BY created_at,rowid', (sid,))]
            result = self.db.execute("SELECT announcement FROM publications WHERE session_id=? AND event='result-v1'", (sid,)).fetchone()
            return {'award_id': row['award_id'] if row and row['announcement'] else None, 'announcement': json.loads(row['announcement']) if row and row['announcement'] else None, 'result_announcement': json.loads(result['announcement']) if result else None, 'threads': threads, 'jobs': jobs, 'history': self.history}

    @staticmethod
    def _public(row, comment=False):
        result = {'id': row['id'], 'body': row['body'], 'author': {'nickname': row['nickname'], 'kind': row['kind']}, 'created_at': row['created_at']}
        result['reply_to' if comment else 'title'] = row['reply_to' if comment else 'title']
        return result

    def post(self, route, data):
        if not isinstance(data, dict):
            raise APIError(400, 'Expected JSON object')
        allowed = {'off-topic': {'session_id'}, 'result': {'session_id','school','player','shortlist','winner'}, 'notice': {'session_id','school','player','award_id'}, 'threads': {'session_id','title','body','nickname'}, 'comments': {'session_id','thread_id','body','nickname','reply_to'}, 'retry': {'session_id','job_id'}}
        if route not in allowed:
            raise APIError(404, 'Not found')
        if set(data) - allowed[route]:
            raise APIError(400, 'Unknown fields; only public content is accepted')
        sid = session(data.get('session_id'))
        def save():
            self._ensure(sid)
            if route == 'off-topic':
                old = self.db.execute("SELECT * FROM jobs WHERE session_id=? AND event='off-topic-v1'", (sid,)).fetchone()
                if old:
                    return 202, {'job_id': old['id'], 'status': old['status']}
                if not self.gateway.configured:
                    return 503, {'error': 'AI is not configured; submit off-topic again after configuration'}
                return 202, self._job(sid, 'off_topic', {}, 'off-topic-v1')
            if route == 'result':
                raise APIError(409, '当前仅实施至情侣答辩结束，不发布获奖结果')
            if route == 'notice':
                award_id = data.get('award_id', 'couple')
                if not isinstance(award_id, str) or award_id != 'couple':
                    raise APIError(400, 'Invalid award_id')
                existing = self.db.execute('SELECT announcement,award_id FROM sessions WHERE id=?', (sid,)).fetchone()
                if existing['announcement'] and existing['award_id'] != award_id:
                    raise APIError(409, 'The published notice award cannot be replaced')
                if award_id == 'couple' and self.db.execute('SELECT 1 FROM publications WHERE session_id=?', (sid,)).fetchone():
                    raise APIError(409, 'A historical result already exists for this session')
                school = text(data.get('school'), 'school', 80)
                player = text(data.get('player'), 'player', 40)
                if award_id == 'couple':
                    notice = {'title': '关于开展2025年度“优秀情侣奖”评选工作的通知',
                        'body': school + '文件\n校学〔2025〕2号\n各学院：\n为尊重学生自主选择，倡导平等、尊重与共同成长，现发布2025年度“优秀情侣奖”评选通知及空白报名表样。有关事项通知如下。\n'
                            + '一、参与原则。学生甲、学生乙须分别知情、自愿同意参与；任何一方均可选择不参加或撤回，不因是否恋爱、是否申报或是否获奖受到评价。\n'
                            + '二、材料边界。分别陈述个人学业、专业实践、成长、关系支持与参评理由，不设性别、交往时长、消费金额或社交热度门槛，不以这些因素排名。不收集私人聊天记录、社交账号、密码或其他与评选无关的隐私。\n'
                            + '三、公开授权。参与评选与对外公开分别征求双方意见；公开展示须另行取得双方自愿授权，不同意公开不影响参与。\n'
                            + '四、工作安排。2025年4月24日周四开放报名，5月4日周日截止，5月5日周一由玩家决定入围，5月10日周六答辩。入围不等于获奖；本游戏阶段仅实施至答辩结束，不进入颁奖。\n'
                            + school + '\n2025年4月24日\n' + school + '办公室\n2025年4月24日印发'}
                self.db.execute('UPDATE sessions SET announcement=COALESCE(announcement,?),award_id=? WHERE id=?', (json.dumps(notice, ensure_ascii=False),award_id,sid))
                old = self.db.execute("SELECT * FROM jobs WHERE session_id=? AND event='notice-v1'", (sid,)).fetchone()
                if old:
                    return 202, {'job_id':old['id'],'status':old['status']}
                if not self.gateway.configured:
                    return 503, {'error':'AI is not configured; announcement saved; submit notice again after configuration'}
                saved = json.loads(self.db.execute('SELECT announcement FROM sessions WHERE id=?', (sid,)).fetchone()[0])
                return 202, self._job(sid,'notice',{'award_id': award_id, 'announcement': saved, 'result_announcement': None},'notice-v1')
            if route == 'retry':
                jid = text(data.get('job_id'), 'job_id', 100)
                job = self.db.execute('SELECT * FROM jobs WHERE id=? AND session_id=?', (jid,sid)).fetchone()
                if not job:
                    raise APIError(404,'Job not found')
                if job['status'] != 'failed':
                    raise APIError(409,'Only failed jobs can be explicitly retried')
                if not self.gateway.configured:
                    raise APIError(503,'AI is not configured')
                if self.db.execute('SELECT calls FROM sessions WHERE id=?',(sid,)).fetchone()[0] >= self.budget:
                    raise APIError(429,'Session AI budget exhausted')
                self.db.execute("UPDATE jobs SET status='queued',error=NULL WHERE id=?",(jid,))
                return 202, {'job_id':jid,'status':'queued'}
            body = text(data.get('body'),'body',3000 if route == 'threads' else 1200)
            nickname = text(data.get('nickname'),'nickname',40)
            if nickname in self.names:
                raise APIError(400,'Player nickname must not impersonate a forum persona')
            if route == 'threads':
                title = text(data.get('title'),'title',100)
                tid = uid()
                self.db.execute('INSERT INTO threads VALUES(?,?,?,?,?,?,?)',(tid,sid,title,body,nickname,'player',now()))
                return 202,self._job(sid,'thread',{'thread_id':tid})
            tid = text(data.get('thread_id'),'thread_id',100)
            if not self.db.execute('SELECT 1 FROM threads WHERE id=? AND session_id=?',(tid,sid)).fetchone():
                raise APIError(404,'Thread not found')
            reply = data.get('reply_to')
            if reply is not None and (not isinstance(reply,str) or not self.db.execute('SELECT 1 FROM comments WHERE id=? AND session_id=? AND thread_id=?',(reply,sid,tid)).fetchone()):
                raise APIError(400,'Invalid reply_to')
            cid = uid()
            self.db.execute('INSERT INTO comments VALUES(?,?,?,?,?,?,?,?)',(cid,sid,tid,body,nickname,'player',now(),reply))
            return 202,self._job(sid,'comment',{'thread_id':tid,'target_comment':cid})
        result = self._transaction(save)
        self.wake.set()
        return result

    def _loop(self):
        while not self.stop.is_set():
            if not self.run_one():
                self.wake.wait(1)
                self.wake.clear()

    def run_one(self):
        def claim():
            job = self.db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at,rowid LIMIT 1").fetchone()
            if not job:
                return None
            if not self.gateway.configured:
                self.db.execute("UPDATE jobs SET status='failed',error='AI is not configured; explicit retry required' WHERE id=?",(job['id'],))
                return False
            calls = self.db.execute('SELECT calls FROM sessions WHERE id=?',(job['session_id'],)).fetchone()[0]
            if calls >= self.budget:
                self.db.execute("UPDATE jobs SET status='failed',error='Session AI budget exhausted' WHERE id=?",(job['id'],))
                return False
            self.db.execute('UPDATE sessions SET calls=calls+1 WHERE id=?',(job['session_id'],))
            self.db.execute("UPDATE jobs SET status='running',error=NULL WHERE id=?",(job['id'],))
            return dict(job)
        job = self._transaction(claim)
        if job is None:
            return False
        if job is False:
            return True
        try:
            sid = job['session_id']
            payload = json.loads(job['payload'])
            if job['kind'] == 'off_topic':
                # A strict allowlist: even persisted payloads must not inject game context.
                task = {'kind': 'off_topic', 'personas': self.personas}
            else:
                snap = self.snapshot(sid)
                if job['kind'] == 'notice':
                    # Older persisted notice jobs predate payload snapshots. Their original
                    # notice is immutable too; never inject the later result into them.
                    payload.setdefault('announcement', snap['announcement'])
                    payload.setdefault('result_announcement', None)
                    payload.setdefault('award_id', snap['award_id'] or 'couple')
                # Persisted jobs contain public identifiers/snapshots only. Never expand
                # arbitrary stored fields into provider context (including private settings).
                keys = {'notice': {'award_id', 'announcement', 'result_announcement'},
                        'result': {'announcement', 'result_announcement'},
                        'thread': {'thread_id'}, 'comment': {'thread_id', 'target_comment'}}
                payload = {key: value for key, value in payload.items() if key in keys.get(job['kind'], set())}
                # History is deliberately absent. Only the current session's recent public data.
                public = []
                for thread in snap['threads'][-12:]:
                    public.append(dict(thread, comments=thread['comments'][-12:]))
                target = next((t for t in snap['threads'] if t['id'] == payload.get('thread_id')), None)
                if target:
                    selected = target['comments'][-12:]
                    requested = next((c for c in target['comments'] if c['id'] == payload.get('target_comment')), None)
                    if requested and requested not in selected:
                        selected = [requested] + selected
                    target = dict(target, comments=selected)
                task = {'kind': job['kind'], 'award_id': snap['award_id'] or 'couple', 'personas': self.personas, 'announcement':snap['announcement'], 'result_announcement':snap['result_announcement'], 'threads':public, 'recent_memory':public[-4:], 'target_thread':target, **payload}
            result = self.gateway.generate(task)
            try:
                validated = self._validate(job['kind'], result, payload)
            except ValueError as exc:
                category = str(exc)
                safe = {'identity/schema': 'identity or fields', 'reply': 'reply index', 'schema': 'root fields', 'comment count': 'comment count', 'thread count': 'thread count'}
                raise AIError('AI schema invalid: ' + safe.get(category, 'structure')) from None
            except APIError:
                raise AIError('AI schema invalid: text length or type') from None
            def commit():
                if job['kind'] in ('notice', 'result', 'off_topic'):
                    for t in validated:
                        tid = uid()
                        self.db.execute('INSERT INTO threads VALUES(?,?,?,?,?,?,?)',(tid,sid,t['title'],t['body'],t['nickname'],'ai',now()))
                        ids = []
                        for c in t['comments']:
                            cid = uid()
                            reply = ids[c['reply_to']] if c['reply_to'] is not None else None
                            self._insert_comment(cid,sid,tid,c,reply)
                            ids.append(cid)
                else:
                    ids = []
                    for c in validated:
                        cid = uid()
                        reply = ids[c['reply_to']] if type(c['reply_to']) is int else c['reply_to']
                        self._insert_comment(cid,sid,payload['thread_id'],c,reply)
                        ids.append(cid)
                self.db.execute("UPDATE jobs SET status='succeeded',error=NULL WHERE id=?",(job['id'],))
            self._transaction(commit)
        except Exception as exc:
            error = str(exc) if isinstance(exc, AIError) else 'AI output invalid or task failed'
            with self.lock:
                self.db.execute("UPDATE jobs SET status='failed',error=? WHERE id=?",(error,job['id']))
        return True

    def _insert_comment(self,cid,sid,tid,c,reply):
        self.db.execute('INSERT INTO comments VALUES(?,?,?,?,?,?,?,?)',(cid,sid,tid,c['body'],c['nickname'],'ai',now(),reply))

    def _validate(self,kind,result,payload):
        def content(obj, fields):
            if not isinstance(obj,dict) or set(obj) != fields:
                raise ValueError('identity/schema')
            nickname = obj.get('nickname')
            if not isinstance(nickname, str) or nickname.strip() not in self.names:
                raise ValueError('identity/schema')
            # Harmless surrounding whitespace is not a different persona.
            obj['nickname'] = nickname.strip()
            text(obj.get('body'),'body',3000 if 'title' in fields else 1200)
            if 'title' in fields:
                text(obj.get('title'),'title',100)
        def comments(items, notice=False):
            if not isinstance(items,list) or not 1 <= len(items) <= 4:
                raise ValueError('comment count')
            for i,c in enumerate(items):
                content(c,{'nickname','body','reply_to'})
                reply = c['reply_to']
                if reply is None:
                    continue
                if type(reply) is int:
                    if not 0 <= reply < i:
                        raise ValueError('reply')
                elif not notice and isinstance(reply, str) and reply == payload.get('target_comment'):
                    continue
                else:
                    raise ValueError('reply')
        expected = 'threads' if kind in ('notice', 'result', 'off_topic') else 'comments'
        if not isinstance(result,dict) or set(result) != {expected}:
            # Report known protocol fields only, never arbitrary model-controlled keys.
            actual = 'threads' if isinstance(result,dict) and set(result) == {'threads'} else 'comments' if isinstance(result,dict) and set(result) == {'comments'} else 'other'
            raise AIError(f'AI schema invalid: expected {expected}, received {actual}')
        if kind in ('notice', 'result', 'off_topic'):
            items = result['threads']
            if not isinstance(items,list):
                raise AIError('AI schema invalid: thread count (expected 3, received non-array)')
            if len(items) != 3:
                raise AIError(f'AI schema invalid: thread count (expected 3, received {len(items)})')
            for t in items:
                content(t,{'nickname','title','body','comments'})
                comments(t['comments'],True)
                if kind == 'off_topic' and len(t['comments']) != 2:
                    raise ValueError('comment count')
            return items
        comments(result['comments'])
        return result['comments']
