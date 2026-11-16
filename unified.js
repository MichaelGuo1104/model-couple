'use strict';
// 两个引擎共享现有工作区；只装配局部控件，不嵌入第二个页面。
(async()=>{
 if(!globalThis.CREATION_PROMPTS?.foundry?.templates||!globalThis.CREATION_PROMPTS?.foundry?.schemas)return;
 const response=await fetch('/creation/author-fragment',{cache:'no-store'});
 if(!response.ok)throw Error('作者控件加载失败，请重启本地服务');
 const fragment=new DOMParser().parseFromString(await response.text(),'text/html');
 const main=document.querySelector('main.shell'),columns=[...main.children];
 let viewing='creation',switching=false,epoch=0,linked=null;
 const original={};
 for(const id of ['next','stage','auto','pause','stop','exportProject','projectFile','start'])original[id]=$(id)[id==='projectFile'?'onchange':'onclick'];
 const panel=document.querySelector('.control-panel');
 const creationGroups=columns.map(column=>{const wrapper=document.createElement('div');wrapper.style.display='contents';for(const child of [...column.children])if(child!==panel)wrapper.append(child);column.append(wrapper);return wrapper;});
 const authorGroups=[...fragment.querySelector('main').children].map((source,i)=>{
  const wrapper=document.createElement('div');wrapper.style.display='contents';
  for(const child of [...source.children])wrapper.append(document.importNode(child,true));
  for(const node of wrapper.querySelectorAll('[id]'))node.id='author-'+node.id;
  for(const node of wrapper.querySelectorAll('[for]'))node.htmlFor='author-'+node.htmlFor;
  wrapper.hidden=true;columns[i].append(wrapper);return wrapper;
 });
 // 主控制区始终只有一套。作者内部控制保留状态与原生处理器供适配器使用。
 const authorControl=document.getElementById('author-step').closest('section');
 for(const node of authorControl.querySelectorAll('button'))node.hidden=true;
 const stages=document.createElement('div');stages.id='author-stages';stages.hidden=true;for(let i=0;i<4;i++)stages.append(document.createElement('span'));columns[0].append(stages);
 const script=document.createElement('script');script.src='/creation/author-engine.js';
 await new Promise((resolve,reject)=>{script.onload=resolve;script.onerror=reject;document.body.append(script);});
 const a=window.authorUI,A=id=>document.getElementById('author-'+id);
 const choiceLabel=document.createElement('label');choiceLabel.textContent='后续作者流程情侣';const choice=document.createElement('select');choice.id='handoffCouple';choiceLabel.append(choice);panel.append(choiceLabel);
 const names={chronos:'05 Chronos',disclosure:'06 披露 Icelos',script:'07 Muse',attitude:'08 态度 Icelos'};
 const pipeline=document.querySelector('.pipeline');pipeline.setAttribute('aria-label','八阶段神明作者创作进度');
 for(const [key,name] of Object.entries(names)){const button=document.createElement('button');button.type='button';button.className='stage';button.dataset.authorStage=key;button.textContent=name;button.onclick=()=>show('author',key);pipeline.append(button);}
 for(const node of pipeline.querySelectorAll('[data-step]')){node.tabIndex=0;node.role='button';node.onclick=()=>{show('creation');$('stageFilter').value=node.dataset.step;renderLog();};node.onkeydown=e=>{if(e.key==='Enter')node.click();};}
 function show(engine,key){if((busy||a.inFlight||a.execution||switching)&&engine!==viewing){status('请先暂停并等待当前请求结束，再查看其他阶段');return;}viewing=engine;creationGroups.forEach(x=>x.hidden=engine!=='creation');authorGroups.forEach(x=>x.hidden=engine!=='author');if(key){A('filter').value=key;A('filter').onchange();}if(engine==='creation')controls();sync();if(engine==='author'&&!a.project&&!switching){$('status').textContent=state&&!state.done?'请先完成前四阶段，或导入旧作者工程继续。':'导入运行设定／作者工程，或按工程ID暂停恢复；不会自动付费。';}}
 function sync(){
  if(state?.couples?.length&&choice.dataset.source!==JSON.stringify(state.couples.map(c=>c.id))){choice.dataset.source=JSON.stringify(state.couples.map(c=>c.id));choice.replaceChildren();for(const c of state.couples){const option=document.createElement('option');option.value=c.id;option.textContent=c.title;choice.append(option);}}
  if(viewing==='creation'&&state?.done&&state.config.awardEnabled&&runtimeReady()&&!a.project&&!switching&&!busy)for(const id of ['next','stage','auto'])$(id).disabled=false;
  if(viewing==='author'){
   const p=a.project,waiting=busy||switching||a.inFlight||!!a.execution;
   for(const id of ['next','stage','auto'])$(id).disabled=waiting||!p?.task||p.status==='stopped';
   $('pause').disabled=!p;$('pause').textContent='暂停';$('stop').disabled=!p;
   $('start').disabled=busy||switching||a.inFlight||!!a.execution;
   $('status').textContent=switching?'正在交接已审查设定…':A('status').textContent;
   $('callCount').textContent='设定 '+(state?.calls||0)+' · 后续 '+(p?.calls||0)+' 次调用';
  }
  for(const node of pipeline.querySelectorAll('[data-author-stage]')){const p=a.project,key=node.dataset.authorStage;node.classList.toggle('active',viewing==='author'&&p?.stage===key);node.classList.toggle('complete',!!p?.locks[key]);}
 }
 globalThis.unifiedControls=sync;
 const authorRender=a.render;
 // 原渲染和原控制仍由作者引擎独立负责，适配器仅同步外壳状态。
 async function attach(setting,mode,continueAuto=false){
  if(switching||a.inFlight)throw Error('交接或请求仍在进行');
  const token=epoch;switching=true;sync();
  try{
   const summary=await a.api('validate',{setting},true);
   const couple=choice.value||summary.couples[0]?.id;
   if(!couple)throw Error('设定中没有可交接情侣');
   const project=await a.api('create',{setting,couple_id:couple,mode,award_enabled:true});
   linked={setting_id:setting.setting_id,couple_id:couple};a.project=project;
   if(token!==epoch){a.project=await a.api('pause',{project_id:project.project_id});continueAuto=false;}
   authorRender();switching=false;show('author');
  }finally{switching=false;sync();}
  if(continueAuto&&token===epoch)await a.run('auto');sync();
 }
 globalThis.unifiedAfterCreation=async()=>{
  if(!state?.done||!state.config.awardEnabled||!runtimeReady()||a.project||switching||a.inFlight)return;
  try{await attach(runtimeSetting(),state.config.mode,state.execution==='auto'&&!paused&&!stopped);}catch(error){status('交接未完成：'+error.message,true);}
 };
 for(const [id,mode] of [['next','step'],['stage','stage'],['auto','auto']])$(id).onclick=async()=>{
  if(viewing==='author'){await a.run(mode);sync();return;}
  if(state?.done&&state.config.awardEnabled&&!a.project){await globalThis.unifiedAfterCreation();if(a.project)await a.run(mode);sync();return;}
  return original[id]();
 };
 for(const action of ['pause','stop'])$(action).onclick=async()=>{
  epoch++;
  if(switching){paused=true;stopped=action==='stop';status('已取消交接后的自动执行；交接返回后保持暂停');return;}
  if(viewing==='author'){await A(action).onclick();sync();return;}return original[action]();
 };
 $('start').onclick=async()=>{if(a.inFlight||a.execution||switching)return;if(a.project&&!confirm('新建设定将解除当前后续工程关联；原后端工程仍保留。继续？'))return;const previous=state;show('creation');await original.start();if(state!==previous){epoch++;a.cancelQueue();a.project=null;linked=null;}};
 function download(name,value){a.downloadLocal(name,value);}
 $('exportProject').onclick=async()=>{
  if(busy||a.inFlight||switching||a.execution){status('请先暂停并等待当前请求结束，再导出工程',true);return;}
  try{let creation=state?projectArchive():null;if(creation)validateProject(creation);const author=a.project?await a.api('export',{project_id:a.project.project_id,kind:'project'}):null;if(creation&&author){if(creation.state.runtimeSettingId===author.setting.setting_id)linked={setting_id:author.setting.setting_id,couple_id:author.couple_id};else creation=null;}if(!creation&&!author)throw Error('暂无工程');download('creation-unified-project.json',{schema_version:'model-couple-unified-project-v1',creation,author,link:linked});}catch(error){status(error.message,true);}
 };
 A('save').onclick=()=>$('exportProject').onclick();A('save').textContent='导出统一可续写工程';
 $('projectFile').onchange=async event=>{
  try{
   if(busy||switching||a.inFlight||a.execution)throw Error('请暂停并等待请求结束后导入');
   const file=event.target.files?.[0];if(!file)return;if(file.size>20*1024*1024)throw Error('工程超过20 MiB');
   const input=JSON.parse(await file.text());let creation=null,author=null;
   if(input.schema_version==='model-couple-unified-project-v1'){
    creation=input.creation;author=input.author;
    if(!creation&&!author)throw Error('统一工程为空');
    if(creation)validateProject(creation);
    if(creation&&author&&(!creation.state.done||creation.state.runtimeSettingId!==input.link?.setting_id||author.setting?.setting_id!==input.link?.setting_id||author.couple_id!==input.link?.couple_id))throw Error('两引擎关联身份不一致');
   }else if(input.schema_version==='model-couple-project-v1'){validateProject(input);creation=input;}
   else if(input.schema_version==='model-couple-author-project-v1')author=input;
   else if(input.schema_version==='model-couple-runtime-v1'){
    if(a.project&&!confirm('导入运行设定将替换当前作者工程显示；后端原工程仍保留。继续？'))return;const summary=await a.api('validate',{setting:input},true);
    A('couple').replaceChildren();for(const c of summary.couples){const option=document.createElement('option');option.value=c.id;option.textContent=c.title;A('couple').append(option);}
    // 复用原设定导入，创建工程由显式按钮决定，绝不在导入时付费。
    const transfer=new DataTransfer();transfer.items.add(file);A('file').files=transfer.files;await A('file').onchange();a.project=null;linked=null;show('author');return;
   }else throw Error('未知工程类型');
   if((state||a.project)&&!confirm('导入将替换当前页面工程；已持久化后续工程不删除。确认已保存当前工作？'))return;
   const imported=author?await a.api('import',{project:author}):null;
   epoch++;a.cancelQueue();if(creation)importProject(JSON.stringify(creation),false);else{state=null;paused=true;stopped=false;}
   a.project=imported;linked=input.link||null;if(imported)authorRender();show(imported?'author':'creation');status('工程已导入并暂停，不会自动调用模型');
  }catch(error){status(error.message,true);}finally{$('projectFile').value='';}
 };
 // 让原生作者动作结束后同步共用控制，不改业务状态机。
 for(const id of ['create','restore','nominate','resume','file']){const event=id==='file'?'onchange':'onclick',handler=A(id)[event];A(id)[event]=async(...args)=>{if(busy||switching){status('设定请求或交接未结束，不可替换后续工程',true);return;}await handler(...args);sync();};}
 const target=location.hash.slice(1);if(Object.hasOwn(names,target))show('author',target);else sync();
})().catch(error=>status(error.message,true));
