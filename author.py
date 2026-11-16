"""离线作者流水线；旧聊天内核只提供设定校验与稳定游戏包协议。"""
import copy
import json
import re
import threading
import uuid
import urllib.error
import socket
from datetime import date, datetime, timezone
from pathlib import Path

import runtime as r
from prompt_catalog import load_catalog

SCHEMA = 'model-couple-author-project-v1'
PREPARATION_SCHEMA = 'model-couple-preparation-package-v1'
STAGES = ('chronos', 'disclosure', 'script', 'attitude')
AGENTS = {'chronos': 'Chronos', 'disclosure': 'Icelos', 'script': 'Muse', 'attitude': 'Icelos'}
ALIASES = {'CriticP': 'C_Prometheus', 'Critic_P': 'C_Prometheus', 'CriticC': 'C_Cupid', 'Critic_C': 'C_Cupid', 'CriticA': 'C_Aphrodite', 'Critic_A': 'C_Aphrodite', 'CriticM': 'C_Mnemosyne', 'Critic_M': 'C_Mnemosyne', 'Critic_I': 'C_Mnemosyne'}


def now():
    return datetime.now(timezone.utc).isoformat()


def fields(value, keys):
    r.require(isinstance(value, dict) and set(value) == set(keys), '字段不完整或有未知字段：' + ', '.join(keys))


def day(value, low='2025-04-24', high='2025-05-04'):
    r.require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), '日期须为ISO日期')
    date.fromisoformat(value)
    r.require(low <= value <= high, f'日期须在{low}至{high}')
    return value


def strings(value, empty=True):
    r.require(isinstance(value, list) and (empty or value) and all(r.text(x) for x in value), '文本列表无效')


def notice():
    result = r.announcement()
    result['body'] = result['body'].replace('5月5日周一公布入围名单，5月10日周六答辩', '5月5日周一由玩家决定并发布入围名单，5月10日周六答辩现场颁奖')
    result['body'] = result['body'].replace('本模拟不会自动填表或提交，讨论或口头愿意均不等于已经报名', '离线作者可创作填表过程；只有双方明确同意、正文齐备且日期合法才能形成提交快照。不得预判入围或获奖')
    return result


def own_sources(p, sid):
    pack = next(x for x in p['setting']['takeover_packages'] if x['student_id'] == sid)
    sources = {}
    # 私有信息可被本人和本人审查者读取，但不能进入披露包。
    for key in ('initial_memories', 'private_information'):
        for i, item in enumerate(pack[key]):
            sources[f'own.{key}.{i}'] = item['text']
    if p['locks'].get('chronos'):
        person = p['results']['chronos']['people'][sid]
        for i, item in enumerate(person['experiences']):
            sources[f'own.experiences.{i}'] = item['text']
        sources['own.registration_attitude'] = person['attitude']
        sources['own.form_text'] = person['form']['text']
        sources['own.form_status'] = person['form']['status']
        sources['own.consent'] = '本人明确同意参评' if person['consent'] else '本人未同意参评'
        sources['public.registration_status'] = p['results']['chronos']['registration']['status']
    return sources


def current_stage(p):
    return next((stage for stage in STAGES if not p['locks'].get(stage)), 'done')


def task(p):
    stage = current_stage(p)
    if stage == 'done' or not p['award_enabled']:
        return None
    if stage != 'chronos' and not p['nomination']:
        return None
    sid = p['members'][p['person_index']] if stage in ('disclosure', 'attitude') else None
    creator = AGENTS[stage]
    return {'stage': stage, 'student_id': sid, 'agent': 'C_' + creator if p['reviewing'] else creator, 'reviewing': p['reviewing']}


def forbidden_claims(value):
    raw = json.dumps(value, ensure_ascii=False)
    r.require(not re.search(r'(?:已经|已|确定|必然)(?:入围|获奖)|荣获优秀情侣奖', raw), '不得创作既定入围或获奖结果')


