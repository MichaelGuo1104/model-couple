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

SCHEMA = 'model-couple-author-project-v2'
PREPARATION_SCHEMA = 'model-couple-preparation-package-v1'
STAGES = ('chronos', 'application', 'disclosure', 'script', 'attitude')
AGENTS = {'chronos': 'Chronos', 'application': 'Muse', 'disclosure': 'Icelos', 'script': 'Muse', 'attitude': 'Icelos'}
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


def strings(value, empty=True, path='文本列表'):
    # Report shape only: never echo rejected text or private source contents.
    r.require(isinstance(value, list), f'{path}：须为JSON字符串数组，实际类型为{type(value).__name__}；不能用字符串、对象或null代替数组')
    r.require(empty or value, f'{path}：须为非空字符串数组，不能是[]')
    for index, item in enumerate(value):
        r.require(r.text(item), f'{path}[{index}]：须为1至20000字符的非空字符串，实际类型为{type(item).__name__}；不能放对象、嵌套数组、null或空白字符串')


def notice():
    result = r.announcement()
    result['body'] = result['body'].replace('仅说明双方自愿提供的共同经历与相互支持', '分别陈述个人学业、专业实践、成长、关系支持与参评理由')
    result['body'] = result['body'].replace('5月5日周一公布入围名单，5月10日周六答辩', '5月5日周一由玩家决定并发布入围名单，5月10日周六答辩现场颁奖')
    result['body'] = result['body'].replace('本模拟不会自动填表或提交，讨论或口头愿意均不等于已经报名', '离线作者可创作填表过程；只有双方明确同意、正文齐备且日期合法才能形成提交快照。不得预判入围或获奖')
    return result


def own_sources(p, sid):
    pack = next(x for x in p['setting']['takeover_packages'] if x['student_id'] == sid)
    sources = {}
    student = next(x for x in p['setting']['students'] if x['id'] == sid)
    # Mixed personal-life prose is visible only to its owner until explicitly disclosed.
    for key in ('grades', 'independent_life', 'voice'):
        if isinstance(student.get(key), str) and student[key].strip():
            sources['own.profile.' + key] = student[key]
    # 私有信息可被本人和本人审查者读取，但不能进入披露包。
    for key in ('initial_memories', 'private_information'):
        for i, item in enumerate(pack[key]):
            sources[f'own.{key}.{i}'] = item['text']
    if p['locks'].get('chronos'):
        person = p['results']['chronos']['people'][sid]
        for i, item in enumerate(person['experiences']):
            sources[f'own.experiences.{i}'] = item['text']
        sources['own.registration_attitude'] = person['attitude']
        if p['locks'].get('application'):
            sources['own.form_text'] = p['results']['application']['statements'][sid]
            sources['own.form_status'] = 'complete'
        sources['own.consent'] = '本人明确同意参评' if person['consent'] else '本人未同意参评'
        sources['public.registration_status'] = p['results']['chronos']['registration']['status']
    return sources


def current_stage(p):
    return next((stage for stage in STAGES if not p['locks'].get(stage)), 'done')


def task(p):
    stage = current_stage(p)
    if stage == 'done' or not p['award_enabled']:
        return None
    if stage in ('disclosure', 'script', 'attitude') and not p['nomination']:
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
        fields(person, ('experiences', 'attitude', 'consent'))
        r.require(isinstance(person['experiences'], list), '经历须为列表')
        previous = '2025-04-24'
        for item in person['experiences']:
            fields(item, ('date', 'text'))
            day(item['date']); r.require(item['date'] >= previous and r.text(item['text']), '经历顺序或正文无效')
            previous = item['date']
        r.require(r.text(person['attitude']) and type(person['consent']) is bool, '态度或本人同意缺失')
        r.require(person['consent'] is True, '剧情结局必须双方明确同意报名')
    reg = value['registration']
    fields(reg, ('status', 'submitted_on'))
    r.require(reg['status'] == 'submitted', '剧情必须以双方报名结束')
    day(reg['submitted_on'])
    forbidden_claims(value)
    return value


