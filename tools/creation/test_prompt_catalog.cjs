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
 h.context.campusFile=fs.readFileSync(__dirname+'/../../documents/校园配置提示词_顶尖综合研究型大学.json','utf8');h.run('parseCampusPrompt(campusFile)');
 const campus={common:'共同校园哨兵 {{p1}} ${globalThis.pwned=true}',prometheus:'人物专属哨兵',cupid:'框架专属哨兵',aphrodite:'细节专属哨兵'};
 h.el('campusPrompt').value=JSON.stringify(campus);
 await h.el('start').onclick();
 assert.equal(JSON.stringify(h.state().config.campusPrompt),JSON.stringify(campus));
 h.el('campusPrompt').value='编辑不改变快照';
 assert.equal(JSON.stringify(h.state().config.campusPrompt),JSON.stringify(campus));
 for(const agent of ['Prometheus','C_Prometheus','Cupid','C_Cupid','Aphrodite','C_Aphrodite']){
   const t=['Cupid','Aphrodite'].includes(agent)?{agent,label:'框架',layer:'calendar'}:{agent,label:'测试'};
   const role=agent.replace(/^C_/,'').toLowerCase();
   for(let round=0;round<2;round++){
    const result=h.run(`prompt(${JSON.stringify(t)})`)[0].content;
    assert(result.includes(campus.common),agent);assert(result.includes(campus[role]),agent);
    for(const key of ['prometheus','cupid','aphrodite'].filter(k=>k!==role))assert(!result.includes(campus[key]),agent+' 不应收到 '+key);
   }
 }
 h.run("state.revisionQueue=[0];state.couples=demo({agent:'Cupid'}).couples");
 const revised=h.run("prompt({agent:'Cupid',label:'修订',revisionIndex:0})");assert(revised[0].content.includes(campus.cupid));assert(!revised[0].content.includes(campus.aphrodite));
 h.run('state.cupidWork={couples:structuredClone(state.couples)}');
 for(const layer of ['events','habits']){const text=h.run(`prompt({agent:'Aphrodite',layer:'${layer}',ci:0,si:0,schema:{}})`)[0].content;assert(text.includes(campus.common));assert(text.includes(campus.aphrodite));assert(!text.includes(campus.cupid));}
 for(const agent of ['Mnemosyne','C_Mnemosyne']){const text=h.run(`prompt({agent:'${agent}',label:'接管'})`)[0].content;for(const value of Object.values(campus))assert(!text.includes(value));}
 const detail=h.run("prompt({agent:'Aphrodite',label:'细节修订',detailRevisionIndex:0})");assert(detail[0].content.includes(campus.aphrodite));assert(!detail[0].content.includes(campus.cupid));
 h.run("state.config.campusPrompt={common:'',prometheus:'',cupid:'',aphrodite:'空common专属'}");assert(h.run("prompt({agent:'Aphrodite',label:'修订',detailRevisionIndex:0})")[0].content.includes('空common专属'));
 h.context.campus=campus;h.run('state.config.campusPrompt=structuredClone(campus)');
 assert.equal(h.run('globalThis.pwned'),undefined);
 h.run('delete state.cupidWork');
 const archive=h.run('projectArchive()');assert.equal(JSON.stringify(archive.state.config.campusPrompt),JSON.stringify(campus));
 const legacy=structuredClone(archive);delete legacy.state.config.campusPrompt;
 assert.equal(h.run(`validateProject(${JSON.stringify(legacy)}).config.campusPrompt.common`),'');
 legacy.state.config.campusPrompt='旧版纯文本';assert.equal(h.run(`validateProject(${JSON.stringify(legacy)}).config.campusPrompt.common`),'旧版纯文本');
 const bad=structuredClone(archive);bad.state.config.campusPrompt=42;
 assert.throws(()=>h.run(`validateProject(${JSON.stringify(bad)})`),/校园配置/);
 h.run(`importProject(${JSON.stringify(archive)},false)`);assert.deepEqual(JSON.parse(h.el('campusPrompt').value),campus);assert.equal(h.run('paused'),true);
 const fileHarness=setup({TextDecoder});const enc=new TextEncoder();
 const importText=async(name,bytes,size=bytes.byteLength)=>{const target={files:[{name,size,arrayBuffer:async()=>bytes.buffer}],value:'selected'};await fileHarness.el('campusPromptFile').onchange({target});assert.equal(target.value,'');};
 await importText('校园.json',enc.encode('\uFEFF'+JSON.stringify(campus)));assert.deepEqual(JSON.parse(fileHarness.el('campusPrompt').value),campus);
 for(const [name,bytes,size] of [['bad.md',enc.encode('bad'),3],['big.json',enc.encode('bad'),262145],['bad.json',new Uint8Array([255]),1],['bad.json',enc.encode('{'),1],['wrong.json',enc.encode('{"common":"缺字段"}'),20]]){await importText(name,bytes,size);assert.deepEqual(JSON.parse(fileHarness.el('campusPrompt').value),campus);assert(fileHarness.el('campusPromptStatus').textContent.includes('失败'));}
 await importText('empty.json',enc.encode(''));assert.equal(JSON.parse(fileHarness.el('campusPrompt').value).common,'');
 for(const invalid of [[],null,{common:1,prometheus:'',cupid:'',aphrodite:''},{...campus,extra:''}])assert.throws(()=>h.run(`validateCampusPrompt(${JSON.stringify(invalid)})`),/校园配置/);
 assert.throws(()=>h.run("validateCampusPrompt({common:'x'.repeat(60001),prometheus:'',cupid:'',aphrodite:''})"),/60000/);
 assert.throws(()=>h.run("validateCampusPrompt({common:'2026年入学',prometheus:'',cupid:'',aphrodite:''})"),/2025/);
 const before=h.state();h.el('campusPrompt').value='{';await h.el('start').onclick();assert.equal(h.state(),before);
 assert.equal(h.run('visibleMaterial(0).boundary.confirmation_status'),catalog.foundry.templates.takeover_boundary_confirmation);
 assert.equal(h.run('visibleMaterial(0).boundary.unknown'),catalog.foundry.templates.takeover_boundary_unknown);
 h.el('brief').value='用户编辑保留';h.run("state.config.brief='工程原有要求'");
 assert.equal(h.el('brief').value,'用户编辑保留');assert.equal(h.state().config.brief,'工程原有要求');
 h.run("state.config.campusPrompt=''");
 const phases=['students','person_review','person_revise'];
 for(const phase of phases){h.run(`state.phase=${JSON.stringify(phase)}`);const messages=h.run('prompt(task())');assert(!messages[0].content.includes('{{p'));assert(messages[0].content.includes('纯恋爱套件'));}
 h.run("state.config.awardEnabled=true;state.lastFailure={phase:state.phase,agent:task().agent,message:'错误哨兵'}");
 const messages=h.run('prompt(task())');assert(messages[0].content.includes('对接套件'));assert(messages.at(-1).content.includes('错误哨兵'));assert(messages.at(-1).content.startsWith(catalog.foundry.templates.prompt_2));
 console.log('提示词VM测试通过：缺目录/缺模板/缺参数明确失败、显式替换不求值、不递归替换、人物初稿/审查/修订、套件与纠错追加。');
})().catch(error=>{console.error(error);process.exitCode=1;});