def validate_chronos(value, p):
    fields(value, ('summary', 'people', 'registration'))
    r.require(r.text(value['summary']), 'Chronos摘要缺失')
    fields(value['people'], p['members'])
    for sid, person in value['people'].items():
        fields(person, ('experiences', 'attitude', 'consent', 'form'))
        r.require(isinstance(person['experiences'], list), '经历须为列表')
        previous = '2025-04-24'
        for item in person['experiences']:
            fields(item, ('date', 'text'))
            day(item['date']); r.require(item['date'] >= previous and r.text(item['text']), '经历顺序或正文无效')
            previous = item['date']
        r.require(r.text(person['attitude']) and type(person['consent']) is bool, '态度或本人同意缺失')
        form = person['form']
        fields(form, ('status', 'filled', 'started_on', 'completed_on', 'text'))
        r.require(form['status'] in ('not_filled', 'partial', 'complete') and type(form['filled']) is bool and isinstance(form['text'], str), '个人填表状态无效')
        if form['status'] == 'not_filled':
            r.require(form == {'status': 'not_filled', 'filled': False, 'started_on': None, 'completed_on': None, 'text': ''}, '未填状态不得夹带正文或日期')
        else:
            r.require(form['filled'] is True and r.text(form['text']), '已填须有实际正文')
            day(form['started_on'])
            if form['status'] == 'complete':
                day(form['completed_on']); r.require(form['completed_on'] >= form['started_on'], '完成早于开始')
            else:
                r.require(form['completed_on'] is None, 'partial不可声明完成')
    reg = value['registration']
    fields(reg, ('status', 'submitted_on', 'withdrawn_on'))
    r.require(reg['status'] in ('not_submitted', 'submitted', 'withdrawn'), '报名状态无效')
    if reg['status'] == 'not_submitted':
        r.require(reg['submitted_on'] is None and reg['withdrawn_on'] is None, '未交状态日期须为空')
    else:
        day(reg['submitted_on'])
        for person in value['people'].values():
            r.require(person['consent'] is True and person['form']['status'] == 'complete' and person['form']['completed_on'] <= reg['submitted_on'], '提交须双方明确同意且两正文已在提交日前完成')
        if reg['status'] == 'withdrawn':
            day(reg['withdrawn_on']); r.require(reg['withdrawn_on'] >= reg['submitted_on'], '撤回早于提交')
        else:
            r.require(reg['withdrawn_on'] is None, 'submitted不得含撤回日期')
    forbidden_claims(value)
    return value


def validate_disclosure(value, p, sid):
    fields(value, ('student_id', 'items', 'stance'))
    r.require(value['student_id'] == sid and r.text(value['stance']), '披露身份或态度无效')
    sources = own_sources(p, sid)
    r.require(isinstance(value['items'], list), '披露须为列表')
    ids = set()
    for item in value['items']:
        fields(item, ('id', 'text', 'source_refs', 'teacher_knows', 'may_write', 'may_perform'))
        r.require(r.text(item['id'], 200) and item['id'] not in ids and r.text(item['text']), '披露ID重复或正文缺失'); ids.add(item['id'])
        r.require(all(type(item[k]) is bool for k in ('teacher_knows', 'may_write', 'may_perform')), '披露授权必须明确为布尔值')
        r.require(not item['may_write'] or item['teacher_knows'], '可写稿须教师获准知情')
        r.require(not item['may_perform'] or item['may_write'], '可表演须可写稿')
        refs = item['source_refs']; strings(refs, False)
        r.require(all(ref in sources and not ref.startswith('own.private_information.') for ref in refs), '披露引用越权或指向隐瞒秘密')
        # 保守采用逐字摘录，避免把无权限原文包裹在任意概述里。
        r.require(all(item['text'] in str(sources[ref]) for ref in refs), '披露正文须为获准来源的逐字摘录')
        secrets = [str(v) for k, v in sources.items() if k.startswith('own.private_information.')]
        r.require(not any(secret and secret in item['text'] for secret in secrets), '披露正文不得附带隐瞒秘密原文')
    forbidden_claims(value)
    return value


def muse_sources(p):
    sources = {}
    for sid in p['members']:
        for item in p['results']['disclosure'][sid]['items']:
            if item['teacher_knows']:
                sources[f'disclosure.{sid}.{item["id"]}'] = {k: copy.deepcopy(item[k]) for k in ('text', 'may_write', 'may_perform')}
    for page in p['game_snapshot']['player_visible']['application']['pages']:
        sid = page['student_id']
        authorization = [item for item in p['results']['disclosure'][sid]['items'] if 'own.form_text' in item['source_refs'] and item['text'] == page['个人陈述（300字左右）']]
        sources[f'application.{sid}'] = {'text': page['个人陈述（300字左右）'], 'may_write': any(item['may_write'] for item in authorization), 'may_perform': any(item['may_perform'] for item in authorization)}
    return sources