def validate_application(value, p):
    fields(value, ('statements', 'metadata'))
    fields(value['statements'], p['members'])
    r.require(all(r.text(text) for text in value['statements'].values()), '报名须双方第一人称正式陈述')
    fields(value['metadata'], ('both_authorized', 'privacy', 'submitted_on'))
    r.require(value['metadata']['both_authorized'] is True and r.text(value['metadata']['privacy']), '授权隐私须在元字段')
    r.require(value['metadata']['submitted_on'] == p['results']['chronos']['registration']['submitted_on'], '提交日期须承接剧情')
    forbidden_claims(value)
    return value


def validate_disclosure(value, p, sid, legacy=False):
    fields(value, ('student_id', 'items', 'stance'))
    r.require(value['student_id'] == sid and r.text(value['stance']), '披露身份或态度无效')
    sources = own_sources(p, sid)
    r.require(isinstance(value['items'], list), '披露须为列表')
    ids = set()
    for item_index, item in enumerate(value['items']):
        keys = ('id', 'text', 'source_refs')
        historical = ('teacher_knows', 'may_write', 'may_perform')
        if legacy and isinstance(item, dict) and set(item) == set(keys + historical):
            # 历史字段仅验证类型，保留原值以维持锁和审查摘要；业务不再使用。
            r.require(all(type(item[k]) is bool for k in historical), '历史披露字段须为布尔值')
        else:
            fields(item, keys)
        r.require(r.text(item['id'], 200) and item['id'] not in ids and r.text(item['text']), '披露ID重复或正文缺失'); ids.add(item['id'])
        refs = item['source_refs']; strings(refs, False)
        r.require(all(ref in sources and not ref.startswith('own.private_information.') for ref in refs), '披露引用越权或指向隐瞒秘密')
        # 保守采用逐字摘录，避免把无权限原文包裹在任意概述里。
        r.require(all(item['text'] in str(sources[ref]) for ref in refs), '披露正文须为获准来源的逐字摘录')
        secrets = [str(v) for k, v in sources.items() if k.startswith('own.private_information.')]
        r.require(not any(secret and secret in item['text'] for secret in secrets), '披露正文不得附带隐瞒秘密原文')
    forbidden_claims(value)
    return value


def public_profiles(p):
    # 当前学生结构没有独立的公开经历/学校字段；混合叙述须经本人披露，不能猜测提取。
    return {student['id']: {key: copy.deepcopy(student[key]) for key in ('name', 'major', 'year', 'grades')
                            if isinstance(student.get(key), str) and student[key].strip()}
            for student in p['setting']['students'] if student['id'] in p['members']}


def muse_sources(p):
    sources = {f'profile.{sid}.{key}': {'text': value}
               for sid, profile in public_profiles(p).items() for key, value in profile.items()}
    for sid in p['members']:
        for item in p['results']['disclosure'][sid]['items']:
            sources[f'disclosure.{sid}.{item["id"]}'] = {'text': copy.deepcopy(item['text'])}
    for page in p['game_snapshot']['player_visible']['application']['pages']:
        sid = page['student_id']
        disclosed = any('own.form_text' in item['source_refs'] and item['text'] == page['个人陈述（300字左右）'] for item in p['results']['disclosure'][sid]['items'])
        if disclosed:
            sources[f'application.{sid}'] = {'text': page['个人陈述（300字左右）']}
    return sources


def script_feasibility(p):
    ready = bool(p['locks'].get('disclosure'))
    refs = list(muse_sources(p)) if ready else []
    blocked = ready and not refs and not p['locks'].get('script')
    return {'blocked': blocked, 'code': 'no_disclosed_material' if blocked else None,
            'reason': '没有公开履历或已披露创作素材；可等待本人自愿补充披露，不自动重试，也不会调用 Muse。这是素材不足，不是授权检查。' if blocked else None,
            'allowed_refs': refs}


def can_replan_disclosure(p):
    return bool(p['award_enabled'] and p['nomination'] and p['locks'].get('chronos') and
                not any(stage in p['locks'] or stage in p['results'] for stage in ('script', 'attitude')))


