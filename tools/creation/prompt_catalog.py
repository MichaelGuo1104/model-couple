"""主线提示词目录：每次读取、严格校验，不求值、不回退。"""
import json
import re
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name('prompts.json')
CONTRACT = {'foundry': {'templates': {'calendar': [], 'cupidTask_0': [], 'cupidTask_1': ['p0', 'p1', 'p2'], 'cupidTask_2': [], 'cupidTask_3': [], 'cupidPrompt_0': ['p0'], 'cupidPrompt_1': ['p0', 'p1', 'p2', 'p3', 'p4', 'p5'], 'cupidPrompt_2': ['p0'], 'cupidPrompt_3': ['p0'], 'cupidPrompt_4': ['p0', 'p1', 'p2', 'p3', 'p4', 'p5'], 'cupidPrompt_5': [], 'takeoverPrompt_0': ['p0', 'p1', 'p2', 'p3', 'p4'], 'takeoverPrompt_1': [], 'takeoverPrompt_2': [], 'takeoverPrompt_3': [], 'takeoverPrompt_4': [], 'takeoverPrompt_5': [], 'takeoverPrompt_6': [], 'takeoverPrompt_7': [], 'takeoverPrompt_8': [], 'prompt_0': [], 'prompt_1': [], 'prompt_2': [], 'buildPrompt_0': ['p0', 'p1'], 'buildPrompt_1': ['p0', 'p1'], 'buildPrompt_2': ['p0', 'p1'], 'buildPrompt_3': [], 'buildPrompt_4': ['p0', 'p1', 'p2', 'p3'], 'buildPrompt_5': ['p0'], 'buildPrompt_6': ['p0'], 'buildPrompt_7': [], 'buildPrompt_8': [], 'buildPrompt_9': [], 'buildPrompt_10': [], 'buildPrompt_11': [], 'buildPrompt_12': [], 'buildPrompt_13': [], 'buildPrompt_14': [], 'buildPrompt_15': []}, 'schemas': {'cognitionSchema': {'Se': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}, 'Si': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}, 'Ne': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}, 'Ni': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}, 'Te': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}, 'Ti': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}, 'Fe': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}, 'Fi': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}}, 'studentSchema': {'summary': 'string', 'response': 'string', 'students': [{'id': 'string', 'name': 'string', 'gender': 'string', 'age': 'number', 'major': 'string', 'year': 'string', 'grades': 'string', 'personality': 'string', 'background': 'string', 'desire': 'string', 'fear': 'string', 'contradiction': 'string', 'independent_life': 'string', 'voice': 'string', 'current_intentions': 'string', 'daily_details': ['string'], 'cognition': {'Se': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}, 'Si': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}, 'Ne': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}, 'Ni': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}, 'Te': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}, 'Ti': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}, 'Fe': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}, 'Fi': {'score': 'number', 'evidence': 'string', 'attention': 'string', 'interpretation': 'string', 'decision': 'string', 'stress': 'string'}}}]}, 'coupleSchema': {'summary': 'string', 'response': 'string', 'couples': [{'id': 'string', 'title': 'string', 'members': ['string'], 'stage': 'string', 'attraction': 'string', 'dynamic': 'string', 'tension': 'string', 'timeline': [{'time': 'string', 'event': 'string'}], 'facts': ['string'], 'perspectives': [{'student_id': 'string', 'interpretation': 'string', 'hidden': 'string', 'unknown': 'string'}], 'daily_details': ['string'], 'current_intentions': 'string'}]}, 'observationSchema': {'student_id': 'string', 'observation': 'string', 'interpretation': 'string'}, 'eventSchema': {'id': 'string', 'stage_id': 'string', 'date': 'string', 'location': 'string', 'participants': ['string'], 'action': 'string', 'result': 'string', 'observations': [{'student_id': 'string', 'observation': 'string', 'interpretation': 'string'}]}, 'habitSchema': {'id': 'string', 'stage_id': 'string', 'participants': ['string'], 'frequency': 'string', 'duration': 'string', 'typical_details': 'string', 'exceptions': 'string', 'evolution': 'string', 'observations': [{'student_id': 'string', 'observation': 'string', 'interpretation': 'string'}]}, 'storySchema': {'met_on': 'string', 'dating_on': 'string', 'known_duration': 'string', 'dating_duration': 'string', 'stages': [{'id': 'string', 'start': 'string', 'end': 'string', 'label': 'string', 'summary': 'string'}], 'events': [{'id': 'string', 'stage_id': 'string', 'date': 'string', 'location': 'string', 'participants': ['string'], 'action': 'string', 'result': 'string', 'observations': [{'student_id': 'string', 'observation': 'string', 'interpretation': 'string'}]}], 'habits': [{'id': 'string', 'stage_id': 'string', 'participants': ['string'], 'frequency': 'string', 'duration': 'string', 'typical_details': 'string', 'exceptions': 'string', 'evolution': 'string', 'observations': [{'student_id': 'string', 'observation': 'string', 'interpretation': 'string'}]}]}, 'reviewSchema': {'approved': 'bool', 'summary': 'string', 'issues': [{'target': 'string', 'severity': 'string', 'problem': 'string', 'suggestion': 'string'}], 'preserve': ['string']}, 'personReviewSchema': {'approved': 'bool', 'summary': 'string', 'issues': [{'target': 'string', 'severity': 'string', 'problem': 'string', 'suggestion': 'string'}], 'preserve': ['string']}, 'coupleReviewSchema': {'approved': 'bool', 'summary': 'string', 'issues': [{'target': 'string', 'severity': 'string', 'problem': 'string', 'suggestion': 'string'}], 'preserve': ['string'], 'person_revision_requests': [{'student_id': 'string', 'reason': 'string'}]}, 'takeoverSchema': {'student_id': 'string', 'role_instructions': 'string', 'initial_memories': [{'text': 'string', 'source_refs': ['string']}], 'private_information': [{'text': 'string', 'source_refs': ['string']}], 'disclosure_policy': 'string', 'cognition_guidance': 'string', 'uncertainties': ['string']}}}, 'author': {'templates': {'rule_0': [], 'rule_1': [], 'rule_2': [], 'rule_3': [], 'rule_4': [], 'rule_5': [], 'rule_6': [], 'rule_7': []}, 'schemas': {'REVIEW_SCHEMA': {'approved': 'bool', 'summary': 'string', 'issues': ['string']}, 'CHRONOS_SCHEMA': {'summary': 'string', 'people': {'学生ID': {'experiences': [{'date': 'string', 'text': 'string'}], 'attitude': 'string', 'consent': 'bool', 'form': {'status': 'string', 'filled': 'bool', 'started_on': 'null', 'completed_on': 'null', 'text': 'string'}}}, 'registration': {'status': 'string', 'submitted_on': 'null', 'withdrawn_on': 'null'}}, 'DISCLOSURE_SCHEMA': {'student_id': 'string', 'items': [{'id': 'string', 'text': 'string', 'source_refs': ['string']}], 'stance': 'string'}, 'SCRIPT_SCHEMA': {'title': 'string', 'characters': ['string'], 'scenes': [{'id': 'string', 'title': 'string', 'beats': [{'id': 'string', 'performers': ['string'], 'kind': 'string', 'text': 'string', 'action': 'string', 'emotion': 'string', 'duration_seconds': 'number', 'source_refs': ['string'], 'framing': 'string'}]}], 'backstage': ['string']}, 'ATTITUDE_SCHEMA': {'student_id': 'string', 'reactions': [{'beat_id': 'string', 'feeling': 'string', 'reason': 'string', 'readiness': 'string'}], 'cooperation': 'string', 'memory': 'string'}}}}

