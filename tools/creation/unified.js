'use strict';
// 两个引擎共享现有工作区；只装配局部控件，不嵌入第二个页面。
(async()=>{
 if(!globalThis.CREATION_PROMPTS?.foundry?.templates||!globalThis.CREATION_PROMPTS?.foundry?.schemas)return;
 const response=await fetch('/creation/author-fragment',{cache:'no-store'});
 if(!response.ok)throw Error('作者控件加载失败，请重启本地服务');
 const fragment=new DOMParser().parseFromString(await response.text(),'text/html');
 const main=document.querySelector('main.shell'),columns=[...main.children];
 let switching=false,epoch=0,linked=null;
 const activeAuthor=()=>!!window.authorUI?.project&&(state?.done||!state);
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
 const stages=document.createElement('div');stages.id='author-stages';stages.hidden=true;for(let i=0;i<5;i++)stages.append(document.createElement('span'));columns[0].append(stages);
 const script=document.createElement('script');script.src='/creation/author-engine.js';
 await new Promise((resolve,reject)=>{script.onload=resolve;script.onerror=reject;document.body.append(script);});
 const a=window.authorUI,A=id=>document.getElementById('author-'+id);
 // 作者轨迹与输出仅保留隐藏兼容节点，可见内容始终复用原三栏。
 for(const group of authorGroups){group.hidden=true;group.style.display='none';}
 for(const section of [...authorGroups[0].children]){if(section===authorControl)continue;section.className='section';columns[0].append(section);}
 for(const id of ['file','couple','mode','award']){A(id).hidden=true;const label=A(id).closest('label');if(label?.tagName==='LABEL')label.hidden=true;}
 A('save').hidden=true;
 const resume=A('resume');resume.hidden=false;panel.append(resume);
 const enableAward=document.createElement('button');enableAward.id='enableAward';enableAward.type='button';enableAward.textContent='启用颁奖对接 / 进入Chronos';panel.append(enableAward);
 const handoffStatus=document.createElement('div');handoffStatus.id='handoffStatus';handoffStatus.className='status';panel.append(handoffStatus);
 let handoffError='';
 const awardChange=$('awardEnabled').onchange;
 $('awardEnabled').onchange=(...args)=>{awardChange?.(...args);if(state?.done&&!a.project&&!switching){state.config.awardEnabled=$('awardEnabled').checked;handoffError='';sync();}};
 enableAward.onclick=async()=>{
  if(!state?.done||!runtimeReady()||a.project||busy||switching||a.inFlight||a.execution)return;
  const message='确认启用颁奖对接并创建 Chronos 工程？只创建并保持暂停，不执行下一步；前期审定内容不变。'+(state.config.mode==='api'?' 当前为 API 模式，后续点击一步／阶段／自动可能调用模型并产生费用。':'');
  if(!confirm(message))return;
  state.config.awardEnabled=true;$('awardEnabled').checked=true;handoffError='';
  try{await attach(runtimeSetting(),state.config.mode,false);status('已进入 Chronos 并保持暂停，请显式选择一步／阶段／自动');}
  catch(error){handoffError='颁奖对接失败：'+error.message+'。可点击入口重试。';status(handoffError,true);}
  sync();
 };
 function retrySettings(){A('retry').checked=$('autoRetry').checked;A('retries').value=$('maxRetries').value;}
 const tabs=document.querySelector('.tabs');
 const authorResult=document.createElement('div');authorResult.className='content';authorResult.hidden=true;columns[2].append(authorResult);
 const resultButton=document.createElement('button');resultButton.dataset.tab='author';resultButton.textContent='日常与报名';tabs.append(resultButton);
 resultButton.onclick=()=>{tab='author';$('output').replaceChildren();for(const button of tabs.querySelectorAll('[data-tab]'))button.classList.toggle('selected',button===resultButton);$('output').hidden=true;authorResult.hidden=false;renderAuthorResults();};
 for(const button of tabs.querySelectorAll('[data-tab]'))if(button!==resultButton){const click=button.onclick;button.onclick=(...args)=>{$('output').hidden=false;authorResult.hidden=true;return click?.(...args);};}
 const choiceLabel=document.createElement('label');choiceLabel.textContent='继续创作的情侣';const choice=document.createElement('select');choice.id='handoffCouple';choiceLabel.append(choice);panel.append(choiceLabel);
 const names={chronos:'05 Chronos · 报名剧情',application:'06 Muse · 填写报名表',disclosure:'07 披露 Icelos',script:'08 Muse · 答辩',attitude:'09 态度 Icelos'};
 const pipeline=document.querySelector('.pipeline');pipeline.setAttribute('aria-label','九阶段神明作者创作进度');
 for(const [key,name] of Object.entries(names)){const button=document.createElement('button');button.type='button';button.className='stage';button.dataset.authorStage=key;button.textContent=name;button.onclick=()=>show('author',key);pipeline.append(button);}
 for(const node of pipeline.querySelectorAll('[data-step]')){node.tabIndex=0;node.role='button';node.onclick=()=>{show('creation');$('stageFilter').value=node.dataset.step;renderLog();};node.onkeydown=e=>{if(e.key==='Enter')node.click();};}
 function show(engine,key){if(key)$('stageFilter').value=key;renderLog();sync();}
 function selectResults(author){if(author)resultButton.click();else for(const button of tabs.querySelectorAll('[data-tab]'))if(button.dataset.tab==='students'){button.click();break;}}
 Object.assign(traceStages,{chronos:'报名剧情',application:'填写报名表',disclosure:'本人披露',script:'共同剧本',attitude:'读稿态度'});
 function option(id,value,label){const node=document.createElement('option');node.value=value;node.textContent=label;$(id).append(node);}
 for(const [key,name] of Object.entries(names))option('stageFilter',key,name);
 for(const agent of ['Chronos','C_Chronos','Icelos','C_Icelos','Muse','C_Muse'])option('filter',agent,agent);
 globalThis.unifiedLogs=()=>[...(state?.logs||[]),...(a.project?.logs||[]).map(row=>({time:row.time,agent:row.task?.agent||'System',label:row.kind==='failure'?'执行失败':row.kind,summary:typeof row.detail==='string'?row.detail:JSON.stringify(row.detail??row),data:row,metadata:{stage:row.task?.stage||'system',kind:row.kind==='failure'?'error':row.kind==='response_committed'?(String(row.task?.agent).startsWith('C_')?'review':'creation'):'system'}}))];
 const archiveStages={students:['person','人物设定'],couples:['framework','关系故事'],detail:['detail','故事细节'],takeover:['memory','个人记忆'],author:['chronos','报名剧情'],application:['application','填写报名表'],disclosure:['disclosure','本人披露'],script:['script','答辩剧本'],attitude:['attitude','读稿态度']};
 const people=()=>state?.students||a.project?.setting?.students||[];
 const personName=id=>people().find(person=>person.id===id)?.name||id;
 const coupleName=c=>(c.members||[]).map(personName).join(' & ')||'尚无人物姓名';
 const audienceLabel=document.createElement('label');audienceLabel.textContent='档案人物（仅筛选，不改变运行目标）';
 const audience=document.createElement('select');audience.id='archivePerson';audienceLabel.append(audience);tabs.append(audienceLabel);
 function refreshAudience(){
  const signature=JSON.stringify(people().map(({id,name})=>({id,name})));if(audience.dataset.source===signature)return;
  const selected=audience.value;audience.dataset.source=signature;audience.replaceChildren();
  for(const [value,label] of [['all','全部'],...people().map(p=>[p.id,p.name]),['shared','双人共同']]){const node=document.createElement('option');node.value=value;node.textContent=label;audience.append(node);}
  audience.value=['all','shared',...people().map(p=>p.id)].includes(selected)?selected:'all';
 }
 function visible(ids=[]){return audience.value==='all'||(audience.value==='shared'?ids.length>1:ids.includes(audience.value));}
 function textNode(tag,text,className){const node=document.createElement(tag);node.textContent=String(text??'');if(className)node.className=className;return node;}
 const fieldLabels={summary:'摘要',gender:'性别',age:'年龄',major:'专业',year:'年级',grades:'成绩',personality:'个性',background:'家庭与处境',desire:'渴望',fear:'害怕',contradiction:'内在矛盾',independent_life:'独立生活',voice:'说话方式',current_intentions:'当日意愿',daily_details:'日常细节',cognition:'认知倾向',attraction:'相互吸引',dynamic:'相处特色',tension:'当前张力',stage:'阶段',timeline:'关系年表',time:'时间',event:'经历',date:'日期',text:'正文',action:'动作',emotion:'情绪',duration_seconds:'时长（秒）',performers:'发言人物',characters:'人物',kind:'段落类型',framing:'叙述标签',source_refs:'来源',initial_memories:'初始记忆',private_information:'私人信息',experiences:'经历',attitude:'态度',consent:'本人意愿',form:'个人报名陈述',registration:'报名状态',status:'状态',filled:'已填写',started_on:'开始日期',completed_on:'完成日期',submitted_on:'提交日期',withdrawn_on:'撤回日期',items:'披露条目',stance:'披露立场',reactions:'逐段读稿反应',beat_id:'对应段落',feeling:'感受',reason:'原因',readiness:'准备程度',cooperation:'配合意愿',memory:'读稿记忆',backstage:'答辩准备说明',facts:'共同事实',perspectives:'个人视角',known_duration:'相识时长',dating_duration:'交往时长',stages:'关系阶段',events:'关键事件',habits:'重复活动与习惯',observations:'个人观察',student_id:'人物',approved:'审查通过',issues:'问题',problem:'问题',suggestion:'建议',severity:'程度',preserve:'必须保留',target:'对象',round:'修订轮次'};
 Object.assign(fieldLabels,{id:'编号',name:'姓名',title:'标题',members:'双方人物',story:'关系故事',students:'人物档案',couples:'情侣档案',agent:'创作角色',label:'任务说明',task:'任务',value:'版本内容',response:'审查结果',people:'人物记录',reviewing:'正在审查',version:'版本',candidate_digest:'候选校验标识',student:'人物',observation:'观察',stage_id:'关系阶段编号',meaning:'个人意义',confidence:'确信程度',boundary:'知情边界',score:'倾向分数',evidence:'依据',content:'内容',readiness_note:'准备说明'});
 const valueLabels={application:'填写报名表',person:'人物设定',framework:'关系故事',detail:'故事细节',chronos:'日常与报名',disclosure:'本人披露',script:'答辩剧本',attitude:'读稿态度',memory:'个人记忆',pending:'待处理',review_approved:'审查通过',manual:'人工接受',manual_accepted:'人工接受',draft:'草稿',approved:'通过',rejected:'未通过',not_started:'未开始',in_progress:'进行中',completed:'已完成',yes:'愿意',no:'不愿意',undecided:'尚未决定',ready:'已准备好',reluctant:'有所保留',submitted:'已提交',withdrawn:'已撤回',not_submitted:'未提交',dialogue:'台词',action:'动作',chorus:'双人共同陈述',fact:'事实标签',interpretation:'个人理解标签',staging:'表达加工标签'};
 function readable(parent,value,key=''){
  if(value===null||value===undefined)return;
  if(Array.isArray(value)){
   const list=document.createElement('ol');for(const item of value){const row=document.createElement('li');readable(row,item,key);list.append(row);}parent.append(list);return;
  }
  if(typeof value==='object'){
   for(const [field,item] of Object.entries(value)){
    const block=document.createElement('div');block.className='body';block.append(textNode('strong',fieldLabels[field]||personName(field)));
    readable(block,item,field);parent.append(block);
    if(field==='beat_id'){
     const scene=a.project?.results?.script?.scenes?.find(scene=>(scene.beats||[]).some(beat=>beat.id===item));
     const beat=scene?.beats.find(beat=>beat.id===item);
     if(beat){const preview=document.createElement('div');preview.append(textNode('strong','对应台词预览 · '+scene.title));readable(preview,{performers:beat.performers,text:beat.text,action:beat.action,duration_seconds:beat.duration_seconds});parent.append(preview);}
    }
   }return;
  }
  const mapped=typeof value==='string'?personName(value):value;
  parent.append(textNode('p',typeof mapped==='boolean'?(mapped?'是':'否'):(valueLabels[mapped]||mapped)));
 }
 function archiveCard(host,title,value,ids=[],statusText='已生成'){
  if(!visible(ids))return;
  const card=document.createElement('article');card.className='card';card.append(textNode('h3',title),textNode('span',statusText,'tag'));
  readable(card,value);
  const raw=document.createElement('details');raw.append(textNode('summary','原始 JSON（折叠）'),textNode('pre',JSON.stringify(value,null,2),'body'));card.append(raw);host.append(card);
 }
 function stageOf(row){return row.task?.stage||(typeof agentStage==='object'?agentStage[row.task?.agent||row.agent]:null)||({人物:'person',框架:'framework',细节:'detail',记忆:'memory'})[row.stage]||row.stage;}
 function filterHistory(value){
  if(audience.value==='all'||!value||typeof value!=='object')return value;
  if(Array.isArray(value))return value.filter(item=>{
   if(!item||typeof item!=='object')return true;
   if(item.student_id)return visible([item.student_id]);
   if(Array.isArray(item.members))return visible(item.members);
   if(people().some(person=>person.id===item.id))return visible([item.id]);
   return true;
  }).map(filterHistory);
  return Object.fromEntries(Object.entries(value).filter(([field])=>!people().some(person=>person.id===field)||visible([field])).map(([field,item])=>[field,filterHistory(item)]));
 }
 function archiveHistory(host,key){
  const history=[...(state?.reviews||[]).map(value=>({type:'审查',value})),...(state?.versions||[]).map(value=>({type:'版本',value})),...(a.project?.reviews||[]).map(value=>({type:'审查',value})),...(a.project?.versions||[]).map(value=>({type:'版本',value}))];
  for(const {type,value} of history){if(stageOf(value)!==key)continue;
   const sid=value.task?.student_id||value.student_id;const ids=sid?[sid]:people().map(p=>p.id);
   if(!visible(ids))continue;
   const approval=value.response?.approved??value.approved;
   const section=document.createElement('details');section.append(textNode('summary',type+' · '+(sid?personName(sid)+' · ':'')+(approval===true?'通过':approval===false?'未通过':'历史记录')));
   readable(section,filterHistory(value));host.append(section);
  }
 }
 function renderArchive(host){
  refreshAudience();host.replaceChildren();const [key,label]=archiveStages[tab]||archiveStages.students,p=a.project,ids=p?.members||people().map(s=>s.id);
  host.append(textNode('h3',label));
  const source=state||p?.setting;
  if(key==='person')for(const person of source?.students||[])archiveCard(host,person.name,person,[person.id],state?((state.personLocked||state.lockedStudents)?'已锁定'+(state.personAcceptance==='manual'?' · 人工接受':' · 审查通过'):'草稿 / 待审查'):'已审定设定');
  if(key==='framework'||key==='detail')for(const couple of source?.couples||[]){
   archiveCard(host,coupleName(couple),key==='framework'?{...couple,...(couple.story?{story:Object.fromEntries(Object.entries(couple.story).filter(([field])=>!['events','habits'].includes(field)))}:{})}:couple.story,couple.members,state?(key==='framework'?(state.lockedFramework?'已锁定':'草稿 / 待审查'):(state.phase==='takeover'||state.done?'已锁定 · 审查通过':'草稿 / 待审查')):'已审定设定');
  }
  if(key==='memory'){
   for(const pack of source?.takeover_packages||[])archiveCard(host,personName(pack.student_id)+' · 个人记忆',pack,[pack.student_id],'已提交 · '+(valueLabels[state?.metadata?.takeover?.[pack.student_id]?.status]||'已审定'));
   if(state?.takeoverDraft)archiveCard(host,personName(state.takeoverDraft.student_id)+' · 个人记忆草稿',state.takeoverDraft,[state.takeoverDraft.student_id],'草稿 / 待审查');
  }
  if(p&&['chronos','application','disclosure','script','attitude'].includes(key)){
   const result=p.results?.[key],locked=p.locks?.[key]?(p.manual_revision?.approved_digests?.[key]?'已锁定 · 人工修订，未经模型复审':'已锁定 · 审查通过'):'已生成 / 阶段未锁定';
   if(key==='chronos'&&result){
    if(audience.value==='all'||audience.value==='shared')archiveCard(host,'双人报名', {summary:result.summary,registration:result.registration},ids,locked);
    for(const [sid,value] of Object.entries(result.people||{}))archiveCard(host,personName(sid)+' · 日常与报名',value,[sid],locked);
   }else if(key==='application'&&result){for(const [sid,value] of Object.entries(result.statements||{}))archiveCard(host,personName(sid)+' · 报名陈述',value,[sid],locked);archiveCard(host,'提交元信息',result.metadata,ids,locked);
   }else if((key==='disclosure'||key==='attitude')&&result){for(const [sid,value] of Object.entries(result))archiveCard(host,personName(sid)+' · '+label,value,[sid],locked);}
   else if(key==='script'&&result){
    archiveCard(host,result.title+' · 双人优秀情侣答辩',{characters:result.characters,backstage:result.backstage},ids,locked);
    for(const scene of result.scenes||[]){const beats=(scene.beats||[]).filter(beat=>visible(beat.performers||[]));if(beats.length)archiveCard(host,scene.title,{...scene,beats}, [...new Set(beats.flatMap(beat=>beat.performers||[]))],locked);}
   }
   if(p.draft&&p.stage===key){const sid=p.task?.student_id||(['disclosure','attitude'].includes(key)?p.members?.[p.person_index]:null);archiveCard(host,label+' · 当前草稿',p.draft,sid?[sid]:ids,'草稿 / '+(p.reviewing?'待审查':'待修订'));}
   if(key==='application'&&p.application)archiveCard(host,'正式报名表',p.application,ids,'正式快照');
  }
  archiveHistory(host,key);
  if(host.children.length===1)host.append(textNode('p','当前筛选下暂无内容；筛选不会改变运行目标。','empty'));
 }
 for(const button of tabs.querySelectorAll('[data-tab]')){
  const entry=archiveStages[button.dataset.tab];if(!entry){button.hidden=true;continue;}button.textContent=entry[1];
 }
 for(const key of ['detail','application','disclosure','script','attitude']){const button=document.createElement('button');button.dataset.tab=key;button.textContent=archiveStages[key][1];tabs.append(button);button.onclick=()=>{tab=key;$('output').hidden=false;authorResult.hidden=true;render();};}
 // 顺序仅影响档案导航，不触碰引擎阶段与任务。
 for(const key of Object.keys(archiveStages)){const button=[...tabs.querySelectorAll('[data-tab]')].find(node=>node.dataset.tab===key);if(button)tabs.append(button);}
 audience.onchange=()=>{render();renderAuthorResults();};
 globalThis.renderCreativeArchive=()=>{if(!state&&!a.project){$('output').replaceChildren();authorResult.replaceChildren();return;}for(const button of tabs.querySelectorAll('[data-tab]'))button.classList.toggle('selected',button.dataset.tab===tab);if(tab==='author'){if(a.project)renderArchive(authorResult);}else renderArchive($('output'));};
 function renderAuthorResults(){authorResult.replaceChildren();if(a.project)renderArchive(authorResult);}
 render();
 let previousLogCount=0;
 globalThis.unifiedAuthorChanged=()=>{const count=globalThis.unifiedLogs().length;renderLog(count>previousLogCount?'append':'view');previousLogCount=count;render();renderAuthorResults();sync();};
 function sync(){
  enableAward.disabled=!state?.done||!runtimeReady()||!!a.project||busy||switching||a.inFlight||!!a.execution;
  handoffStatus.textContent=a.project?'颁奖对接工程已创建，执行由共用控制区决定。':switching?'正在交接已审查设定…':handoffError||(!state?.done?'前期尚未完成，暂不能进入 Chronos。':!runtimeReady()?'前期尚未全部通过严格审查，暂不能交接。':!state.config.awardEnabled?'未启用颁奖对接：当前为纯恋爱完成工程。可点击“启用颁奖对接 / 进入Chronos”确认开启；不会自动调用模型。':'颁奖对接已勾选，尚未创建后续工程。请点击入口确认进入 Chronos。');
  handoffStatus.className='status'+(handoffError&&!a.project?' error':'');
  const couples=state?.couples||a.project?.setting?.couples||[];const choiceSource=JSON.stringify(couples.map(c=>[c.id,coupleName(c)]));
  if(choice.dataset.source!==choiceSource){const selected=choice.value;choice.dataset.source=choiceSource;choice.replaceChildren();for(const c of couples){const option=document.createElement('option');option.value=c.id;option.textContent=coupleName(c);choice.append(option);}if(couples.some(c=>c.id===selected))choice.value=selected;}
  if(!activeAuthor()&&state?.done&&!a.project)for(const id of ['next','stage','auto'])$(id).disabled=!state.config.awardEnabled||!runtimeReady()||switching||busy;
  if(activeAuthor()){
   const p=a.project,waiting=busy||switching||a.inFlight||!!a.execution;
   for(const id of ['next','stage','auto'])$(id).disabled=waiting||!p?.task||p.script_feasibility?.blocked||p.status==='stopped';
   $('pause').disabled=!p;$('pause').textContent='暂停';$('stop').disabled=!p;
   $('start').disabled=busy||switching||a.inFlight||!!a.execution;
   $('status').textContent=switching?'正在交接已审查设定…':A('status').textContent;
   $('runBadge').textContent=p?.stage==='done'?'全部完成':p?.status||'就绪';
   $('traceState').textContent=p?.failure?.message||A('status').textContent;
  }
  if(!activeAuthor())A('resume').disabled=!state||!stopped||busy;
  const authorCalls=a.project?.calls||0,knownRequests=state?.requestAttempts||0;
  const authorRequests=a.project?.mode==='demo'?0:a.project?.logs?.filter(row=>row.kind==='request').length;
  $('callCount').textContent='任务 '+((state?.calls||0)+authorCalls)+' 次 · 已记录 API 请求 '+(knownRequests+(authorRequests||0))+' 次'+(a.project?.mode==='api'?'（作者历史仅统计保留的请求证据）':'');
  for(const node of pipeline.querySelectorAll('[data-author-stage]')){const p=a.project,key=node.dataset.authorStage;node.classList.toggle('active',activeAuthor()&&p?.stage===key);node.classList.toggle('complete',!!p?.locks[key]);}
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
  if(continueAuto&&token===epoch){retrySettings();await a.run('auto');}sync();
 }
 globalThis.unifiedAfterCreation=async()=>{
  if(!state?.done||!state.config.awardEnabled||!runtimeReady()||a.project||switching||a.inFlight)return;
  try{await attach(runtimeSetting(),state.config.mode,state.execution==='auto'&&!paused&&!stopped);}catch(error){status('交接未完成：'+error.message,true);}
 };
 for(const [id,mode] of [['next','step'],['stage','stage'],['auto','auto']])$(id).onclick=async()=>{
  if(activeAuthor()){retrySettings();await a.run(mode);sync();return;}
  if(state?.done&&state.config.awardEnabled&&!a.project){await globalThis.unifiedAfterCreation();if(a.project){retrySettings();await a.run(mode);}sync();return;}
  return original[id]();
 };
 for(const action of ['pause','stop'])$(action).onclick=async()=>{
  epoch++;
  if(switching){paused=true;stopped=action==='stop';status('已取消交接后的自动执行；交接返回后保持暂停');return;}
  if(activeAuthor()){await A(action).onclick();sync();return;}return original[action]();
 };
 $('start').onclick=async()=>{if(a.inFlight||a.execution||switching)return;if(a.project&&!confirm('新建设定将解除当前后续工程关联；原后端工程仍保留。继续？'))return;const previous=state;show('creation');await original.start();if(state!==previous){epoch++;a.cancelQueue();a.project=null;linked=null;globalThis.unifiedAuthorChanged();selectResults(false);}};
 function download(name,value){a.downloadLocal(name,value);}
 $('exportProject').onclick=async()=>{
  if(busy||a.inFlight||switching||a.execution){status('请先暂停并等待当前请求结束，再导出工程',true);return;}
  try{let creation=state?projectArchive():null;if(creation)validateProject(creation);const author=a.project?await a.api('export',{project_id:a.project.project_id,kind:'project'}):null;if(creation&&author){if(creation.state.runtimeSettingId===author.setting.setting_id)linked={setting_id:author.setting.setting_id,couple_id:author.couple_id};else throw Error('两引擎关联身份不一致，请分别保存原工程后核对；未丢弃设定工程');}if(!creation&&!author)throw Error('暂无工程');download('creation-unified-project.json',{schema_version:'model-couple-unified-project-v1',creation,author,link:linked});}catch(error){status(error.message,true);}
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
   else if(input.schema_version==='model-couple-author-project-v2')author=input;
   else if(input.schema_version==='model-couple-runtime-v1'){
    if((state||a.project)&&!confirm('导入运行设定将替换当前页面工程；后端原工程仍保留。继续？'))return;const summary=await a.api('validate',{setting:input},true);
    A('couple').replaceChildren();for(const c of summary.couples){const option=document.createElement('option');option.value=c.id;option.textContent=(input.couples?.find(pair=>pair.id===c.id)?.members||c.members||[]).map(id=>input.students?.find(person=>person.id===id)?.name||id).join(' & ')||'尚无人物姓名';A('couple').append(option);}
    // 复用原设定导入，创建工程由显式按钮决定，绝不在导入时付费。
    const transfer=new DataTransfer();transfer.items.add(file);A('file').files=transfer.files;await A('file').onchange();epoch++;a.cancelQueue();state=null;paused=true;stopped=false;$('output').replaceChildren();a.project=null;linked=null;globalThis.unifiedAuthorChanged();selectResults(true);show('author');return;
   }else throw Error('未知工程类型');
   if((state||a.project)&&!confirm('导入将替换当前页面工程；已持久化后续工程不删除。确认已保存当前工作？'))return;
   const imported=author?await a.api('import',{project:author}):null;
   epoch++;a.cancelQueue();if(creation)importProject(JSON.stringify(creation),false);else{state=null;paused=true;stopped=false;$('output').replaceChildren();}
   handoffError='';a.project=imported;linked=input.link||null;if(imported)authorRender();globalThis.unifiedAuthorChanged();selectResults(!!imported);show(imported?'author':'creation');status('工程已导入并暂停，不会自动调用模型');
  }catch(error){status(error.message,true);}finally{$('projectFile').value='';}
 };
 // 让原生作者动作结束后同步共用控制，不改业务状态机。
 for(const id of ['create','restore','nominate','replanDisclosure','resume','file']){const event=id==='file'?'onchange':'onclick',handler=A(id)[event];A(id)[event]=async(...args)=>{if(busy||switching){status('设定请求或交接未结束，不可替换后续工程',true);return;}await handler(...args);sync();};}
 const authorResume=A('resume').onclick;
 A('resume').onclick=async()=>{if(activeAuthor())return authorResume();if(!state||busy||switching)return;stopped=false;paused=true;controls();status('已恢复执行权限，等待显式执行');};
 const target=location.hash.slice(1);if(Object.hasOwn(names,target))show('author',target);else sync();
})().catch(error=>status(error.message,true));