def validate_script(value, p):
    fields(value, ('title', 'characters', 'scenes', 'backstage'))
    r.require(r.text(value['title']) and value['characters'] == p['members'], '剧本人物必须为当前两人ID，不按性别编码')
    r.require(isinstance(value['scenes'], list) and value['scenes'], '剧本须有场景')
    strings(value['backstage'])
    sources = muse_sources(p); ids = set()
    for scene in value['scenes']:
        fields(scene, ('id', 'title', 'beats'))
        r.require(r.text(scene['id'], 200) and scene['id'] not in ids and r.text(scene['title']), '场景ID或标题无效'); ids.add(scene['id'])
        r.require(isinstance(scene['beats'], list) and scene['beats'], '场景须有段落')
        for beat in scene['beats']:
            fields(beat, ('id', 'performers', 'kind', 'text', 'action', 'emotion', 'duration_seconds', 'source_refs', 'framing'))
            r.require(r.text(beat['id'], 200) and beat['id'] not in ids, '段落ID重复'); ids.add(beat['id'])
            r.require(isinstance(beat['performers'], list) and 1 <= len(beat['performers']) <= 2 and len(set(beat['performers'])) == len(beat['performers']) and all(x in p['members'] for x in beat['performers']), '表演人物越权')
            r.require(beat['kind'] in ('dialogue', 'action', 'chorus') and (beat['kind'] != 'chorus' or len(beat['performers']) == 2), '段落类型或合唱人数无效')
            r.require(all(isinstance(beat[k], str) for k in ('text', 'action', 'emotion')) and (r.text(beat['text']) or r.text(beat['action'])), '台词或动作缺失')
            r.require(type(beat['duration_seconds']) in (int, float) and 0 < beat['duration_seconds'] <= 600, '段落时长无效')
            r.require(beat['framing'] in ('fact', 'interpretation', 'staging'), '事实、解释和舞台包装须区分')
            strings(beat['source_refs'], False)
            r.require(all(ref in sources and sources[ref]['may_write'] and sources[ref]['may_perform'] for ref in beat['source_refs']), '剧本来源未授权写作或表演')
            if beat['framing'] == 'fact':
                r.require(any(beat['text'] in sources[ref]['text'] for ref in beat['source_refs']), '事实台词须引用原文，改写须标记interpretation/staging并审核')
    forbidden_claims(value)
    return value


def beat_ids(p):
    return [b['id'] for scene in p['results']['script']['scenes'] for b in scene['beats']]


def validate_attitude(value, p, sid):
    fields(value, ('student_id', 'reactions', 'cooperation', 'memory'))
    r.require(value['student_id'] == sid and r.text(value['cooperation']) and r.text(value['memory']), '个人反应身份或准备心态缺失')
    r.require(isinstance(value['reactions'], list) and value['reactions'], '须有具体段落反应')
    seen = set()
    for item in value['reactions']:
        fields(item, ('beat_id', 'feeling', 'reason', 'readiness'))
        r.require(item['beat_id'] in beat_ids(p) and item['beat_id'] not in seen, '反应须指向唯一具体段落'); seen.add(item['beat_id'])
        r.require(item['feeling'] in ('like', 'dislike', 'mixed', 'neutral') and r.text(item['reason']) and r.text(item['readiness']), '段落喜恶、理由或配合心态缺失')
    return value