def validate_script(value, p):
    fields(value, ('title', 'characters', 'scenes', 'backstage'))
    r.require(r.text(value['title']) and value['characters'] == p['members'], '剧本人物必须为当前两人ID，不按性别编码')
    r.require(isinstance(value['scenes'], list) and value['scenes'], '剧本须有场景')
    strings(value['backstage'], path='script.backstage')
    sources = muse_sources(p); ids = set()
    for scene_index, scene in enumerate(value['scenes']):
        fields(scene, ('id', 'title', 'beats'))
        r.require(r.text(scene['id'], 200) and scene['id'] not in ids and r.text(scene['title']), '场景ID或标题无效'); ids.add(scene['id'])
        r.require(isinstance(scene['beats'], list) and scene['beats'], '场景须有段落')
        for beat_index, beat in enumerate(scene['beats']):
            fields(beat, ('id', 'performers', 'kind', 'text', 'action', 'emotion', 'duration_seconds', 'source_refs', 'framing'))
            r.require(r.text(beat['id'], 200) and beat['id'] not in ids, '段落ID重复'); ids.add(beat['id'])
            r.require(isinstance(beat['performers'], list) and 1 <= len(beat['performers']) <= 2 and len(set(beat['performers'])) == len(beat['performers']) and all(x in p['members'] for x in beat['performers']), '表演人物越权')
            r.require(beat['kind'] in ('dialogue', 'action', 'chorus') and (beat['kind'] != 'chorus' or len(beat['performers']) == 2), '段落类型或合唱人数无效')
            r.require(all(isinstance(beat[k], str) for k in ('text', 'action', 'emotion')) and (r.text(beat['text']) or r.text(beat['action'])), '台词或动作缺失')
            r.require(type(beat['duration_seconds']) in (int, float) and 0 < beat['duration_seconds'] <= 600, '段落时长无效')
            r.require(beat['framing'] in ('fact', 'interpretation', 'staging'), 'framing须为兼容标签fact、interpretation或staging，不作真实性判断')
            strings(beat['source_refs'], False, f'script.scenes[{scene_index}].beats[{beat_index}].source_refs')
            for ref in beat['source_refs']:
                source = sources.get(ref)
                # 只反馈引用位置，不回显来源正文或未披露信息。
                r.require(source is not None, '剧本来源不在已披露素材中：' + json.dumps({'scene': scene['id'], 'beat': beat['id'], 'ref': ref}, ensure_ascii=False))
            # 引用仅追踪已披露的素材启发；兼容标签不要求台词与来源一致。
    raw = json.dumps(value, ensure_ascii=False)
    secrets = [item['text'] for pack in p['setting']['takeover_packages'] if pack['student_id'] in p['members'] for item in pack['private_information']]
    r.require(not any(secret and secret in raw for secret in secrets), '剧本不得夹带隐瞒秘密原文')
    # Stage speech never establishes registration, nomination or award state.
    # Those remain guarded by immutable snapshots and external-event validation.
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
    elif stage == 'application':
        payload = {'profiles': public_profiles(p), 'personal_practice': {s['id']: s['independent_life'] for s in p['setting']['students'] if s['id'] in p['members']}, 'chronos': p['results']['chronos'], 'announcement': p['announcement'], 'members': p['members']}
        rule += templates['application_writer']
    elif stage == 'disclosure':
        payload = {'student_id': sid, 'sources': own_sources(p, sid)}
        rule += templates['rule_4']
    elif stage == 'script':
        payload = {'announcement': p['announcement'], 'application': p['game_snapshot']['player_visible']['application'], 'profile': public_profiles(p), 'disclosure_sources': muse_sources(p), 'members': p['members']}
        payload['allowed_source_refs'] = list(payload['disclosure_sources'])
        payload['context_only_refs'] = ['application.' + member for member in p['members'] if 'application.' + member not in payload['disclosure_sources']]
        rule += templates['rule_5']
    else:
        payload = {'student_id': sid, 'sources': own_sources(p, sid), 'script': {k: p['results']['script'][k] for k in ('title', 'characters', 'scenes')}}
        rule += templates['rule_6']
    if t['reviewing']:
        payload['candidate'] = p['draft']
        rule += templates['application_critic'] if stage == 'application' else templates['rule_2']
    elif p['draft'] is not None:
        payload['previous_draft'] = p['draft']; payload['revision_requests'] = p['last_review']
    if p.get('failure'):
        feedback = p['failure']['message']
        obsolete = p['failure'].get('code') == 'insufficient_authorization' or any(marker in feedback for marker in ('可写稿须教师获准知情', '可表演须可写稿', '没有同时获准写作与表演', '剧本来源未授权写作或表演', '事实台词须引用原文'))
        if not obsolete:
            payload['validation_feedback'] = feedback
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
            people[x] = {'experiences': [{'date': '2025-04-26', 'text': '收到公告后仍按原课表生活；我回想起：' + source}], 'attitude': '愿意用本人记忆写陈述，不承诺结果', 'consent': True}
        return {'summary': '固定示例：日常延续与自愿报名', 'people': people, 'registration': {'status': 'submitted', 'submitted_on': '2025-05-03'}}
    if stage == 'application':
        return {'statements': {x: '各位评委好，我是' + next(s['name'] for s in p['setting']['students'] if s['id'] == x) + '。我的学业情况是' + public_profiles(p).get(x, {}).get('grades', '尚无公开成绩资料') + '。我希望在保持独立成长的同时与伴侣互相支持，申请优秀情侣奖。' for x in p['members']}, 'metadata': {'both_authorized': True, 'privacy': '授权与隐私仅作为提交元信息', 'submitted_on': p['results']['chronos']['registration']['submitted_on']}}
    if stage == 'disclosure':
        ref = next(k for k in own_sources(p, sid) if k.startswith('own.initial_memories.'))
        return {'student_id': sid, 'items': [{'id': 'd1', 'text': own_sources(p, sid)[ref], 'source_refs': [ref]}, {'id': 'form', 'text': own_sources(p, sid)['own.form_text'], 'source_refs': ['own.form_text']}], 'stance': '愿意披露这段及本人正式正文作为创作素材，私有信息不附给教师'}
    if stage == 'script':
        sources = muse_sources(p)
        beats = []
        for i, x in enumerate(p['members']):
            refs = [ref for ref in sources if ref.startswith('profile.' + x + '.') or ref == 'application.' + x or ref.startswith('disclosure.' + x + '.')]
            if not refs:
                continue
            profile = public_profiles(p).get(x, {})
            identity = '，'.join(profile[key] for key in ('name', 'major', 'year') if key in profile)
            achievement = '我的学业情况是' + profile['grades'] + '。' if 'grades' in profile else ''
            beats.append({'id': 'beat' + str(i + 1), 'performers': [x], 'kind': 'dialogue', 'text': f'各位评委好，我是{identity or x}。{achievement}我们今天用各自的成长和共同的互助，说明为什么申请优秀情侣奖。', 'action': '面向评委展示本人资料页，讲完后示意同伴接续陈述', 'emotion': '自信而克制，尊重同伴的独立表达', 'duration_seconds': 25, 'source_refs': refs, 'framing': 'interpretation'})
        shared_refs = [ref for ref in sources if ref.startswith('disclosure.')]
        if shared_refs:
            beats.append({'id': 'beat_mutual', 'performers': list(p['members']), 'kind': 'chorus', 'text': '我们想把彼此的支持包装成一座连接两条成长道路的桥：不是替对方生活，而是让各自的努力被看见。', 'action': '并列展示双方资料，分别指向自己的部分后停顿', 'emotion': '温暖且有分寸', 'duration_seconds': 20, 'source_refs': shared_refs, 'framing': 'staging'})
        if beats:
            beats.append({'id': 'beat_qa', 'performers': list(p['members']), 'kind': 'dialogue', 'text': '若被问到双方各自的优势和互助方式，我们先由本人说明，再请同伴补充；未准备到的问题，现场各自回应。感谢各位聆听，请提问。', 'action': '合上陈述资料，面向评委等待提问；这里只准备衔接，不预写玩家问题或现场结论', 'emotion': '从容、开放', 'duration_seconds': 15, 'source_refs': [beats[0]['source_refs'][0]], 'framing': 'staging'})
        return {'title': '各自成长，彼此成就——优秀情侣奖双人答辩准备稿', 'characters': p['members'], 'scenes': [{'id': 'scene1', 'title': '双人陈述、资料展示与问答准备', 'beats': beats}], 'backstage': ['教师以成长之桥宣传包装双方材料，可夸张改写甚至编造宣传情节；这是答辩准备，不是戏剧演出，也不决定情侣优劣。未知履历不补齐，不设置评分、权重或算法选优；加工不写回真实经历、报名快照或获奖结果。']}
    return {'student_id': sid, 'reactions': [{'beat_id': bid, 'feeling': 'mixed', 'reason': '认可真实表达，但担心停顿显得刻意', 'readiness': '愿意准备，现场仍可改变表达'} for bid in beat_ids(p)], 'cooperation': '准备采用，但不承诺照本宣科', 'memory': '5月5日我读过共同剧本，对具体段落有保留。'}


