'use strict';
// 显式启用付费实测；DOM仅替代浏览器界面，所有接口均连接现有本地服务。
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const origin='http://127.0.0.1:8765';
async function main(){
 if(!process.argv.includes('--live'))throw Error('实际付费运行须显式传入 --live');
 const configPath=require('node:path').resolve(__dirname,'../common/config.json'),before=fs.readFileSync(configPath),config=JSON.parse(before);
 assert(['base','key','model'].every(k=>typeof config[k]==='string'&&config[k].trim()),'配置无效，停止');
 const safe=s=>[config.key,config.base].filter(Boolean).reduce((v,k)=>v.split(k).join('[已过滤]'),String(s));
 let requests=0,pending=null,configLoad=null,attempted=null;
 const elements=new Map(),el=id=>{if(!elements.has(id))elements.set(id,{value:'',checked:false,disabled:false,hidden:false,textContent:'',innerHTML:'',classList:{toggle(){},remove(){}}});return elements.get(id);};
 const html=fs.readFileSync(__dirname+'/student-foundry.html','utf8');
 Object.entries({mode:'api',count:'3',pairs:'1',personRounds:'1',rounds:'1',brief:html.match(/id="brief"[^>]*>([^<]*)<\/textarea>/)[1],filter:'all',...config}).forEach(([k,v])=>el(k).value=v);
 el('step').checked=true;
 const fetchLocal=async(path,options={})=>{
  assert(typeof path==='string'&&path.startsWith('/')&&!path.startsWith('//'),'只允许本地同源接口');
  assert(path!=='/api/config/save','禁止写配置');
  if(path==='/api/chat'){assert(requests<10,'请求预算已耗尽');requests++;const t=vm.runInContext('task()',context);attempted={agent:t.agent,label:t.label};}
  return fetch(origin+path,{...options,headers:{...options.headers,Origin:origin}});
 };
 const health=await fetchLocal('/health');assert(health.ok&&(await health.json()).service==='student-foundry-relay','现有服务不可用，停止');
 const context=vm.createContext({console,structuredClone,AbortController,URL,Blob,crypto:crypto.webcrypto,document:{getElementById:el,querySelectorAll:()=>[],createElement:()=>({click(){}})},window:{addEventListener(){}},confirm:()=>true,setTimeout,clearTimeout,fetch:(path,opts)=>{const promise=fetchLocal(path,opts);if(path==='/api/config/load')configLoad=promise;return promise;}});
 const run=code=>vm.runInContext(code,context);
 try{
  run(html.match(/<script>([\s\S]*?)<\/script>/)[1]);
  await configLoad;await new Promise(resolve=>setImmediate(resolve));
  // 跟踪真实execute的Promise，避免轮询或跳过前端异常处理。
  context.track=promise=>{pending=promise;return promise;};
  run('const originalExecute=execute;execute=id=>track(originalExecute(id));');
  await el('start').onclick();if(pending)await pending;
  let steps=0;
  const report=()=>{
   const s=run('state'),last=s?.logs.filter(x=>x.agent!=='System').at(-1);
   console.log(safe(JSON.stringify({request:requests,role:attempted?.agent,label:attempted?.label,lastCommittedRole:last?.agent,phase:s?.phase,status:el('status').textContent,waiting:s?.waiting})));
  };
  report();
  while(true){
   const s=run('state');assert(s,'前端未启动：'+safe(el('status').textContent));
   await run('journal.queue');assert(!run('journal.failure'),'日志不可写，停止');
   if(run('paused'))break;
   if(s.waiting==='person'){
    console.log('人物达到1次修订上限：按本次授权自动触发人工接受，非审查通过，保留原问题。');
    run("audit('diagnostic_authorization','User',{action:'按本次授权自动人工接受人物',personRounds:1,rounds:1,maxRequests:10})");
    el('acceptPerson').onclick();
   }
   if(s.done||s.waiting==='couple'||requests>=10)break;
   assert(++steps<=10,'执行步数超限');await run('execute(runId)');report();
  }
  run("audit('diagnostic_end','System',{requests:"+requests+",phase:state.phase,done:state.done,waiting:state.waiting,personAcceptance:state.personAcceptance})");
  await run('journal.queue');
  const s=run('state');
  console.log(safe(JSON.stringify({requests,done:s.done,phase:s.phase,personAcceptance:s.personAcceptance,personRevisions:s.personRevisions,coupleRevisions:s.coupleRevisions,students:s.students.length,couples:s.couples.length,reviews:s.reviews.map(r=>({agent:r.agent,round:r.round,approved:r.approved,issues:r.issues.length})),warnings:s.logs.filter(x=>x.label==='结构归一化警告').map(x=>x.summary),failures:s.logs.filter(x=>x.label==='步骤失败').map(x=>x.summary),journal:run('journal.path'),logFailure:run('journal.failure')})));
  assert(!run('paused'),'实际步骤失败，已停止且未重试');
 }finally{
  assert(crypto.createHash('sha256').update(before).digest('hex')===crypto.createHash('sha256').update(fs.readFileSync(configPath)).digest('hex'),'配置被外部改动');
  console.log('配置内容哈希一致，未写入配置；实际模型请求数：'+requests);
 }
}
main().catch(()=>{console.error('诊断停止：服务、配置、日志或实际步骤异常；未重试。请查看本轮日志及前面的脱敏状态。');process.exitCode=1;});