def messages(p, t):
    catalog = load_catalog()['author']
    templates, schemas = catalog['templates'], catalog['schemas']
    stage, sid = t['stage'], t['student_id']
    rule = templates['rule_3'] + t['agent'] + templates['rule_0']
    stage_schema = {stage: schemas[stage.upper() + '_SCHEMA'] for stage in STAGES}
    if stage == 'chronos':
        payload = {'date_range': ['2025-04-24', '2025-05-04'], 'announcement': p['announcement'], 'people': {x: {'sources': own_sources(p, x)} for x in p['members']}}
        rule += templates['rule_1']
    elif stage == 'disclosure':
        payload = {'student_id': sid, 'sources': own_sources(p, sid)}
        rule += templates['rule_4']
    elif stage == 'script':
        payload = {'announcement': p['announcement'], 'application': p['game_snapshot']['player_visible']['application'], 'disclosure_sources': muse_sources(p), 'members': p['members']}
        rule += templates['rule_5']
    else:
        payload = {'student_id': sid, 'sources': own_sources(p, sid), 'script': {k: p['results']['script'][k] for k in ('title', 'characters', 'scenes')}}
        rule += templates['rule_6']
    if t['reviewing']:
        payload['candidate'] = p['draft']
        rule += templates['rule_2']
    elif p['draft'] is not None:
        payload['previous_draft'] = p['draft']; payload['revision_requests'] = p['last_review']
    if p.get('failure'):
        payload['validation_feedback'] = p['failure']['message']
    return [{'role': 'system', 'content': rule + templates['rule_7'] + json.dumps(schemas['REVIEW_SCHEMA'] if t['reviewing'] else stage_schema[stage], ensure_ascii=False)}, {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}]



def demo(p, t):
    if t['reviewing']:
        # 这是明确的固定mock响应，而非程序替真实模型生成通过记录。
        return {'approved': True, 'summary': '固定示例审查响应；非真实模型审核', 'issues': []}
    stage, sid = t['stage'], t['student_id']
    if stage == 'chronos':
        people = {}
        for x in p['members']:
            source = next(v for k, v in own_sources(p, x).items() if k.startswith('own.initial_memories.'))
            people[x] = {'experiences': [{'date': '2025-04-26', 'text': '收到公告后仍按原课表生活；我回想起：' + source}], 'attitude': '愿意用本人记忆写陈述，不承诺结果', 'consent': True, 'form': {'status': 'complete', 'filled': True, 'started_on': '2025-04-28', 'completed_on': '2025-05-02', 'text': '我想保留自己的理解：' + source}}
        return {'summary': '固定示例：日常延续与自愿报名', 'people': people, 'registration': {'status': 'submitted', 'submitted_on': '2025-05-03', 'withdrawn_on': None}}
    if stage == 'disclosure':
        ref = next(k for k in own_sources(p, sid) if k.startswith('own.initial_memories.'))
        return {'student_id': sid, 'items': [{'id': 'd1', 'text': own_sources(p, sid)[ref], 'source_refs': [ref], 'teacher_knows': True, 'may_write': True, 'may_perform': True}, {'id': 'form', 'text': own_sources(p, sid)['own.form_text'], 'source_refs': ['own.form_text'], 'teacher_knows': True, 'may_write': True, 'may_perform': True}], 'stance': '只披露这段并授权本人正式正文用于准备表演，私有信息不附给教师'}
    if stage == 'script':
        beats = [{'id': 'beat' + str(i + 1), 'performers': [x], 'kind': 'dialogue', 'text': muse_sources(p)['application.' + x]['text'], 'action': '看向同伴，停顿后开口', 'emotion': '认真但保留迟疑', 'duration_seconds': 25, 'source_refs': ['application.' + x], 'framing': 'fact'} for i, x in enumerate(p['members'])]
        return {'title': '不同步的课表', 'characters': p['members'], 'scenes': [{'id': 'scene1', 'title': '各自讲述', 'beats': beats}], 'backstage': ['教师希望指导成果被认可；不构成获奖事实或必须服从的规则。']}
    return {'student_id': sid, 'reactions': [{'beat_id': bid, 'feeling': 'mixed', 'reason': '认可真实表达，但担心停顿显得刻意', 'readiness': '愿意准备，现场仍可改变表达'} for bid in beat_ids(p)], 'cooperation': '准备采用，但不承诺照本宣科', 'memory': '5月5日我读过共同剧本，对具体段落有保留。'}


def validate_result(value, p, t):
    if t['reviewing']:
        fields(value, ('approved', 'summary', 'issues'))
        r.require(type(value['approved']) is bool and r.text(value['summary']), '审查结构无效')
        strings(value['issues']); r.require(value['approved'] == (value['issues'] == []), '审查通过状态与问题矛盾')
        return value
    return {'chronos': lambda: validate_chronos(value, p), 'disclosure': lambda: validate_disclosure(value, p, t['student_id']), 'script': lambda: validate_script(value, p), 'attitude': lambda: validate_attitude(value, p, t['student_id'])}[t['stage']]()