def validate_result(value, p, t):
    if t['reviewing']:
        fields(value, ('approved', 'summary', 'issues'))
        r.require(type(value['approved']) is bool and r.text(value['summary']), '审查结构无效')
        strings(value['issues']); r.require(value['approved'] == (value['issues'] == []), '审查通过状态与问题矛盾')
        return value
    return {'chronos': lambda: validate_chronos(value, p), 'application': lambda: validate_application(value, p), 'disclosure': lambda: validate_disclosure(value, p, t['student_id']), 'script': lambda: validate_script(value, p), 'attitude': lambda: validate_attitude(value, p, t['student_id'])}[t['stage']]()


def make_game(p):
    chronos = p['results']['chronos']; submitted = chronos['registration']['submitted_on']
    old = {'setting': p['setting'], 'session_id': p['project_id'], 'members': p['members'], 'date': submitted,
           'statements': {sid: {'text': text, 'versions': [{'version': 1}]} for sid, text in p['results']['application']['statements'].items()}}
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
        fields({k: v for k, v in p.items() if k != 'manual_revision'}, ('schema_version', 'project_id', 'setting', 'couple_id', 'members', 'mode', 'award_enabled', 'announcement', 'status', 'reviewing', 'person_index', 'draft', 'last_review', 'results', 'locks', 'versions', 'reviews', 'logs', 'failure', 'nomination', 'game_snapshot', 'calls'))
        r.require(p['schema_version'] == SCHEMA and len(json.dumps(p).encode()) <= 20 * 1024 * 1024, '工程版本或体积无效：新报名流程仅接受author v2；旧v1原档请保留为历史，不会静默迁移或补造审查')
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
            elif stage == 'application': validate_application(result, p)
            elif stage == 'script': validate_script(result, p)
            else:
                r.require(isinstance(result, dict) and set(result) <= set(p['members']), '逐人结果越权')
                for sid, value in result.items():
                    if stage == 'disclosure': validate_disclosure(value, p, sid, legacy=True)
                    else: validate_attitude(value, p, sid)
                r.require(not locked or set(result) == set(p['members']), '锁定缺少个人结果')
            if locked:
                r.require(p['locks'][stage] == r.digest(result), '已锁定阶段被修改')
                subjects = p['members'] if stage in ('disclosure', 'attitude') else [None]
                for sid in subjects:
                    content = result[sid] if sid else result
                    r.require((p.get('manual_revision', {}).get('approved_digests', {}).get(stage) == r.digest(result) and p['manual_revision'].get('actor') == 'operator' and p['manual_revision'].get('model_reviewed') is False) or any(x.get('stage') == stage and x.get('student_id') == sid and x.get('candidate_digest') == r.digest(content) and x.get('agent') == 'C_' + AGENTS[stage] and x.get('response', {}).get('approved') is True and x['response'].get('issues') == [] for x in p['reviews']), '缺少独立审查记录，不能伪造锁定')
        if p['game_snapshot'] is not None:
            r.validate_game_package(p['game_snapshot'])
            r.require(p['locks'].get('application') and p['results']['chronos']['registration']['status'] == 'submitted', '非已提交工程不得保存游戏包')
            r.require(make_game(p)['player_visible'] == p['game_snapshot']['player_visible'], '报名快照与锁定正文不一致')
        if p['nomination'] is not None:
            fields(p['nomination'], ('date', 'actor', 'event', 'snapshot_digest'))
            r.require(p['game_snapshot'] is not None and p['nomination'] == {'date': '2025-05-05', 'actor': 'operator', 'event': '玩家已决定入围', 'snapshot_digest': r.digest(p['game_snapshot'])}, '入围须为5/5外部操作者事件')
        r.require(not any(stage in p['results'] for stage in STAGES[2:]) or p['nomination'] is not None, '未外部入围禁止准备')
        pending = task(p)
        if p['draft'] is not None:
            r.require(pending is not None, '无活动任务不得夹带候选')
            if pending['stage'] == 'disclosure':
                validate_disclosure(p['draft'], p, pending['student_id'], legacy=True)
            else:
                validate_result(p['draft'], p, {**pending, 'reviewing': False})
        r.require(not p['reviewing'] or p['draft'] is not None, '审查阶段缺少候选')
        if p['last_review'] is not None:
            validate_result(p['last_review'], p, {'reviewing': True})
        for review in p['reviews']:
            r.require(isinstance(review, dict) and review.get('stage') in STAGES, '审查历史结构无效')
            validate_result(review.get('response'), p, {'reviewing': True})
        r.require(not any(stage in p['locks'] for stage in STAGES[2:]) or p['game_snapshot'] is not None, '准备锁定缺少提交快照')
        r.require(p['award_enabled'] or not p['results'] and not p['locks'] and not p['reviews'] and p['game_snapshot'] is None and p['nomination'] is None, '纯恋爱不得加载奖流程')
        return p

    def event(self, p, kind, t=None, detail=None):
        p['logs'].append({'time': now(), 'kind': kind, 'task': copy.deepcopy(t), 'detail': copy.deepcopy(detail)})

    def step(self, pid, call):
        with self.lock:
            p = self.load(pid); t = task(p)
            r.require(pid not in self.busy and p['status'] in ('paused', 'ready', 'failed') and t is not None, '当前阶段不可调用；检查停止状态或外部入围门槛')
            feasibility = script_feasibility(p)
            if t['stage'] == 'script' and feasibility['blocked']:
                p['status'] = 'failed'
                p['failure'] = {'task': t, 'message': feasibility['reason'], 'code': feasibility['code'], 'retryable': False}
                if not p['logs'] or p['logs'][-1].get('detail') != p['failure']:
                    self.event(p, 'failure', t, p['failure'])
                self.save(p)
                return p
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
                            if stage == 'application' and value['approved']:
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

    def replan_disclosure(self, pid, confirmed):
        with self.lock:
            p = self.load(pid)
            r.require(confirmed is True, '须用户显式确认重新规划披露／补充披露')
            r.require(pid not in self.busy and p['status'] != 'stopped' and can_replan_disclosure(p), '已有剧本／态度结果或锁定、未入围或请求在途，不能重新规划披露')
            previous = {key: copy.deepcopy(p[key]) for key in ('draft', 'last_review', 'failure', 'reviewing', 'person_index')}
            previous['disclosure'] = copy.deepcopy(p['results'].get('disclosure'))
            previous['disclosure_lock'] = p['locks'].get('disclosure')
            # versions 的阶段保存在 task 中；不能按顶层 stage 过滤。
            for key in ('reviews', 'versions'):
                def is_disclosure(row):
                    return (row.get('task') or {}).get('stage') == 'disclosure' if key == 'versions' else row.get('stage') == 'disclosure'
                previous[key] = copy.deepcopy([row for row in p[key] if is_disclosure(row)])
                p[key] = [row for row in p[key] if not is_disclosure(row)]
            previous['reason'] = '用户显式确认重新规划披露；旧披露及其审查仅留作审计，不作为当前创作素材'
            self.event(p, 'disclosure_replanned', {'stage': 'disclosure', 'student_id': None, 'agent': 'operator', 'reviewing': False}, previous)
            p['results'].pop('disclosure', None); p['locks'].pop('disclosure', None)
            p.update(status='paused', draft=None, last_review=None, failure=None, reviewing=False, person_index=0)
            self.validate_project(p); self.save(p)
            return p

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
                roles[sid] = {'student_id': sid, 'memories': [x['text'] for x in pack['initial_memories']], 'private_information': [x['text'] for x in pack['private_information']], 'experiences': copy.deepcopy(p['results']['chronos']['people'][sid]['experiences']), 'registration_attitude': p['results']['chronos']['people'][sid]['attitude'], 'own_registration': {'status': 'complete', 'text': p['results']['application']['statements'][sid]}, 'registration_history': copy.deepcopy(p['results']['chronos']['registration']), 'preparation_attitude': copy.deepcopy(p['results']['attitude'][sid]), 'disclosure_stance': p['results']['disclosure'][sid]['stance']}
            script = p['results']['script']
            return {'schema_version': PREPARATION_SCHEMA, 'source_submission_digest': r.digest(p['game_snapshot']), 'nomination': copy.deepcopy(p['nomination']), 'common_script': {k: copy.deepcopy(script[k]) for k in ('title', 'characters', 'scenes')}, 'role_private_by_student_id': roles, 'notice': '准备采用不等于现场必须照做；仅学生参加未来现场，本包不含审核、后台意图或神名提示。分区非加密，消费端须隔离访问。'}

    def view(self, p):
        t = task(p)
        return {k: copy.deepcopy(p[k]) for k in ('project_id', 'mode', 'award_enabled', 'status', 'locks', 'results', 'draft', 'last_review', 'logs', 'failure', 'calls', 'nomination', 'members')} | {'manual_revision': {k: copy.deepcopy(v) for k, v in p.get('manual_revision', {}).items() if k != 'original_author'}, 'task': t, 'stage': current_stage(p), 'script_feasibility': script_feasibility(p), 'can_replan_disclosure': can_replan_disclosure(p) and p['project_id'] not in self.busy and p['status'] != 'stopped', 'can_nominate': p['game_snapshot'] is not None and p['nomination'] is None, 'can_export_game': p['game_snapshot'] is not None, 'can_export_preparation': current_stage(p) == 'done', 'names': {x['id']: x['name'] for x in p['setting']['students'] if x['id'] in p['members']}, 'application': copy.deepcopy(p['game_snapshot']['player_visible']['application']) if p['game_snapshot'] else None}

    def dispatch(self, action, data, call):
        expected = {'create': ('setting', 'couple_id', 'mode', 'award_enabled'), 'load': ('project_id',), 'step': ('project_id',), 'pause': ('project_id',), 'stop': ('project_id',), 'resume': ('project_id',), 'nominate': ('project_id', 'event', 'event_date', 'confirmed'), 'export': ('project_id', 'kind'), 'import': ('project',), 'replan_disclosure': ('project_id', 'confirmed')}
        r.require(action in expected, '未知作者操作'); fields(data, expected[action])
        if action == 'create': p = self.create(**data)
        elif action == 'import': p = self.import_project(data['project'])
        elif action == 'export': return self.export(data['project_id'], data['kind'])
        elif action == 'nominate': p = self.nominate(data['project_id'], data['event'], data['event_date'], data['confirmed'])
        elif action == 'replan_disclosure': p = self.replan_disclosure(data['project_id'], data['confirmed'])
        elif action == 'step': p = self.step(data['project_id'], call)
        elif action == 'load':
            with self.lock: p = self.load(data['project_id'])
        else: p = self.control(data['project_id'], action)
        return self.view(p)


ENGINE = Engine()
