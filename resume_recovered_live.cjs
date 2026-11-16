'use strict';
// 仅隔离浏览器DOM；模型、同源转发、日志与严格校验均使用真实实现。
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {spawn}=require('node:child_process'),readline=require('node:readline');
const root=__dirname,originalSource=root+'/logs/2026-11-15_call23_recovered.project.json';
const source=process.env.RESUME_PROJECT||originalSource,previousRequests=Number(process.env.PREVIOUS_REQUESTS||0);
async function main(){
 assert(process.argv.includes('--live'),'必须显式授权 --live');
 const configBytes=fs.readFileSync(require('node:path').resolve(root,'../common/config.json')),config=JSON.parse(configBytes),sourceBytes=fs.readFileSync(source);
 const safe=x=>[config.key,config.base].filter(Boolean).reduce((s,k)=>s.split(k).join('[已过滤]'),String(x));
 const stamp=new Date().toISOString().replace(/[:.]/g,'-'),prefix=root+'/logs/'+stamp+'_continued';
 const python=`import sys,threading\nsys.path.insert(0,sys.argv[1])\nimport student_server as app\nfrom http.server import ThreadingHTTPServer\ns=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)\ns.upstream_timeout=300\nt=threading.Thread(target=s.serve_forever,daemon=True);t.start()\nprint(s.server_port,flush=True)\ntry: sys.stdin.read()\nfinally: s.shutdown();s.server_close();t.join()\n`;
 const service=spawn('python',['-u','-c',python,root],{stdio:['pipe','pipe','pipe']});
 let stderr='';service.stderr.on('data',x=>{stderr+=safe(x);});
 const exited=new Promise(resolve=>service.on('exit',(code)=>resolve(code)));
 let run,requests=previousRequests,history=[],journalPath='',done=false;
 assert(Number.isInteger(previousRequests)&&previousRequests>=0&&previousRequests<35,'历史预算无效');
 try{
  const origin=await new Promise((resolve,reject)=>{const lines=readline.createInterface({input:service.stdout});lines.once('line',line=>{if(!/^\d+$/.test(line))return reject(Error('临时服务启动失败'));resolve('http://127.0.0.1:'+line);});service.once('error',reject);service.once('exit',()=>reject(Error('临时服务提前退出')));});
  const elements=new Map(),el=id=>{if(!elements.has(id))elements.set(id,{value:'',checked:false,disabled:false,hidden:false,textContent:'',innerHTML:'',scrollTop:0,scrollHeight:1200,clientHeight:400,classList:{toggle(){},remove(){}},addEventListener(){},getBoundingClientRect(){return {top:0};},focus(){},click(){}});return elements.get(id);};
  Object.entries({filter:'all',stageFilter:'all',kindFilter:'all',...config}).forEach(([k,v])=>el(k).value=v);
  const context=vm.createContext({console,structuredClone,AbortController,TextEncoder,URL,Blob,crypto:crypto.webcrypto,document:{getElementById:el,querySelectorAll:()=>[],createElement:()=>({click(){}})},window:{addEventListener(){}},confirm:()=>false,setTimeout:(fn,ms)=>setTimeout(fn,ms===120000?360000:ms),clearTimeout,fetch:async(path,opts={})=>{
   assert(typeof path==='string'&&path.startsWith('/')&&!path.startsWith('//'),'仅允许同源请求');assert(path!=='/api/config/save','禁止改配置');
   if(path==='/api/chat'){assert(requests<35,'35次预算耗尽');requests++;}
   return fetch(origin+path,{...opts,headers:{...opts.headers,Origin:origin}});
  }});
  run=code=>vm.runInContext(code,context);
  run(fs.readFileSync(root+'/student-foundry.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1]);
  run(`importProject(${JSON.stringify(sourceBytes.toString('utf8'))},false)`);
  assert(previousRequests>0||run('state.phase')==='detail_revise','首次必须从detail_revise开始');assert.equal(run('state.config.mode'),'api');assert.equal(run('state.students.length'),4);assert.equal(run('state.couples.length'),1);
  const lockedStudents=run('JSON.stringify(state.students)'),lockedFramework=run('state.lockedFramework');
  await run('startJournal()');journalPath=run('journal.path');
  run(`audit('resume_authorization','System',${JSON.stringify({source:source.split('/').at(-1),max_requests:35,upstream_timeout_seconds:300,frontend_timeout_seconds:360,manual_acceptance:false})})`);
  let consecutiveFailures=0;
  while(!run('state.done')&&requests<35){
   assert(!run('state.waiting'),'出现限额等待，停止以免越权');
   const before=run('state.phase'),agent=run('task().agent'),student=run('state.students[state.takeoverIndex]?.id');
   await el('next').onclick();await run('journal.queue');assert(!run('journal.failure'),'日志失败停止');
   const failure=run('state.lastFailure');
   const row={request:requests,project_call:run('state.calls'),phase:before,agent,student,next_phase:run('state.phase'),error:failure?.error||null};
   if(agent.startsWith('Critic')&&!failure){const r=run('state.reviews.at(-1)');row.approved=r.approved;row.issues=r.issues.map(x=>({target:x.target,problem:x.problem,suggestion:x.suggestion}));}
   history.push(row);console.log(safe(JSON.stringify({...row,issues:row.issues?.length})));
   fs.writeFileSync(prefix+'.steps.json',safe(JSON.stringify({requests,history,journal:journalPath},null,2))+'\n',{flag:'w'});
   fs.writeFileSync(prefix+'.project.json',run('JSON.stringify(projectArchive(),null,2)')+'\n');
   assert.equal(run('JSON.stringify(state.students)'),lockedStudents,'禁止改变既有人物');assert.equal(run('state.lockedFramework'),lockedFramework,'禁止改变框架锁');
   if(failure){consecutiveFailures++;assert(consecutiveFailures<1,'校验失败已留raw与差异，需诊断后再续写');assert(!/超时|110秒|300秒|HTTP|网络|连接|预算/.test(failure.error),'外部请求失败需诊断，不自动重试');}
   else consecutiveFailures=0;
  }
  done=run('state.done');
  if(done){
   assert(run('runtimeReady()'),'完成但未满足严格运行条件');
   const setting=run('runtimeSetting()');
   const response=await fetch(origin+'/api/simulation/validate',{method:'POST',headers:{'Content-Type':'application/json',Origin:origin},body:JSON.stringify({setting})});assert(response.ok,'后端严格校验失败');await response.json();
   const archive=run('JSON.stringify(projectArchive())');run(`importProject(${JSON.stringify(archive)},false)`);assert(run('runtimeReady()'),'完成工程回导后不可运行');assert.equal(run('JSON.stringify(runtimeSetting())'),JSON.stringify(setting),'回导运行设定不一致');
   fs.writeFileSync(prefix+'.runtime.json',JSON.stringify(setting,null,2)+'\n',{flag:'wx'});
  }
 }catch(e){history.push({diagnostic_error:safe(e.message)});console.error(safe(e.message));process.exitCode=1;
 }finally{
  if(run){if(run('journal'))await run('journal.queue');fs.writeFileSync(prefix+'.project.json',run('JSON.stringify(projectArchive(),null,2)')+'\n');}
  service.stdin.end();const code=await exited;
  assert(fs.readFileSync(require('node:path').resolve(root,'../common/config.json')).equals(configBytes),'配置哈希发生变化');assert(fs.readFileSync(source).equals(sourceBytes),'原恢复工程发生变化');
  const summary={done,requests,max_requests:35,cost:'未知',journal:journalPath,project:prefix+'.project.json',runtime:done?prefix+'.runtime.json':null,history,temporary_service_closed:code===0,config_unchanged:true,source_unchanged:true,stderr};
  fs.writeFileSync(prefix+'.steps.json',safe(JSON.stringify(summary,null,2))+'\n');console.log(safe(JSON.stringify({...summary,history:history.map(x=>({...x,issues:x.issues?.length}))})));
 }
}
main().catch(()=>{console.error('诊断终止；未输出敏感配置。');process.exitCode=1;});