def make_game(p):
    chronos = p['results']['chronos']; submitted = chronos['registration']['submitted_on']
    old = {'setting': p['setting'], 'session_id': p['project_id'], 'members': p['members'], 'date': submitted,
           'statements': {sid: {'text': person['form']['text'], 'versions': [{'version': 1}]} for sid, person in chronos['people'].items()}}
    candidate = r.application_candidate(old)
    app = candidate['application']; app.update(title='2025年优秀情侣奖双人申请表（游戏内已提交）', status='游戏内已提交', notice=r.SUBMISSION_NOTICE)
    for page in app['pages']:
        page.update(参与确认='操作者声明双方已授权本版本（非学生签署）', 提交状态='游戏内已提交')
    packs = {x['student_id']: copy.deepcopy(x) for x in p['setting']['takeover_packages'] if x['student_id'] in p['members']}
    for pack in packs.values():
        for key in ('initial_memories', 'private_information'):
            pack[key] = [{'text': item['text']} for item in pack[key]]
    package = {'schema_version': r.GAME_SCHEMA, 'submission': {'version': 1, 'submitted_at_system': now(), 'submitted_at_story': submitted, 'actor': 'operator', 'both_authorized': True, 'candidate_token': r.digest(candidate), 'statement_versions': candidate['statement_versions'], 'notice': r.SUBMISSION_NOTICE}, 'source': candidate['source'], 'player_visible': {'application': app}, 'role_private': {'students': {x['id']: copy.deepcopy(x) for x in p['setting']['students'] if x['id'] in p['members']}, 'relationship': copy.deepcopy(next(x for x in p['setting']['couples'] if x['id'] == p['couple_id'])), 'takeover_by_student_id': packs}, 'privacy_notice': r.PRIVACY_NOTICE}
    return r.validate_game_package(package)


