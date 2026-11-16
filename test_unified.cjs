'use strict';
// 离线执行真实装配器；模型与DOM由可观察替身提供，不启动服务或读取配置。
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/unified.js','utf8');
async function setup(){
 const nodes=new Map(),calls=[],downloads=[];let context;
 class Node{
  constructor(tag='div'){this.tag=tag;this.children=[];this.style={};this.dataset={};this.value='';this.textContent='';this.hidden=false;this.disabled=false;this.files=[];this.classList={toggle(){}};}
  set id(v){this._id=v;nodes.set(v,this);}get id(){return this._id;}
  append(...children){for(const node of children){if(node.parent)node.parent.children=node.parent.children.filter(x=>x!==node);node.parent=this;this.children.push(node);if(node.tag==='option'&&!this.value)this.value=node.value;}if(this===body&&children[0]?.tag==='script')queueMicrotask(()=>children[0].onload());}
  replaceChildren(...children){this.children=[];this.value='';this.append(...children);}
  querySelectorAll(query){const all=this.children.flatMap(x=>[x,...x.querySelectorAll('*')]);if(query==='*')return all;if(query==='[id]')return all.filter(x=>x.id);if(query==='[for]')return [];if(query==='button')return all.filter(x=>x.tag==='button');if(query==='[data-step]')return all.filter(x=>x.dataset.step);if(query==='[data-author-stage]')return all.filter(x=>x.dataset.authorStage);return [];}
  closest(){return this.parent;}remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this);}setAttribute(){}click(){return this.onclick?.();}
 }
 const el=id=>{if(!nodes.has(id)){const n=new Node();n.id=id;}return nodes.get(id);};
 const body=new Node('body'),main=new Node('main'),panel=new Node(),pipeline=new Node();
 for(let i=0;i<3;i++){const col=new Node();col.append(new Node());main.append(col);}main.children[0].append(panel);
 for(const key of ['person','framework','detail','memory']){const node=new Node();node.dataset.step=key;pipeline.append(node);}
 const fragmentMain=new Node('main');for(let i=0;i<3;i++)fragmentMain.append(new Node());
 for(const id of ['step','stage','auto','pause','stop','resume','create','restore','nominate','file','couple','filter','status','projectId','stages']){const n=new Node(id==='file'?'input':'button');n.id=id;fragmentMain.children[0].append(n);}
 const doc={body,createElement:tag=>new Node(tag),getElementById:el,importNode:n=>{const copy=new Node(n.tag);if(n.id)copy.id=n.id;return copy;},querySelector:q=>q==='main.shell'?main:q==='.control-panel'?panel:pipeline};
 for(const id of ['next','stage','auto','pause','stop','exportProject','projectFile','start'])el(id)[id==='projectFile'?'onchange':'onclick']=async()=>{};
 const state={done:true,config:{awardEnabled:true,mode:'demo'},calls:1,execution:'auto',runtimeSettingId:'setting',couples:[{id:'c1',title:'情侣'}]};
 const a={project:null,inFlight:false,execution:null,cancelQueue(){this.execution=null;},render(){el('author-status').textContent='当前阶段';},async api(action,data){calls.push({action,data});if(action==='validate')return {couples:[{id:'c1'}]};if(action==='create'||action==='import')return {schema_version:'model-couple-author-project-v1',project_id:'p',setting:{setting_id:'setting'},couple_id:'c1',locks:{},task:{stage:'chronos'},stage:'chronos',status:'paused'};if(action==='pause')return {...this.project,status:'paused'};if(action==='export')return this.project;},async run(mode){calls.push({action:'run',mode});this.project.task=null;this.project.stage='disclosure';},downloadLocal(name,value){downloads.push(value);}};
 for(const id of ['create','restore','nominate','resume','file'])el(id)[id==='file'?'onchange':'onclick']=async()=>{};
 // 原HTML控件在被前缀重命名后保留其处理器。
 const oldImport=doc.importNode;doc.importNode=n=>{const copy=oldImport(n);copy.onclick=async()=>{};copy.onchange=async()=>{};return copy;};
 context=vm.createContext({CREATION_PROMPTS:JSON.parse(fs.readFileSync(__dirname+'/prompts.json','utf8')),console,JSON,Object,Error,Promise,location:{hash:''},document:doc,DOMParser:class{parseFromString(){return {querySelector:()=>fragmentMain};}},fetch:async()=>({ok:true,text:async()=>''}),window:{authorUI:a},state,busy:false,paused:false,stopped:false,$:el,status:msg=>el('status').textContent=msg,runtimeReady:()=>true,runtimeSetting:()=>({setting_id:'setting'}),renderLog(){},projectArchive:()=>({schema_version:'model-couple-project-v1',state:context.state}),validateProject:x=>{if(!x.state)throw Error('无效工程');return x.state;},importProject:raw=>{context.state=JSON.parse(raw).state;context.paused=true;},confirm:()=>true});
 vm.runInContext(source,context);for(let i=0;i<12;i++)await new Promise(resolve=>setImmediate(resolve));
 return {context,el,a,calls,downloads,pipeline};
}
async function main(){
 const {setup:creationSetup}=require('./test_student_foundry.cjs');const real=creationSetup();real.run('globalThis.hookCalls=0;globalThis.unifiedAfterCreation=async()=>{if(state.done)hookCalls++}');await real.el('start').onclick();for(let i=0;i<40&&!real.state().done;i++)await real.run('execute(runId)');assert.equal(real.state().done,true);assert.equal(real.run('hookCalls'),1);
 const h=await setup();assert.equal(h.pipeline.children.length,8);await h.context.unifiedAfterCreation();assert.equal(h.calls.filter(x=>x.action==='create').length,1);assert.equal(h.calls.filter(x=>x.action==='run').length,1);assert.equal(h.a.project.stage,'disclosure');await h.context.unifiedAfterCreation();assert.equal(h.calls.filter(x=>x.action==='create').length,1);
 await h.el('exportProject').onclick();assert.equal(h.downloads[0].schema_version,'model-couple-unified-project-v1');assert.equal(h.downloads[0].link.setting_id,'setting');
 h.el('projectFile').files=[{size:1,text:async()=>JSON.stringify(h.downloads[0])}];await h.el('projectFile').onchange({target:h.el('projectFile')});assert.equal(h.a.project.status,'paused');assert.equal(h.calls.filter(x=>x.action==='run').length,1);
 const old=await setup();old.context.state.config.awardEnabled=false;await old.context.unifiedAfterCreation();assert.equal(old.calls.length,0);
 const paused=await setup();paused.context.paused=true;await paused.context.unifiedAfterCreation();assert.equal(paused.calls.filter(x=>x.action==='create').length,1);assert(!paused.calls.some(x=>x.action==='run'));
 const strict=await setup();strict.context.runtimeReady=()=>false;await strict.context.unifiedAfterCreation();assert.equal(strict.calls.length,0);
 const stopping=await setup();let release;const api=stopping.a.api;stopping.a.api=async(action,data)=>{if(action==='create')await new Promise(resolve=>release=resolve);return api.call(stopping.a,action,data);};const transfer=stopping.context.unifiedAfterCreation();await new Promise(resolve=>setImmediate(resolve));await stopping.el('stop').onclick();release();await transfer;assert(!stopping.calls.some(x=>x.action==='run'));assert(stopping.calls.some(x=>x.action==='pause'));
 console.log('统一装配器通过：八阶段、严审交接、纯恋爱结束、同次自动授权、外部门槛、暂停导入、双引擎导出、交接停止隔离。');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
