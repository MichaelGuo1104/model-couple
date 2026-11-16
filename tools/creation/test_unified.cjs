'use strict';
// 离线执行真实装配器；模型与DOM由可观察替身提供，不启动服务或读取配置。
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/unified.js','utf8');
async function setup(real=null){
 const nodes=new Map(),calls=[],downloads=[];let context;
 class Node{
  constructor(tag='div'){this.tag=tag;this.children=[];this.style={};this.dataset={};this.value='';this.textContent='';this.hidden=false;this.disabled=false;this.files=[];const classes=new Set();this.classList={toggle(name,enabled){if(enabled)classes.add(name);else classes.delete(name);},contains:name=>classes.has(name)};}
  set id(v){this._id=v;nodes.set(v,this);}get id(){return this._id;}
  append(...children){for(const node of children){if(node.parent)node.parent.children=node.parent.children.filter(x=>x!==node);node.parent=this;this.children.push(node);if(node.tag==='option'&&!this.value)this.value=node.value;}if(this===body&&children[0]?.tag==='script')queueMicrotask(()=>children[0].onload());}
  replaceChildren(...children){this.children=[];this.value='';this.append(...children);}
  querySelectorAll(query){const all=this.children.flatMap(x=>[x,...x.querySelectorAll('*')]);if(query==='*')return all;if(query==='[id]')return all.filter(x=>x.id);if(query==='[for]')return [];if(query==='button')return all.filter(x=>x.tag==='button');if(query==='[data-tab]')return all.filter(x=>x.dataset.tab);if(query==='[data-step]')return all.filter(x=>x.dataset.step);if(query==='[data-author-stage]')return all.filter(x=>x.dataset.authorStage);return [];}
  closest(){return this.parent;}remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this);}setAttribute(){}click(){return this.onclick?.();}
 }
 const el=id=>{if(!nodes.has(id)){const n=real?real.el(id):new Node();if(real){const previous={...n};Object.setPrototypeOf(n,Node.prototype);Object.assign(n,new Node(),previous);n.style={};n.dataset={};n.children=[];}n.id=id;}return nodes.get(id);};
 const body=new Node('body'),main=new Node('main'),panel=new Node(),pipeline=new Node();
 for(let i=0;i<3;i++){const col=new Node();col.append(new Node());main.append(col);}main.children[0].append(panel);
 for(const key of ['person','framework','detail','memory']){const node=new Node();node.dataset.step=key;pipeline.append(node);}
 const fragmentMain=new Node('main');for(let i=0;i<3;i++)fragmentMain.append(new Node());
 for(const id of ['step','stage','auto','pause','stop','resume','create','restore','nominate','replanDisclosure','file','couple','filter','status','projectId','stages']){const n=new Node(id==='file'?'input':'button');n.id=id;if(id==='replanDisclosure'){const section=new Node('section');section.append(n);fragmentMain.children[0].append(section);}else fragmentMain.children[0].append(n);}
 const doc={body,querySelectorAll:()=>[],createElement:tag=>new Node(tag),getElementById:el,importNode:n=>{const copy=new Node(n.tag);if(n.id)copy.id=n.id;return copy;},querySelector:q=>q==='main.shell'?main:q==='.control-panel'?panel:q==='.tabs'?el('tabs'):pipeline};
 for(const id of ['next','stage','auto','pause','stop','exportProject','projectFile','start'])el(id)[id==='projectFile'?'onchange':'onclick']=async()=>{};
 for(const key of ['students','couples','review','versions','takeover']){const button=new Node('button');button.dataset.tab=key;button.onclick=()=>{context.tab=key;for(const item of el('tabs').children)item.classList.toggle('selected',item===button);};el('tabs').append(button);}
 const state={done:true,config:{awardEnabled:true,mode:'demo'},calls:1,execution:'auto',runtimeSettingId:'setting',couples:[{id:'c1',title:'情侣'}]};
 const a={project:null,inFlight:false,execution:null,cancelQueue(){this.execution=null;},render(){el('author-status').textContent='当前阶段';},async api(action,data){calls.push({action,data});if(action==='validate')return {couples:[{id:'c1'}]};if(action==='create'||action==='import')return {schema_version:'model-couple-author-project-v2',project_id:'p',setting:{setting_id:'setting'},couple_id:'c1',locks:{},task:{stage:'chronos'},stage:'chronos',status:'paused'};if(action==='pause')return {...this.project,status:'paused'};if(action==='export')return this.project;},async run(mode){calls.push({action:'run',mode});this.project.task=null;this.project.stage='disclosure';},downloadLocal(name,value){downloads.push(value);}};
 for(const id of ['create','restore','nominate','resume','file'])el(id)[id==='file'?'onchange':'onclick']=async()=>{};
 // 原HTML控件在被前缀重命名后保留其处理器。
 const oldImport=doc.importNode;doc.importNode=n=>{const copy=oldImport(n);copy.onclick=async()=>{};copy.onchange=async()=>{};return copy;};
 context=vm.createContext({CREATION_PROMPTS:JSON.parse(fs.readFileSync(__dirname+'/prompts.json','utf8')),console,JSON,Object,Error,Promise,DataTransfer:class{constructor(){this.files=[];this.items={add:file=>this.files.push(file)};}},location:{hash:''},document:doc,DOMParser:class{parseFromString(){return {querySelector:()=>fragmentMain};}},fetch:async()=>({ok:true,text:async()=>''}),window:{authorUI:a},traceStages:{},tab:'students',state,busy:false,paused:false,stopped:false,$:el,status:msg=>el('status').textContent=msg,runtimeReady:()=>true,runtimeSetting:()=>({setting_id:'setting'}),renderLog(){},render(){context.renderCreativeArchive?.();},projectArchive:()=>({schema_version:'model-couple-project-v1',state:context.state}),validateProject:x=>{if(!x.state)throw Error('无效工程');return x.state;},importProject:raw=>{context.state=JSON.parse(raw).state;context.paused=true;},confirm:()=>true});
 if(real){const adapter=context;context=real.context;for(const key of ['document','DOMParser','fetch','DataTransfer','location','window','confirm'])context[key]=adapter[key];context.window.authorUI=a;}
 vm.runInContext(source,context);for(let i=0;i<12;i++)await new Promise(resolve=>setImmediate(resolve));
 return {context,el,a,calls,downloads,pipeline};
}
async function main(){
 const archiveOnly=process.argv.includes('--archive-only');
 const {setup:creationSetup}=require('./test_student_foundry.cjs');if(!archiveOnly){const real=creationSetup();real.run('globalThis.hookCalls=0;globalThis.unifiedAfterCreation=async()=>{if(state.done)hookCalls++}');await real.el('start').onclick();for(let i=0;i<40&&!real.state().done;i++)await real.run('execute(runId)');assert.equal(real.state().done,true);assert.equal(real.run('hookCalls'),1);}
 const h=await setup();assert.equal(h.pipeline.children.length,9);await h.context.unifiedAfterCreation();assert.equal(h.calls.filter(x=>x.action==='create').length,1);assert.equal(h.calls.filter(x=>x.action==='run').length,1);assert.equal(h.a.project.stage,'disclosure');await h.context.unifiedAfterCreation();assert.equal(h.calls.filter(x=>x.action==='create').length,1);
 assert.equal(h.el('author-replanDisclosure').hidden,false);h.a.project.task={stage:'script'};h.a.project.script_feasibility={blocked:true};h.context.unifiedControls();for(const id of ['next','stage','auto'])assert(h.el(id).disabled);h.a.project.script_feasibility={blocked:false};h.context.unifiedControls();assert(!h.el('next').disabled);
 const taskBefore=JSON.stringify(h.a.project.task);await h.pipeline.children[4].onclick();assert.equal(JSON.stringify(h.a.project.task),taskBefore);assert.equal(h.el('stageFilter').value,'chronos');assert(h.el('callCount').textContent.includes('任务 1 次'));
 await h.el('exportProject').onclick();assert.equal(h.downloads[0].schema_version,'model-couple-unified-project-v1');assert.equal(h.downloads[0].link.setting_id,'setting');
 h.el('projectFile').files=[{size:1,text:async()=>JSON.stringify(h.downloads[0])}];await h.el('projectFile').onchange({target:h.el('projectFile')});assert.equal(h.a.project.status,'paused');assert.equal(h.calls.filter(x=>x.action==='run').length,1);
 const result=h.el('tabs').children.find(x=>x.dataset.tab==='author');assert.equal(h.context.tab,'author');assert(result.classList.contains('selected'));assert(h.el('output').hidden);
 const couplesTab=h.el('tabs').children.find(node=>node.dataset.tab==='couples');couplesTab.click();assert.equal(h.context.tab,'couples');assert(!result.classList.contains('selected'));assert(!h.el('output').hidden);result.click();assert(result.classList.contains('selected'));assert(!couplesTab.classList.contains('selected'));
 h.a.project.results={chronos:{sentinel:'旧作者卡片'}};h.context.unifiedAuthorChanged();const authorResult=h.context.document.querySelector('main.shell').children[2].children.at(-1);assert(authorResult.children.length>=1);
 const creation=h.downloads[0].creation;h.el('projectFile').files=[{size:1,text:async()=>JSON.stringify(creation)}];await h.el('projectFile').onchange({target:h.el('projectFile')});assert.equal(h.context.tab,'students');assert.equal(h.a.project,null);assert.equal(authorResult.children.length,0);assert(!h.el('output').hidden);assert(authorResult.hidden);
 h.el('output').append(h.context.document.createElement('article'));h.el('projectFile').files=[{size:1,text:async()=>JSON.stringify(h.downloads[0].author)}];await h.el('projectFile').onchange({target:h.el('projectFile')});assert.equal(h.context.state,null);assert.equal(h.context.tab,'author');assert.equal(h.el('output').children.length,0);assert(result.classList.contains('selected'));
 h.a.project.results={chronos:{sentinel:'运行设定导入前的卡片'}};h.context.unifiedAuthorChanged();h.el('output').append(h.context.document.createElement('article'));h.el('projectFile').files=[{size:1,text:async()=>JSON.stringify({schema_version:'model-couple-runtime-v1',setting_id:'setting'})}];await h.el('projectFile').onchange({target:h.el('projectFile')});assert.equal(h.context.state,null);assert.equal(h.a.project,null);assert.equal(authorResult.children.length,0);assert.equal(h.el('output').children.length,0);assert.equal(h.context.tab,'author');assert.equal(h.calls.filter(x=>x.action==='run').length,1);
 // 结构化档案只读筛选、稳定ID姓名映射与注入安全。
 const archive=await setup(),allText=node=>[node.textContent,...node.children.map(allText)].join('\n');
 archive.context.state.students=[{id:'s1',name:'甲同学',personality:'<img src=x onerror=alert(1)>'},{id:'s2',name:'乙同学'}];
 archive.context.state.couples=[{id:'stable-couple',title:'不应出现在交接项的故事标题',members:['s1','s2'],story:{events:[{text:'事件正文'}]}}];
 archive.context.state.versions=[{stage:'人物',students:[]}];archive.context.state.reviews=[{agent:'C_Prometheus',approved:false,summary:'审查问题哨兵'}];
 archive.context.agentStage={C_Prometheus:'person'};archive.context.unifiedControls();
 assert.equal(archive.el('handoffCouple').children[0].value,'stable-couple');assert.equal(archive.el('handoffCouple').children[0].textContent,'甲同学 & 乙同学');
 archive.context.render();assert(allText(archive.el('output')).includes('甲同学'));assert(allText(archive.el('output')).includes('草稿'));assert(allText(archive.el('output')).includes('版本'));assert(allText(archive.el('output')).includes('审查问题哨兵'));
 assert(!archive.el('output').querySelectorAll('*').some(node=>node.tag==='img'));assert(allText(archive.el('output')).includes('<img src=x onerror=alert(1)>'));
 const before=JSON.stringify(archive.context.state);archive.el('archivePerson').value='s2';archive.el('archivePerson').onchange();assert(!allText(archive.el('output')).includes('<img'));assert.equal(JSON.stringify(archive.context.state),before);
 archive.el('archivePerson').value='shared';archive.el('archivePerson').onchange();assert(!allText(archive.el('output')).includes('个性'));
 const tabByKey=key=>archive.el('tabs').children.find(node=>node.dataset.tab===key);
 assert.deepEqual(archive.el('tabs').children.filter(node=>node.dataset.tab&&!node.hidden).map(node=>node.textContent),['人物设定','关系故事','故事细节','个人记忆','报名剧情','填写报名表','本人披露','答辩剧本','读稿态度']);
 archive.a.project={members:['s1','s2'],stage:'script',task:{stage:'script'},locks:{script:true},results:{script:{title:'双人答辩',characters:['s1','s2'],scenes:[{id:'scene1',title:'第一场景',beats:[{performers:['s1','s2'],text:'双人陈述哨兵',action:'翻阅资料',duration_seconds:35}]}],backstage:[]}},versions:[],reviews:[]};
 tabByKey('script').click();const scriptText=allText(archive.el('output'));for(const text of ['甲同学','乙同学','第一场景','双人陈述哨兵','动作','时长（秒）','已锁定','原始 JSON'])assert(scriptText.includes(text),text);
 assert(archive.el('output').querySelectorAll('*').filter(node=>node.tag==='details').every(node=>!node.open));
 const target=JSON.stringify(archive.a.project.task);archive.el('archivePerson').value='s1';archive.el('archivePerson').onchange();assert.equal(JSON.stringify(archive.a.project.task),target);assert.equal(archive.calls.length,0);
 // 收尾回归：框架年表、角色优先归类、版本内部筛选、真实锁字段和读稿关联。
 archive.context.state.lockedStudents=JSON.stringify(archive.context.state.students);tabByKey('students').click();archive.context.render();assert(allText(archive.el('output')).includes('已锁定'));
 archive.context.state.couples[0].story.stages=[{title:'关系阶段保留哨兵'}];
 archive.context.state.versions=[{stage:'人物',students:[{id:'s1',name:'人物版本甲哨兵'},{id:'s2',name:'人物版本乙哨兵'}]},{stage:'框架',agent:'Aphrodite',couples:[{id:'c1',members:['s1','s2'],title:'细节版本哨兵'},{id:'c2',members:['s3','s4'],title:'其他情侣哨兵'}]}];
 archive.context.agentStage.Aphrodite='detail';tabByKey('students').click();archive.context.render();assert(allText(archive.el('output')).includes('人物版本甲哨兵'));assert(!allText(archive.el('output')).includes('人物版本乙哨兵'));
 tabByKey('couples').click();archive.context.render();assert(allText(archive.el('output')).includes('关系阶段保留哨兵'));assert(!allText(archive.el('output')).includes('事件正文'));assert(!allText(archive.el('output')).includes('细节版本哨兵'));
 tabByKey('detail').click();assert(allText(archive.el('output')).includes('细节版本哨兵'));assert(!allText(archive.el('output')).includes('其他情侣哨兵'));
 archive.a.project.results.script.scenes[0].beats[0].id='beat-preview';archive.a.project.results.attitude={s1:{student_id:'s1',reactions:[{beat_id:'beat-preview',feeling:'读稿感受哨兵'}]}};
 tabByKey('attitude').click();for(const text of ['对应台词预览','双人陈述哨兵','翻阅资料','35','读稿感受哨兵'])assert(allText(archive.el('output')).includes(text),text);
 const old=await setup();old.context.state.config.awardEnabled=false;await old.context.unifiedAfterCreation();assert.equal(old.calls.length,0);
 const paused=await setup();paused.context.paused=true;await paused.context.unifiedAfterCreation();assert.equal(paused.calls.filter(x=>x.action==='create').length,1);assert(!paused.calls.some(x=>x.action==='run'));
 const strict=await setup();strict.context.runtimeReady=()=>false;strict.context.unifiedControls();assert(strict.el('enableAward').disabled);await strict.el('enableAward').onclick();await strict.context.unifiedAfterCreation();assert.equal(strict.calls.length,0);
 const unfinished=await setup();unfinished.context.state.done=false;unfinished.context.unifiedControls();assert(unfinished.el('enableAward').disabled);await unfinished.el('enableAward').onclick();assert.equal(unfinished.calls.length,0);
 const stopping=await setup();let release;const api=stopping.a.api;stopping.a.api=async(action,data)=>{if(action==='create')await new Promise(resolve=>release=resolve);return api.call(stopping.a,action,data);};const transfer=stopping.context.unifiedAfterCreation();await new Promise(resolve=>setImmediate(resolve));await stopping.el('stop').onclick();release();await transfer;assert(!stopping.calls.some(x=>x.action==='run'));assert(stopping.calls.some(x=>x.action==='pause'));
 // 只读用户原档，不输出正文；真实前期导入、审查门槛与装配器共同执行。
 const archivePath=__dirname+'/../creation-unified-project.json',raw=fs.readFileSync(archivePath,'utf8');
 const realImport=creationSetup(),actual=await setup(realImport);
 const loadActual=async()=>{actual.el('projectFile').files=[{size:Buffer.byteLength(raw),text:async()=>raw}];await actual.el('projectFile').onchange({target:actual.el('projectFile')});};
 await loadActual();assert.equal(realImport.state().done,true);assert.equal(realImport.state().phase,'done');assert.equal(realImport.state().config.mode,'api');assert.equal(realImport.state().config.awardEnabled,false);assert(realImport.run('runtimeReady()'));assert.equal(actual.a.project,null);
 for(const id of ['next','stage','auto'])assert(actual.el(id).disabled);
 assert.equal(actual.el('enableAward').disabled,false);assert(actual.el('handoffStatus').textContent.includes('未启用'));assert.equal(actual.calls.length,0);
 const snapshot=JSON.stringify(realImport.state());let confirmation='';actual.context.confirm=message=>{confirmation=message;return false;};await actual.el('enableAward').onclick();assert(confirmation.includes('可能调用模型并产生费用'));assert.equal(JSON.stringify(realImport.state()),snapshot);assert.equal(actual.calls.length,0);
 actual.el('awardEnabled').checked=true;actual.el('awardEnabled').onchange();assert.equal(realImport.state().config.awardEnabled,true);assert.equal(actual.calls.length,0);actual.el('awardEnabled').checked=false;actual.el('awardEnabled').onchange();assert.equal(realImport.state().config.awardEnabled,false);assert(actual.el('next').disabled);
 actual.context.confirm=()=>true;await actual.el('enableAward').onclick();assert.equal(realImport.state().config.awardEnabled,true);assert.equal(actual.el('awardEnabled').checked,true);assert.deepEqual(actual.calls.map(x=>x.action),['validate','create']);assert.equal(actual.calls[1].data.mode,'api');assert.equal(actual.calls[1].data.award_enabled,true);assert.equal(actual.a.project.status,'paused');assert.equal(actual.el('next').disabled,false);assert(actual.el('status').textContent.includes('保持暂停'));assert.equal(realImport.state().done,true);assert.equal(realImport.state().phase,'done');
 await loadActual();actual.calls.length=0;const createApi=actual.a.api;actual.a.api=async(action,data)=>{if(action==='create')throw Error('离线创建失败哨兵');return createApi.call(actual.a,action,data);};await actual.el('enableAward').onclick();assert.equal(actual.a.project,null);assert(actual.el('status').textContent.includes('离线创建失败哨兵'));assert(actual.el('handoffStatus').textContent.includes('可点击入口重试'));assert.equal(actual.el('enableAward').disabled,false);assert(!actual.calls.some(x=>['step','run'].includes(x.action)));
 actual.a.api=createApi;await actual.el('enableAward').onclick();assert.equal(actual.a.project.status,'paused');assert(!actual.calls.some(x=>['step','run'].includes(x.action)));assert.equal(fs.readFileSync(archivePath,'utf8'),raw);
 console.log('实际归档离线VM通过：严格导入、未授权灰态与可用入口、取消无变化、勾选同步、确认仅创建、暂停待执行、失败原因与重试，原档未修改。');
 console.log('统一装配器通过：九阶段、严审交接、纯恋爱结束、同次自动授权、外部门槛、暂停导入、双引擎导出、交接停止隔离。');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
