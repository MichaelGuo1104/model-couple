'use strict';
// 隔离DOM、网络及配置；只运行固定示例，不调用真实API。
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/student-foundry.html','utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
function setup(overrides={}){
 const elements=new Map(),events=[],timers=[];let serial=0,fail=false,confirmation=true,exportText='';
 const el=id=>{if(!elements.has(id))elements.set(id,{value:'',checked:false,disabled:false,hidden:false,textContent:'',innerHTML:'',scrollTop:0,scrollHeight:1200,clientHeight:400,listeners:{},classList:{toggle(){},remove(){}},addEventListener(type,fn){this.listeners[type]=fn;},getBoundingClientRect(){return {top:id.startsWith('trace-entry-')?300:0};},focus(options){this.focusOptions=options;},click(){}});return elements.get(id);};
 Object.entries({timeoutSeconds:'300',mode:'demo',count:'2',pairs:'1',brief:'当代大学成年人日常',filter:'all',key:'secret-test-key'}).forEach(([k,v])=>el(k).value=v);
 const ctx=vm.createContext({CREATION_PROMPTS:JSON.parse(fs.readFileSync(__dirname+'/prompts.json','utf8')),console,structuredClone,AbortController,TextEncoder,URL,crypto:require('node:crypto').webcrypto,Blob:class{constructor(parts){exportText=parts.join('');}},document:{getElementById:el,querySelectorAll:()=>[],createElement:()=>({click(){}})},window:{addEventListener(){}},confirm:()=>confirmation,setTimeout:(fn,ms)=>{if(ms===500){fn();return 1;}timers.push({fn,ms});return timers.length;},clearTimeout(){},fetch:async(path,opts)=>{const data=JSON.parse(opts.body);if(path.includes('/config/'))throw Error('隔离配置');if(fail)throw Error('模拟日志不可写');if(path.endsWith('/start'))return{ok:true,json:async()=>({run_id:'run'+(++serial),path:'tools/logs/test'+serial+'.log'})};events.push(data);return{ok:true,json:async()=>({written:true})};}});
 Object.assign(ctx,overrides);vm.runInContext(script,ctx);vm.runInContext('URL.createObjectURL=()=>"blob:test";URL.revokeObjectURL=()=>{};',ctx);
 return{el,events,timers,run:s=>vm.runInContext(s,ctx),state:()=>vm.runInContext('state',ctx),flush:()=>vm.runInContext('journal.queue',ctx),fail:v=>fail=v,confirm:v=>confirmation=v,export:()=>exportText};
}
async function drain(h){for(let i=0;i<250;i++){const index=h.timers.findIndex(t=>t.ms===200);if(index<0)return;const [timer]=h.timers.splice(index,1);await timer.fn();}throw Error('自动执行未停止');}
async function next(h){await h.el('next').onclick();}
async function main(){
 // UI 的 DOM 事件与离线渲染验证，不请求浏览器或真实服务。
 const ui=setup();await ui.el('start').onclick();ui.el('follow').checked=true;
 for(const id of ['filter','stageFilter','kindFilter'])ui.el(id).value='all';
 ui.run(`state.logs=[{agent:'Prometheus',label:'人物初稿',summary:'人物正文',time:'10:00'}, {agent:'Cupid',label:'关系框架',summary:'框架正文'}, {agent:'Aphrodite',label:'细节',summary:'细节正文'}, {agent:'Mnemosyne',label:'接管',summary:'记忆正文'}, {agent:'System',label:'旧记录',summary:'未归类'}, {agent:'System',label:'步骤失败',summary:'错误哨兵',metadata:{stage:'detail',kind:'error',round:2,call:8}}];state.phase='takeover';renderLog();`);
 for(const stage of ['person','framework','detail','memory','system'])assert(ui.el('log').innerHTML.includes('group-'+stage));
 assert.equal(ui.run("traceStage(state.logs[0])"),'person');assert.equal(ui.run("traceStage(state.logs[4])"),'system');assert.equal(ui.run("traceStage(state.logs[5])"),'detail');
 assert(!ui.el('log').innerHTML.includes('data-trace-key="entry-0" open'));assert(ui.el('logCount').textContent.includes('6 / 6'));
 ui.el('stageFilter').value='framework';ui.el('log').scrollTop=73;ui.el('stageFilter').onchange();assert.equal(ui.el('log').scrollTop,73);assert.equal(ui.run('traceFiltered().length'),1);assert(ui.el('log').innerHTML.includes('框架正文'));assert(!ui.el('log').innerHTML.includes('人物正文'));
 ui.el('stageFilter').value='all';ui.el('filter').value='Prometheus';ui.el('filter').onchange();assert.equal(ui.run('traceFiltered().length'),1);ui.el('filter').value='all';ui.el('kindFilter').value='error';ui.el('kindFilter').onchange();assert.equal(ui.run('traceFiltered().length'),1);ui.el('kindFilter').value='all';ui.el('logSearch').value='错误哨兵';ui.el('logSearch').oninput();assert.equal(ui.run('traceFiltered().length'),1);ui.el('logSearch').value='';
 ui.run(`log('Prometheus','人物测试','<img src=x onerror=alert(1)> '+ '长正文'.repeat(300),{raw:'</pre><script>alert(1)</script>',secret:'secret-test-key'})`);
 assert.equal(ui.el('log').scrollTop,1200);assert(!ui.el('log').innerHTML.includes('<img'));assert(!ui.el('log').innerHTML.includes('<script>'));assert(ui.el('log').innerHTML.includes('&lt;img'));assert(!ui.el('log').innerHTML.includes('secret-test-key'));assert(ui.el('log').innerHTML.includes('[已过滤密钥]'));assert(ui.state().logs.at(-1).summary.length>800);assert.equal(ui.state().logs.at(-1).metadata.stage,'person');
 ui.el('log').scrollTop=120;ui.el('log').listeners.toggle({target:{dataset:{traceKey:'entry-6'},open:true}});assert.equal(ui.el('log').scrollTop,120);ui.run("log('System','测试','展开时不跟随')");assert.equal(ui.el('log').scrollTop,120);assert(ui.el('log').innerHTML.includes('data-trace-key="entry-6" open'));
 ui.el('kindFilter').value='review';ui.el('kindFilter').onchange();assert(ui.el('log').innerHTML.includes('没有匹配'));ui.run("log('C_Prometheus','审查','筛选中不跟随')");assert.equal(ui.el('log').scrollTop,120);
 ui.el('locateError').onclick();assert.equal(ui.el('kindFilter').value,'all');assert.equal(ui.el('follow').checked,false);assert.equal(ui.el('trace-entry-5').focusOptions.preventScroll,true);assert(ui.el('log').innerHTML.includes('data-trace-key="entry-5" open'));
 ui.el('follow').checked=true;ui.el('log').scrollTop=0;ui.el('log').listeners.scroll();assert.equal(ui.el('follow').checked,false);ui.run('renderLog()');assert.equal(ui.el('log').scrollTop,0);
 ui.run('traceOpen.clear()');ui.el('follow').checked=true;ui.el('log').scrollTop=55;ui.el('log').listeners.toggle({target:{dataset:{traceKey:'group-person'},open:false}});ui.run("log('Prometheus','人物新增','分组折叠时不跟随')");assert.equal(ui.el('log').scrollTop,55);assert(!ui.el('log').innerHTML.includes('data-trace-key="group-person" open'));ui.el('follow').checked=false;ui.run('traceOpen.clear()');ui.run("log('Prometheus','人物新增','关闭跟随时不跳')");assert.equal(ui.el('log').scrollTop,55);ui.el('follow').checked=true;ui.el('follow').onchange();assert.equal(ui.el('log').scrollTop,55);
 await ui.flush();console.log('UI模拟DOM通过：四阶段/旧记录归类/默认折叠/完整正文及JSON/筛选计数/XSS脱敏/跟随不跳/错误定位。');
 const calendar=setup();calendar.el('brief').value='2026年校园';await calendar.el('start').onclick();assert.equal(calendar.state(),null);assert.throws(()=>calendar.run("assertNatural('二零二六年经历')"),/晚于2025年/);
 const h=setup();await h.el('start').onclick();assert.equal(h.state().phase,'person_review');assert.equal(h.state().calls,1);assert.equal(h.run('paused'),true);for(const key of ['personRounds','rounds','detailRounds','takeoverRounds'])assert.equal(h.state().config[key],null);
 await h.el('stage').onclick();await drain(h);assert.equal(h.state().phase,'draft');assert.equal(h.state().calls,4);assert.equal(h.run('paused'),true);assert.equal(h.state().couples.length,0);
 await h.el('stage').onclick();await drain(h);assert.equal(h.state().phase,'details');assert.equal(h.state().couples[0].story.events.length,0);assert.equal(h.run('task().agent'),'Aphrodite');assert.equal(h.state().reviews.at(-1).agent,'C_Cupid');
 const locked=JSON.stringify(h.state().couples.map(c=>({...c,story:{...c.story,events:[],habits:[]}})));
 const calls=h.state().calls;await next(h);assert.equal(h.state().calls,calls+1);assert.equal(h.state().cupidWork.layer,'habits');assert.equal(h.run('paused'),true);
 assert.throws(()=>h.run("{const d=demo(task());d.framework_revision_requests=[];validate(task(),d)}"),/框架/);
 await h.el('stage').onclick();await drain(h);assert.equal(h.state().phase,'takeover');assert.equal(h.state().takeover_packages.length,0);assert.equal(h.state().detailRevisions,1);assert.equal(h.run('paused'),true);
 assert.equal(JSON.stringify(h.state().couples.map(c=>({...c,story:{...c.story,events:[],habits:[]}}))),locked);
 h.run("state.phase='detail_revise'");for(const mutation of ["d.couples[0].title='越权'","d.couples[0].story.events[0].id='换ID'","d.couples[0].story.events[0].stage_id='p2'"])assert.throws(()=>h.run(`{const d=demo(task());${mutation};validate(task(),d)}`),/框架|IDs|stage_id/);h.run("state.phase='takeover'");
 await next(h);assert.equal(h.state().takeoverIndex,0);assert.equal(h.state().phase,'takeover_review');
 await h.el('stage').onclick();await drain(h);assert.equal(h.state().done,true);assert.equal(h.state().takeover_packages.length,2);assert.equal(h.state().takeoverRevisions,0);assert(h.run('runtimeReady()'));
 for(const entry of h.state().logs){assert(entry.metadata);if(entry.agent!=='System')assert.equal(entry.metadata.stage,h.run(`agentStage[${JSON.stringify(entry.agent)}]`));}assert(h.state().logs.some(x=>x.label==='调用开始'&&x.metadata.taskAgent==='Aphrodite'&&x.metadata.stage==='detail'));
 assert(h.state().versions.some(v=>v.stage==='人物'));assert(h.state().versions.some(v=>v.stage==='框架'));assert(h.state().versions.some(v=>v.stage==='细节'));assert(h.state().versions.some(v=>v.stage==='记忆'));
 const runtime=h.run('JSON.stringify(runtimeSetting())');const setting=JSON.parse(runtime);assert.equal(setting.review_status.detail.agent,'C_Aphrodite');assert.equal(setting.review_status.takeover.s1.review.agent,'C_Mnemosyne');
 await h.flush();for(const role of ['Prometheus','Cupid','Aphrodite','Mnemosyne','C_Prometheus','C_Cupid','C_Aphrodite','C_Mnemosyne'])assert(h.events.some(x=>x.entry.role===role&&x.entry.event==='task'),role);assert(!JSON.stringify(h.events).includes('secret-test-key'));
 const auto=setup();auto.el('count').value='6';auto.el('pairs').value='2';await auto.el('start').onclick();await auto.el('auto').onclick();await drain(auto);assert.equal(auto.state().done,true);assert.equal(auto.state().takeover_packages.length,6);assert(auto.run('runtimeReady()'));
 // 默认无限：超过原先1至2轮限制依然审核到通过，结果不被程序擅改。
 const unlimited=setup();await unlimited.el('start').onclick();unlimited.run("globalThis.originalDemo=demo;demo=t=>{const d=originalDemo(t);if(t.agent==='C_Prometheus'){d.approved=state.personRevisions>=4;d.issues=d.approved?[]:[{target:'s1',severity:'一般',problem:'持续复核',suggestion:'补充'}];}return d;}");await unlimited.el('stage').onclick();await drain(unlimited);assert.equal(unlimited.state().personRevisions,4);assert.equal(unlimited.state().phase,'draft');assert.equal(unlimited.state().waiting,null);
 // 四个阶段均可超出旧限额；各阶段修订计数独立。
 const allUnlimited=setup();await allUnlimited.el('start').onclick();allUnlimited.run("globalThis.originalDemo=demo;demo=t=>{const d=originalDemo(t);const rounds={C_Prometheus:state.personRevisions,C_Cupid:state.coupleRevisions,C_Aphrodite:state.detailRevisions,C_Mnemosyne:state.takeoverRevisions};if(Object.hasOwn(rounds,t.agent)){d.approved=rounds[t.agent]>=3;d.issues=d.approved?[]:[{target:t.agent==='C_Prometheus'?'s1':t.agent==='C_Mnemosyne'?state.students[state.takeoverIndex].id:'c1',severity:'一般',problem:'持续复核',suggestion:'补充'}];}return d;}");await allUnlimited.el('auto').onclick();await drain(allUnlimited);assert.equal(allUnlimited.state().done,true);for(const field of ['personRevisions','coupleRevisions','detailRevisions'])assert.equal(allUnlimited.state()[field],3);assert.equal(allUnlimited.state().metadata.takeover.s2.revisions,3);
 // 有限限额保留追加与人工接受安全边界。
 const finite=setup();finite.el('personRounds').value='0';await finite.el('start').onclick();await finite.el('stage').onclick();await drain(finite);assert.equal(finite.state().waiting,'person');finite.el('extend').onclick();assert.equal(finite.state().config.personRounds,1);await next(finite);await next(finite);assert.equal(finite.state().phase,'draft');
 const manual=setup();manual.el('personRounds').value='0';await manual.el('start').onclick();await next(manual);manual.el('acceptPerson').onclick();assert.equal(manual.state().personAcceptance,'manual');await manual.el('auto').onclick();await drain(manual);assert.equal(manual.state().done,true);assert(!manual.run('runtimeReady()'));assert.throws(()=>manual.run('runtimeSetting()'),/全部审查通过/);
 // 失败必须暂停原步骤且不安排重试。
 const bad=setup();await bad.el('start').onclick();bad.run("demo=()=>({approved:false,summary:'坏结构',issues:[],preserve:[]})");await bad.el('auto').onclick();await drain(bad);assert.equal(bad.run('paused'),true);assert.equal(bad.state().phase,'person_review');assert.equal(bad.state().calls,2);
 // 结构归一化、关键身份和锁定人物仍有严格校验。
 const schema=setup();await schema.el('start').onclick();schema.run("state.phase='students';const d=demo(task());d.creator_notes='安全扩展';validate(task(),d);if('creator_notes' in d)throw Error('未归一化')");for(const mutation of ["delete d.summary","d.students[0].age=17","d.students[0].cognition.Se.score=101"])assert.throws(()=>schema.run(`{const d=demo(task());${mutation};validate(task(),d)}`));schema.run("state.phase='person_revise'");assert.throws(()=>schema.run("{const d=demo(task());d.students[0].name='换名';validate(task(),d)}"),/基本身份/);
 // 日志写入失败不丢弃已提交的角色输出。
 const journalFailure=setup();journalFailure.fail(true);await journalFailure.el('start').onclick();await journalFailure.flush();assert.equal(journalFailure.state().phase,'person_review');assert(journalFailure.el('logStatus').textContent.includes('失败'));
 // 请求进行中暂停：提交当前请求后停；停止：丢弃返回结果。
 const pause=setup();await pause.el('start').onclick();pause.run("globalThis.originalDemo=demo;globalThis.release=null;demo=t=>new Promise(resolve=>{release=()=>resolve(originalDemo(t))})");const pending=pause.el('auto').onclick();pause.el('pause').onclick();pause.run('release()');await pending;await drain(pause);assert.equal(pause.state().phase,'person_revise');assert.equal(pause.run('paused'),true);
 const stop=setup();await stop.el('start').onclick();stop.run("globalThis.originalDemo=demo;globalThis.release=null;demo=t=>new Promise(resolve=>{release=()=>resolve(originalDemo(t))})");const stopping=stop.el('auto').onclick();stop.el('stop').onclick();stop.run('release()');await stopping;await drain(stop);assert.equal(stop.state().phase,'person_review');assert.equal(stop.state().reviews.length,0);
 // 已排队自动任务在暂停后不得误执行。
 const queued=setup();await queued.el('start').onclick();await queued.el('auto').onclick();const queuedCalls=queued.state().calls;queued.el('pause').onclick();await drain(queued);assert.equal(queued.state().calls,queuedCalls);
 // 框架、细节、逐人记忆的自定义限额可追加，审查历史不丢失。
 for(const [field,waiting] of [['rounds','couple'],['detailRounds','detail'],['takeoverRounds','takeover']]){const limited=setup();limited.el(field).value='0';await limited.el('start').onclick();await limited.el('auto').onclick();await drain(limited);assert.equal(limited.state().waiting,waiting);const reviewCount=limited.state().reviews.length;limited.el('extend').onclick();await new Promise(resolve=>setImmediate(resolve));await drain(limited);assert(limited.state().reviews.length>reviewCount);if(waiting==='takeover'){assert.equal(limited.state().metadata.takeover.s1.status,'review_approved');assert.equal(limited.state().waiting,'takeover');assert.equal(limited.state().takeoverIndex,1);}else assert.equal(limited.state().done,true);}
 // 单人隔离和来源白名单。
 h.run("state.done=false;state.takeoverIndex=0;state.phase='takeover';state.students[1].background='他人档案哨兵';state.couples[0].perspectives[1].hidden='他人秘密哨兵';state.notes=['创作意见哨兵']");const input=h.run('JSON.stringify(prompt(task()))');for(const secret of ['他人档案哨兵','他人秘密哨兵','创作意见哨兵'])assert(!input.includes(secret));for(const ref of ['$.students[1].background','$.couples[0].story.events[0].observations[1].observation','$.couples[0].facts[0]','$.students[0]'])assert.throws(()=>h.run(`{const d=demo(task());d.initial_memories[0].source_refs=[${JSON.stringify(ref)}];validate(task(),d)}`),/白名单/);
 // strict新审核metadata、旧完成导入、人工接受/缺审拒绝。
 const {spawnSync}=require('node:child_process');const py=spawnSync('python',['-c',`import sys,json,copy
sys.path.insert(0,'tools/creation')
import runtime
s=json.load(sys.stdin)
runtime.validate_setting(s)
for mutate in ('detail','manual','role'):
 t=copy.deepcopy(s)
 if mutate=='detail': t['review_status']['detail']['approved']=False
 if mutate=='manual': t['review_status']['manual_acceptance']=True
 if mutate=='role': t['review_status']['takeover']['s1']['review']['agent']='Critic_I'
 try: runtime.validate_setting(t)
 except ValueError: pass
 else: raise AssertionError(mutate)
t=copy.deepcopy(s)
t['review_status'].pop('detail');t['review_status'].pop('pipeline')
t['review_status']['person']['agent']='Critic_P';t['review_status']['couple']['agent']='Critic_C'
for v in t['review_status']['takeover'].values(): v['review']['agent']='Critic_I'
runtime.validate_setting(t)
print('Python strict新流程、旧标识兼容与拒绝用例通过')`],{input:runtime,encoding:'utf8',cwd:__dirname+'/../..'});assert.equal(py.status,0,py.stderr);console.log(py.stdout.trim());
 console.log('Node回归通过：一步/四阶段边界/全自动/无限超旧限额/失败暂停/请求暂停及停止/越权/严格导出/命名/单人隔离。');
}
module.exports={setup};
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