CONTRACT['foundry']['templates'].update({
    'campus_context': ['p0'],
    'default_brief': [],
    'takeover_boundary_confirmation': [],
    'takeover_boundary_unknown': [],
})


CONTRACT['author']['templates'].update({'application_writer': [], 'application_critic': []})
CONTRACT['author']['schemas']['CHRONOS_SCHEMA']['people']['学生ID'].pop('form')
CONTRACT['author']['schemas']['CHRONOS_SCHEMA']['registration'] = {'status': 'string', 'submitted_on': 'string'}
CONTRACT['author']['schemas']['APPLICATION_SCHEMA'] = {'statements': {'学生ID': 'string'}, 'metadata': {'both_authorized': 'bool', 'privacy': 'string', 'submitted_on': 'string'}}


def _check_shape(value, expected, path):
    if isinstance(expected, dict):
        if not isinstance(value, dict) or set(value) != set(expected):
            raise ValueError(path + ' 字段缺失或包含未知字段')
        for key, item in expected.items():
            _check_shape(value[key], item, path + '.' + key)
    elif isinstance(expected, list):
        if not isinstance(value, list) or bool(value) != bool(expected):
            raise ValueError(path + ' 列表结构无效')
        for i, item in enumerate(value):
            _check_shape(item, expected[0], path + '[' + str(i) + ']')
    else:
        valid = {'string': isinstance(value, str), 'number': type(value) in (int, float), 'bool': type(value) is bool, 'null': value is None}
        if not valid[expected]:
            raise ValueError(path + ' 类型或内容无效：' + expected)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('重复键：' + key)
        if key in ('__proto__', 'prototype', 'constructor'):
            raise ValueError('不允许的键：' + key)
        result[key] = value
    return result


def load_catalog(path=None):
    path = Path(path) if path is not None else CATALOG_PATH
    try:
        if path.is_symlink():
            raise ValueError('不允许符号链接')
        raw = path.read_bytes()
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError('超过2 MiB')
        catalog = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('不允许非有限数字')))
        if not isinstance(catalog, dict) or set(catalog) != set(CONTRACT):
            raise ValueError('必须包含 foundry 和 author')
        for section, contract in CONTRACT.items():
            data = catalog[section]
            if not isinstance(data, dict) or set(data) != {'templates', 'schemas'}:
                raise ValueError(section + ' 必须包含 templates 和 schemas')
            templates = data['templates']
            if not isinstance(templates, dict) or set(templates) != set(contract['templates']):
                raise ValueError(section + '.templates 模板键缺失或包含未知键')
            for key, params in contract['templates'].items():
                text = templates[key]
                if not isinstance(text, str) or not text.strip():
                    raise ValueError(section + '.templates.' + key + ' 必须为非空文本')
                actual = sorted(set(re.findall(r'\{\{([A-Za-z][A-Za-z0-9_]*)\}\}', text)))
                remainder = re.sub(r'\{\{([A-Za-z][A-Za-z0-9_]*)\}\}', '', text)
                if actual != params or '{{' in remainder or '}}' in remainder:
                    raise ValueError(section + '.templates.' + key + ' 占位符与代码契约不一致')
            _check_shape(data['schemas'], contract['schemas'], section + '.schemas')
        return catalog
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        raise ValueError('prompts.json 加载失败：' + str(error)) from error


def javascript_bootstrap():
    data = json.dumps(load_catalog(), ensure_ascii=True, allow_nan=False)
    return ('globalThis.CREATION_PROMPTS=' + data.replace('<', r'\u003c').replace('>', r'\u003e').replace('&', r'\u0026') + ';\n').encode('utf-8')
