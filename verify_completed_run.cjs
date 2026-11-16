'use strict';
// 只做离线验收：不调用模型，不启动长期服务。用真实前端脚本导入已完成工程，
// 复核严格运行条件、运行设定导出、工程往返一致性和后端严格校验。
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const root = __dirname;
const projectPath = process.env.PROJECT || root + '/logs/2026-11-15T03-11-57-821Z_continued.project.json';
const settingPath = process.env.SETTING || root + '/logs/2026-11-15T03-11-57-821Z_continued.runtime.json';
const outBase = root + '/logs/2026-11-15_call23_resumed_complete';

const elements = new Map();
const el = id => {
  if (!elements.has(id)) elements.set(id, {
    value: '', checked: false, disabled: false, hidden: false, textContent: '', innerHTML: '',
    scrollTop: 0, scrollHeight: 1200, clientHeight: 400,
    classList: { toggle() {}, remove() {}, add() {} }, dataset: {},
    addEventListener() {}, getBoundingClientRect: () => ({ top: 0 }), focus() {}, click() {}
  });
  return elements.get(id);
};
['filter', 'stageFilter', 'kindFilter'].forEach(k => { el(k).value = k === 'filter' ? 'all' : 'all'; });

const context = vm.createContext({
  console, structuredClone, AbortController, TextEncoder, URL, Blob, crypto: crypto.webcrypto,
  document: {
    getElementById: el, querySelectorAll: () => [],
    createElement: () => ({ click() {}, style: {}, setAttribute() {}, appendChild() {} }),
    body: { appendChild() {}, removeChild() {} }, addEventListener() {}
  },
  window: { addEventListener() {} },
  confirm: () => false,
  setTimeout: (fn, ms) => setTimeout(fn, ms), clearTimeout,
  fetch: async () => { throw new Error('离线验收禁止任何网络请求'); },
  localStorage: { getItem: () => null, setItem() {}, removeItem() {} }
});
const run = code => vm.runInContext(code, context);
run(fs.readFileSync(root + '/student-foundry.html', 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1]);

// 该工程由被中断的续写进程写出：最后一次导出发生在运行设定生成之前，
// 因此缺少 state.runtimeSettingId。这里补回本次运行实际生成的 id（不新造值），
// 使存档与运行设定可一一对应；其余内容不改动。
const archive = JSON.parse(fs.readFileSync(projectPath, 'utf8'));
const savedSettingRaw = JSON.parse(fs.readFileSync(settingPath, 'utf8'));
let repaired = false;
if (!archive.state.runtimeSettingId) {
  assert.match(savedSettingRaw.setting_id, /^[0-9a-f]{32}$/, '运行设定ID格式异常');
  archive.state.runtimeSettingId = savedSettingRaw.setting_id;
  repaired = true;
}
const archiveText = JSON.stringify(archive);
const imported = run(`importProject(${JSON.stringify(archiveText)},false)`);
assert.equal(imported, true, '工程未能导入');

const state = JSON.parse(run('JSON.stringify({phase:state.phase,done:state.done,waiting:state.waiting,acceptance:state.personAcceptance,interventions:state.interventions,calls:state.calls,students:state.students.length,couples:state.couples.length,packages:state.takeover_packages.length,unresolved:state.unresolved})'));
assert.equal(state.phase, 'done', '工程未处于完成阶段');
assert.equal(state.done, true);
assert.equal(state.waiting, null, '存在待处理限额');
assert.equal(state.acceptance, 'review_approved', '人物不是审查通过而是人工接受');
assert.ok(!state.interventions.some(i => String(i.action).includes('人工接受')), '存在人工接受记录');
assert.equal(state.unresolved.length, 0, '存在未解决事项');
assert.equal(state.students, 4); assert.equal(state.couples, 1); assert.equal(state.packages, 4);

const ready = run('runtimeReady()');
assert.equal(ready, true, '未满足严格运行条件');

const reviews = JSON.parse(run(`JSON.stringify(state.reviews.map(r=>({agent:r.agent,approved:r.approved,issues:(r.issues||[]).length})))`));
const lastOf = agent => [...reviews].reverse().find(r => r.agent === agent);
for (const agent of ['CriticP', 'CriticC', 'CriticA', 'CriticM']) {
  const last = lastOf(agent);
  assert.ok(last, `缺少 ${agent} 审查`);
  assert.equal(last.approved, true, `${agent} 最终未通过`);
  assert.equal(last.issues, 0, `${agent} 最终仍有问题`);
}

const setting = run('runtimeSetting()');
assert.equal(setting.schema_version, 'model-couple-runtime-v1');
assert.equal(setting.date, '2025-04-23');
assert.equal(setting.students.length, 4);
assert.equal(setting.takeover_packages.length, 4);

const settingText = run('JSON.stringify(runtimeSetting())');
const savedSettingText = JSON.stringify(JSON.parse(fs.readFileSync(settingPath, 'utf8')));
assert.equal(settingText, savedSettingText, '与续写运行时保存的运行设定不一致');

// 工程往返：重新导出并再次导入，运行设定必须逐字一致
const reArchived = run('JSON.stringify(projectArchive())');
run(`importProject(${JSON.stringify(reArchived)},false)`);
assert.equal(run('runtimeReady()'), true, '往返导入后不可运行');
assert.equal(run('JSON.stringify(runtimeSetting())'), settingText, '往返导入后运行设定发生变化');

fs.writeFileSync(outBase + '.project.json', JSON.stringify(JSON.parse(reArchived), null, 2) + '\n');
fs.writeFileSync(outBase + '.setting.json', JSON.stringify(setting, null, 2) + '\n');

// 后端严格校验：在隔离进程内直接调用 simulation/runtime.py
const check = spawnSync('C:/Users/25367/AppData/Local/Programs/Python/Python314/python.exe', ['-c', `
import json,sys
sys.path.insert(0, ${JSON.stringify(root + '/../simulation')})
import runtime
setting = json.load(open(sys.argv[1], encoding='utf-8'))
result = runtime.validate_setting(setting)
print(json.dumps({'ok': True, 'setting_id': setting['setting_id'], 'students': len(setting['students'])}, ensure_ascii=False))
`, outBase + '.setting.json'], { encoding: 'utf8' });
if (check.status !== 0) {
  console.error(check.stderr || check.stdout);
  throw new Error('后端严格校验未通过');
}

console.log(JSON.stringify({
  done: true,
  requests_total_across_runs: 21,
  students: state.students,
  couples: state.couples,
  packages: state.packages,
  calls_in_project: state.calls,
  reviews: reviews.length,
  final_approved: { CriticP: lastOf('CriticP').approved, CriticC: lastOf('CriticC').approved, CriticA: lastOf('CriticA').approved, CriticM: lastOf('CriticM').approved },
  runtime_ready: ready,
  backend_validation: check.stdout.trim(),
  project: outBase + '.project.json',
  setting: outBase + '.setting.json'
}, null, 2));