class Engine:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else r.DATA / 'author_projects'
        self.lock = threading.RLock()
        self.busy = set()

    def path(self, pid):
        r.require(isinstance(pid, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}_[a-f0-9]{32}', pid), '工程ID无效')
        path = self.directory / (pid + '.json')
        r.require(not self.directory.is_symlink() and not path.is_symlink(), '工程路径无效')
        return path

    def save(self, p):
        self.directory.mkdir(exist_ok=True)
        path = self.path(p['project_id']); temp = path.with_suffix('.tmp')
        r.require(not temp.is_symlink(), '临时路径无效')
        temp.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding='utf-8'); temp.replace(path)

    def load(self, pid):
        p = json.loads(self.path(pid).read_text(encoding='utf-8'))
        self.validate_project(p)
        if p['status'] == 'running' and pid not in self.busy:
            p['status'] = 'paused'; self.save(p)
        return p

    def create(self, setting, couple_id, mode='demo', award_enabled=False):
        setting = r.validate_setting(setting)
        r.require(mode in ('demo', 'api') and (mode != 'api' or setting['mode'] == 'api') and type(award_enabled) is bool, '模式无效')
        couple = next((x for x in setting['couples'] if x['id'] == couple_id), None)
        r.require(couple is not None, '情侣ID无效')
        p = {'schema_version': SCHEMA, 'project_id': datetime.now().strftime('%Y-%m-%d_') + uuid.uuid4().hex, 'setting': setting, 'couple_id': couple_id, 'members': couple['members'], 'mode': mode, 'award_enabled': award_enabled, 'announcement': notice() if award_enabled else None, 'status': 'paused', 'reviewing': False, 'person_index': 0, 'draft': None, 'last_review': None, 'results': {}, 'locks': {}, 'versions': [], 'reviews': [], 'logs': [], 'failure': None, 'nomination': None, 'game_snapshot': None, 'calls': 0}
        self.save(p)
        return p

    def validate_project(self, p):
        fields(p, ('schema_version', 'project_id', 'setting', 'couple_id', 'members', 'mode', 'award_enabled', 'announcement', 'status', 'reviewing', 'person_index', 'draft', 'last_review', 'results', 'locks', 'versions', 'reviews', 'logs', 'failure', 'nomination', 'game_snapshot', 'calls'))
        r.require(p['schema_version'] == SCHEMA and len(json.dumps(p).encode()) <= 20 * 1024 * 1024, '工程版本或体积无效')
        self.path(p['project_id']); r.validate_setting(p['setting'])
        couple = next((x for x in p['setting']['couples'] if x['id'] == p['couple_id']), None)
        r.require(couple and p['members'] == couple['members'], '工程成员不一致')
        r.require(p['mode'] in ('demo', 'api') and (p['mode'] != 'api' or p['setting']['mode'] == 'api') and type(p['award_enabled']) is bool, '工程模式无效')
        r.require(p['announcement'] == (notice() if p['award_enabled'] else None), '工程公告无效')
        r.require(p['status'] in ('paused', 'ready', 'running', 'failed', 'stopped') and type(p['reviewing']) is bool and type(p['person_index']) is int and 0 <= p['person_index'] <= 1, '工程游标无效')
        r.require(type(p['calls']) is int and p['calls'] >= 0 and all(isinstance(p[k], list) for k in ('versions', 'reviews', 'logs')), '工程记录无效')
        r.require(isinstance(p['locks'], dict) and set(p['locks']) <= set(STAGES) and isinstance(p['results'], dict) and set(p['results']) <= set(STAGES), '锁定阶段无效')
        seen_unlocked = False
        for stage in STAGES:
            locked = stage in p['locks']
            if not locked: seen_unlocked = True
            r.require(not locked or not seen_unlocked, '锁定阶段不可跳跃')
            r.require(not locked or stage in p['results'], '锁定阶段缺少结果')
            if stage not in p['results']: continue
            result = p['results'][stage]
            if stage == 'chronos': validate_chronos(result, p)
            elif stage == 'script': validate_script(result, p)
            else:
                r.require(isinstance(result, dict) and set(result) <= set(p['members']), '逐人结果越权')
                for sid, value in result.items():
                    (validate_disclosure if stage == 'disclosure' else validate_attitude)(value, p, sid)
                r.require(not locked or set(result) == set(p['members']), '锁定缺少个人结果')
            if locked:
                r.require(p['locks'][stage] == r.digest(result), '已锁定阶段被修改')
                subjects = p['members'] if stage in ('disclosure', 'attitude') else [None]
                for sid in subjects:
                    content = result[sid] if sid else result
                    r.require(any(x.get('stage') == stage and x.get('student_id') == sid and x.get('candidate_digest') == r.digest(content) and x.get('agent') == 'C_' + AGENTS[stage] and x.get('response', {}).get('approved') is True and x['response'].get('issues') == [] for x in p['reviews']), '缺少独立审查记录，不能伪造锁定')
        if p['game_snapshot'] is not None:
            r.validate_game_package(p['game_snapshot'])
            r.require(p['locks'].get('chronos') and p['results']['chronos']['registration']['status'] == 'submitted', '非已提交工程不得保存游戏包')
            r.require(make_game(p)['player_visible'] == p['game_snapshot']['player_visible'], '报名快照与锁定正文不一致')
        if p['nomination'] is not None:
            fields(p['nomination'], ('date', 'actor', 'event', 'snapshot_digest'))
            r.require(p['game_snapshot'] is not None and p['nomination'] == {'date': '2025-05-05', 'actor': 'operator', 'event': '玩家已决定入围', 'snapshot_digest': r.digest(p['game_snapshot'])}, '入围须为5/5外部操作者事件')
        r.require(not any(stage in p['results'] for stage in STAGES[1:]) or p['nomination'] is not None, '未外部入围禁止准备')
        pending = task(p)
        if p['draft'] is not None:
            r.require(pending is not None, '无活动任务不得夹带候选')
            validate_result(p['draft'], p, {**pending, 'reviewing': False})
        r.require(not p['reviewing'] or p['draft'] is not None, '审查阶段缺少候选')
        if p['last_review'] is not None:
            validate_result(p['last_review'], p, {'reviewing': True})
        for review in p['reviews']:
            r.require(isinstance(review, dict) and review.get('stage') in STAGES, '审查历史结构无效')
            validate_result(review.get('response'), p, {'reviewing': True})
        r.require(not any(stage in p['locks'] for stage in STAGES[1:]) or p['game_snapshot'] is not None, '准备锁定缺少提交快照')
        r.require(p['award_enabled'] or not p['results'] and not p['locks'] and not p['reviews'] and p['game_snapshot'] is None and p['nomination'] is None, '纯恋爱不得加载奖流程')
        return p

    def event(self, p, kind, t=None, detail=None):
        p['logs'].append({'time': now(), 'kind': kind, 'task': copy.deepcopy(t), 'detail': copy.deepcopy(detail)})

    def step(self, pid, call):
        with self.lock:
            p = self.load(pid); t = task(p)
            r.require(pid not in self.busy and p['status'] in ('paused', 'ready', 'failed') and t is not None, '当前阶段不可调用；检查停止状态或外部入围门槛')
            self.busy.add(pid); p['status'] = 'running'; p['calls'] += 1
            self.event(p, 'request', t); self.save(p)
        try:
            value = demo(p, t) if p['mode'] == 'demo' else call(messages(p, t))
            validate_result(value, p, t)
            with self.lock:
                current = self.load(pid)
                if current['status'] in ('stopped', 'paused'):
                    self.event(current, 'discarded_after_control', t); self.save(current); return current
                stage, sid = t['stage'], t['student_id']
                if not t['reviewing']:
                    current['draft'] = copy.deepcopy(value); current['reviewing'] = True
                    current['versions'].append({'task': t, 'value': copy.deepcopy(value), 'time': now()})
                else:
                    record = {'stage': stage, 'student_id': sid, 'agent': t['agent'], 'candidate_digest': r.digest(current['draft']), 'response': copy.deepcopy(value), 'time': now()}
                    current['reviews'].append(record); current['last_review'] = copy.deepcopy(value); current['reviewing'] = False
                    if value['approved']:
                        if sid:
                            current['results'].setdefault(stage, {})[sid] = current['draft']
                        else: current['results'][stage] = current['draft']
                        current['draft'] = None; current['last_review'] = None
                        if sid and current['person_index'] == 0: current['person_index'] = 1
                        else:
                            current['person_index'] = 0; current['locks'][stage] = r.digest(current['results'][stage])
                            if stage == 'chronos' and value['approved'] and current['results']['chronos']['registration']['status'] == 'submitted':
                                current['game_snapshot'] = make_game(current)
                current['status'] = 'ready'; current['failure'] = None
                self.event(current, 'response_committed', t, value); self.save(current); return current
        except Exception as error:
            with self.lock:
                current = self.load(pid)
                if current['status'] not in ('stopped', 'paused'):
                    # 不存放上游异常原文，以免服务商回显凭据；本地校验差异可安全反馈。
                    message = str(error)[:1000] if isinstance(error, ValueError) else '调用失败；当前步骤未提交，可重试。超时不保证上游停止，可能重复计费。'
                    http_status = error.code if isinstance(error, urllib.error.HTTPError) else None
                    retryable = (http_status in (408, 429) or http_status is not None and 500 <= http_status <= 599) if http_status is not None else isinstance(error, (ValueError, TimeoutError, socket.timeout, urllib.error.URLError))
                    current['status'] = 'failed'; current['failure'] = {'task': t, 'message': message, 'retryable': retryable}
                    self.event(current, 'failure', t, current['failure']); self.save(current)
                return current
        finally:
            with self.lock: self.busy.discard(pid)

    def control(self, pid, action):
        with self.lock:
            p = self.load(pid)
            r.require(action in ('pause', 'stop', 'resume'), '未知控制')
            r.require(not (action == 'resume' and pid in self.busy), '调用尚未结束，不能恢复并发执行')
            p['status'] = {'pause': 'paused', 'stop': 'stopped', 'resume': 'paused'}[action]
            self.event(p, action); self.save(p); return p

    def nominate(self, pid, event, event_date, confirmed):
        with self.lock:
            p = self.load(pid)
            r.require(pid not in self.busy and p['status'] != 'stopped' and p['game_snapshot'] is not None and p['nomination'] is None, '仅已提交且尚未准备的工程可录入入围')
            r.require(event == '玩家已决定入围' and event_date == '2025-05-05' and confirmed is True, '须操作者显式确认5/5玩家已决定入围，不由模型选择')
            p['nomination'] = {'date': event_date, 'actor': 'operator', 'event': event, 'snapshot_digest': r.digest(p['game_snapshot'])}
            self.event(p, 'external_nomination', detail=p['nomination']); self.save(p); return p

    def import_project(self, project):
        p = copy.deepcopy(project); self.validate_project(p)
        with self.lock:
            # 导入为新工程，不覆盖同ID在途或未保存的工作。
            p['project_id'] = datetime.now().strftime('%Y-%m-%d_') + uuid.uuid4().hex
            p['status'] = 'paused'; self.event(p, 'imported_paused'); self.save(p)
        return p

    def export(self, pid, kind):
        with self.lock:
            p = self.load(pid)
            if kind == 'project': return copy.deepcopy(p)
            if kind == 'background': return copy.deepcopy(p['setting'])
            r.require(p['game_snapshot'] is not None, '只有已提交报名快照可导出游戏包')
            if kind == 'game': return copy.deepcopy(p['game_snapshot'])
            r.require(kind == 'preparation' and current_stage(p) == 'done' and p['nomination'] is not None, '准备阶段尚未全部审查锁定')
            roles = {}
            for sid in p['members']:
                pack = p['game_snapshot']['role_private']['takeover_by_student_id'][sid]
                roles[sid] = {'student_id': sid, 'memories': [x['text'] for x in pack['initial_memories']], 'private_information': [x['text'] for x in pack['private_information']], 'experiences': copy.deepcopy(p['results']['chronos']['people'][sid]['experiences']), 'registration_attitude': p['results']['chronos']['people'][sid]['attitude'], 'own_registration': copy.deepcopy(p['results']['chronos']['people'][sid]['form']), 'registration_history': copy.deepcopy(p['results']['chronos']['registration']), 'preparation_attitude': copy.deepcopy(p['results']['attitude'][sid]), 'disclosure_stance': p['results']['disclosure'][sid]['stance']}
            script = p['results']['script']
            return {'schema_version': PREPARATION_SCHEMA, 'source_submission_digest': r.digest(p['game_snapshot']), 'nomination': copy.deepcopy(p['nomination']), 'common_script': {k: copy.deepcopy(script[k]) for k in ('title', 'characters', 'scenes')}, 'role_private_by_student_id': roles, 'notice': '准备采用不等于现场必须照做；仅学生参加未来现场，本包不含审核、后台意图或神名提示。分区非加密，消费端须隔离访问。'}

    def view(self, p):
        t = task(p)
        return {k: copy.deepcopy(p[k]) for k in ('project_id', 'mode', 'award_enabled', 'status', 'locks', 'results', 'draft', 'last_review', 'logs', 'failure', 'calls', 'nomination', 'members')} | {'task': t, 'stage': current_stage(p), 'can_nominate': p['game_snapshot'] is not None and p['nomination'] is None, 'can_export_game': p['game_snapshot'] is not None, 'can_export_preparation': current_stage(p) == 'done', 'names': {x['id']: x['name'] for x in p['setting']['students'] if x['id'] in p['members']}, 'application': copy.deepcopy(p['game_snapshot']['player_visible']['application']) if p['game_snapshot'] else None}

    def dispatch(self, action, data, call):
        expected = {'create': ('setting', 'couple_id', 'mode', 'award_enabled'), 'load': ('project_id',), 'step': ('project_id',), 'pause': ('project_id',), 'stop': ('project_id',), 'resume': ('project_id',), 'nominate': ('project_id', 'event', 'event_date', 'confirmed'), 'export': ('project_id', 'kind'), 'import': ('project',)}
        r.require(action in expected, '未知作者操作'); fields(data, expected[action])
        if action == 'create': p = self.create(**data)
        elif action == 'import': p = self.import_project(data['project'])
        elif action == 'export': return self.export(data['project_id'], data['kind'])
        elif action == 'nominate': p = self.nominate(data['project_id'], data['event'], data['event_date'], data['confirmed'])
        elif action == 'step': p = self.step(data['project_id'], call)
        elif action == 'load':
            with self.lock: p = self.load(data['project_id'])
        else: p = self.control(data['project_id'], action)
        return self.view(p)


ENGINE = Engine()
