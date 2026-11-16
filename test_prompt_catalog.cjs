'use strict';
// 直接注入JSON，全部使用离线VM；验证替换不求值以及目录必需性。
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {setup}=require('./test_student_foundry.cjs');
const catalog=JSON.parse(fs.readFileSync(__dirname+'/prompts.json','utf8'));
assert.throws(()=>setup({CREATION_PROMPTS:undefined}),/prompts.json 未加载/);
const source=fs.readFileSync(__dirname+'/student-foundry.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
assert(source.trimStart().startsWith("'use strict';"));
const brokenElements=new Map();
const brokenElement=id=>{if(!brokenElements.has(id))brokenElements.set(id,{});return brokenElements.get(id);};
assert.throws(()=>setup({CREATION_PROMPTS:undefined,CREATION_PROMPTS_ERROR:'prompts.json 加载失败：坏JSON',document:{getElementById:brokenElement}}),/坏JSON/);
assert(brokenElement('status').textContent.includes('修复 prompts.json 后刷新'));
assert.equal(brokenElement('status').className,'status error');
for(const id of ['start','next','stage','auto','pause','stop','extend','acceptPerson','acceptTakeover'])assert.equal(brokenElement(id).disabled,true);
const briefElement={value:'',addEventListener(){}};setup({document:{getElementById:()=>briefElement,querySelectorAll:()=>[],createElement:()=>({click(){}})}});
assert.equal(briefElement.value,catalog.foundry.templates.default_brief);
const h=setup();
assert.equal(h.el('brief').value,'当代大学成年人日常');
assert.equal(h.run("renderPrompt('calendar')"),catalog.foundry.templates.calendar);
assert.throws(()=>h.run("renderPrompt('missing')"),/缺少模板/);
assert.throws(()=>h.run("renderPrompt('cupidPrompt_0')"),/占位符缺少参数/);
assert.equal(h.run("renderPrompt('cupidPrompt_0',{p0:'${globalThis.pwned=true} {{p1}}'})"),catalog.foundry.templates.cupidPrompt_0.replace('{{p0}}','${globalThis.pwned=true} {{p1}}'));
assert.equal(h.run('globalThis.pwned'),undefined);
(async()=>{
 await h.el('start').onclick();
 assert.equal(h.run('visibleMaterial(0).boundary.confirmation_status'),catalog.foundry.templates.takeover_boundary_confirmation);
 assert.equal(h.run('visibleMaterial(0).boundary.unknown'),catalog.foundry.templates.takeover_boundary_unknown);
 h.el('brief').value='用户编辑保留';h.run("state.config.brief='工程原有要求'");
 assert.equal(h.el('brief').value,'用户编辑保留');assert.equal(h.state().config.brief,'工程原有要求');
 const phases=['students','person_review','person_revise'];
 for(const phase of phases){h.run(`state.phase=${JSON.stringify(phase)}`);const messages=h.run('prompt(task())');assert(!messages[0].content.includes('{{p'));assert(messages[0].content.includes('纯恋爱套件'));}
 h.run("state.config.awardEnabled=true;state.lastFailure={phase:state.phase,agent:task().agent,message:'错误哨兵'}");
 const messages=h.run('prompt(task())');assert(messages[0].content.includes('对接套件'));assert(messages.at(-1).content.includes('错误哨兵'));assert(messages.at(-1).content.startsWith(catalog.foundry.templates.prompt_2));
 console.log('提示词VM测试通过：缺目录/缺模板/缺参数明确失败、显式替换不求值、不递归替换、人物初稿/审查/修订、套件与纠错追加。');
})().catch(error=>{console.error(error);process.exitCode=1;});
