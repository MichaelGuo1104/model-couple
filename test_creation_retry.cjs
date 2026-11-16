'use strict';
// 全部接口与计时器隔离，不读取配置、不调用真实模型。
const assert=require('node:assert/strict');
const {setup}=require('./test_student_foundry.cjs');
async function fixture(sequence,options={}){
 let h,n=0,serial=0;const requests=[],waits=[],active=new Map();
 h=setup({TypeError,setTimeout(fn,ms){const id=++serial;active.set(id,{fn,ms});if(ms===500||ms===2000||ms===4000||ms===8000||ms===15000){if(ms!==500)waits.push(ms);if(!options.holdWait||ms===500)queueMicrotask(()=>{if(active.delete(id))fn();});}return id;},clearTimeout(id){active.delete(id);},fetch:async(url,opts={})=>{
  if(url.includes('/config/'))throw Error('隔离配置');
  if(url==='/health')return {ok:true,json:async()=>({service:'student-foundry-relay'})};
  if(url.startsWith('/api/log/'))return {ok:true,json:async()=>({run_id:'offline',path:'offline',written:true})};
  assert.equal(url,'/api/chat');requests.push(JSON.parse(opts.body));const action=sequence[n++]??'good';
  if(action==='network')throw new TypeError('网络断开 secret-test-key');
  if(action==='timeout'){[...active.values()].find(x=>x.ms===(requests.at(-1).timeout_seconds+30)*1000).fn();throw Error('超时');}
  if(action==='backendTimeout')return {ok:false,status:504,headers:{get:()=>null},text:async()=>JSON.stringify({error:'后端等待超时',timeout_source:'backend'})};
  if(action==='pending'||action==='pendingBad')return new Promise((resolve,reject)=>{h.release=()=>resolve(response(action==='pendingBad'?'missing':'good'));opts.signal.addEventListener('abort',()=>reject(Error('已取消')),{once:true});});
  return response(action);
 }});
 function response(action){const status=typeof action==='number'?action:200;let content;
  if(action==='badJSON')content='{ secret-test-key';
  else {const d=h.run('demo(task())');if(action==='missing')delete d.summary;if(action==='invalid')d.students[0].age=17;content=JSON.stringify(d);}
  return {ok:status===200,status,headers:{get:()=>null},text:async()=>JSON.stringify(status===200?{choices:[{message:{content}}]}:{upstream_status:status,error:'HTTP '+status})};
 }
 // 只建立空工程；随后恢复真实执行函数，避免初始化自动调用。
 h.run('globalThis.realExecute=execute;execute=()=>{}');await h.el('start').onclick();h.run('execute=realExecute;state.config.mode="api";state.config.base="https://offline.invalid/v1";state.config.model="offline";state.config.autoRetry=true;state.config.maxRetries=2');
 return {h,requests,waits,active,start:()=>h.el('next').onclick()};
}
async function main(){
 for(const error of ['network','timeout','backendTimeout',408,504,429,500,501,599,'badJSON','missing','invalid']){
  const f=await fixture([error,'good']);await f.start();assert.equal(f.requests.length,2,String(error));assert.equal(f.h.state().phase,'person_review');assert.equal(f.h.state().versions.length,1);assert.equal(f.h.state().requestAttempts,2);assert.deepEqual(f.waits,[['timeout','backendTimeout',408,504].includes(error)?15000:2000]);assert(f.requests.every(r=>r.timeout_seconds===300));if(error==='timeout')assert.match(f.h.state().logs.find(x=>x.label==='API 尝试失败').summary,/前端总等待超过330秒/);
  if(['badJSON','missing','invalid'].includes(error)){const feedback=f.requests[1].payload.messages.at(-1).content;assert.match(feedback,/上次调用未提交/);assert.match(feedback,error==='badJSON'?/合法 JSON/:error==='missing'?/\$\.summary.*缺少/:/成年年龄/);}
  await f.h.flush();assert(!JSON.stringify(f.h.events).includes('secret-test-key'));assert(!JSON.stringify(f.h.state().logs).includes('secret-test-key'));
 }
 for(const seconds of [30,720,1800]){const f=await fixture(['pending']);f.h.run(`state.config.timeoutSeconds=${seconds}`);const p=f.start();for(let i=0;i<30&&!f.h.release;i++)await Promise.resolve();assert.equal(f.requests[0].timeout_seconds,seconds);assert([...f.active.values()].some(x=>x.ms===(seconds+30)*1000));f.h.release();await p;assert(![...f.active.values()].some(x=>x.ms===(seconds+30)*1000));}
 const legacy=await fixture(['good']);legacy.h.run('delete state.config.timeoutSeconds');await legacy.start();assert.equal(legacy.requests[0].timeout_seconds,300);
 for(const value of ['', '29','1801','30.5','true']){const h=setup();h.el('timeoutSeconds').value=value;await h.el('start').onclick();assert.equal(h.state(),null);assert.match(h.el('status').textContent,/30–1800/);}
 const hint=setup();hint.el('timeoutSeconds').value='720';hint.el('timeoutSeconds').oninput();assert.match(hint.el('timeoutHint').textContent,/750秒/);
 const mixed=await fixture(['network','missing','good']);await mixed.start();assert.equal(mixed.requests.length,3);assert.deepEqual(mixed.waits,[2000,4000]);assert.equal(mixed.h.state().versions.length,1);
 const exhausted=await fixture(['network','missing','invalid','good']);await exhausted.start();assert.equal(exhausted.requests.length,3);assert.equal(exhausted.h.state().phase,'students');assert.equal(exhausted.h.state().versions.length,0);assert.equal(exhausted.h.state().reviews.length,0);assert.equal(exhausted.h.run('paused'),true);await exhausted.start();assert.equal(exhausted.h.state().phase,'person_review');assert.equal(exhausted.h.state().requestAttempts,4);
 for(const code of [400,401,403,404]){const f=await fixture([code,'good']);await f.start();assert.equal(f.requests.length,1);assert.equal(f.h.state().phase,'students');}
 const disabled=await fixture(['missing','good']);disabled.h.run('state.config.autoRetry=false');await disabled.start();assert.equal(disabled.requests.length,1);
 for(const control of ['pause','stop']){
  const f=await fixture(['missing','good'],{holdWait:true});const p=f.start();for(let i=0;i<30&&!f.waits.length;i++)await Promise.resolve();assert.equal(f.waits.length,1);f.h.el(control).onclick();await p;assert.equal(f.requests.length,1);assert.equal(f.h.state().phase,'students');assert.equal(f.h.state().versions.length,0);
  const timed=await fixture(['timeout','good'],{holdWait:true});const tp=timed.start();for(let i=0;i<40&&!timed.waits.length;i++)await Promise.resolve();assert.deepEqual(timed.waits,[15000]);timed.h.el(control).onclick();await tp;assert.equal(timed.requests.length,1);assert.equal(timed.active.size,0);
  const inflight=await fixture(['pending','good']);const q=inflight.start();for(let i=0;i<30&&!inflight.h.release;i++)await Promise.resolve();assert(inflight.h.release);inflight.h.el(control).onclick();if(control==='pause'){inflight.h.release();}await q;assert.equal(inflight.requests.length,1);assert.equal(inflight.h.state().phase,control==='pause'?'person_review':'students');
 }
 const pauseFailure=await fixture(['pendingBad','good']);const pending=pauseFailure.start();for(let i=0;i<30&&!pauseFailure.h.release;i++)await Promise.resolve();pauseFailure.h.el('pause').onclick();pauseFailure.h.release();await pending;assert.equal(pauseFailure.requests.length,1);assert.equal(pauseFailure.h.state().phase,'students');
 const review=await fixture(['good','missing','good']);await review.start();await review.start();assert.equal(review.requests.length,3);assert.equal(review.h.state().reviews.length,1);assert.equal(review.h.state().versions.length,1);assert.equal(review.h.state().reviews[0].approved,false,'真实未通过审查不得因重试被改为通过');
 const nested=await fixture(['good']);assert.match(nested.h.run("(()=>{const d=demo(task());delete d.students[0].voice;try{validate(task(),d)}catch(e){return e.message}})()"),/\$\.students\[0\]\.voice/);
 const archive=await fixture(['good']);archive.h.run('state.config.autoRetry=true;state.config.maxRetries=7;importProject(JSON.stringify(projectArchive()),false)');assert.equal(archive.h.state().config.autoRetry,true);assert.equal(archive.h.state().config.maxRetries,7);archive.h.run('const old=projectArchive();delete old.state.config.autoRetry;delete old.state.config.maxRetries;importProject(JSON.stringify(old),false)');assert.equal(archive.h.state().config.autoRetry,false);assert.equal(archive.h.state().config.maxRetries,2);archive.h.run('validateProject(projectArchive())');
 const saved=await fixture(['good']);saved.h.run('state.config.timeoutSeconds=720;importProject(JSON.stringify(projectArchive()),false)');assert.equal(saved.h.state().config.timeoutSeconds,720);assert.equal(saved.h.el('timeoutSeconds').value,'720');assert.match(saved.h.el('timeoutHint').textContent,/750秒/);saved.h.run('const oldTimeout=projectArchive();delete oldTimeout.state.config.timeoutSeconds;importProject(JSON.stringify(oldTimeout),false)');assert.equal(saved.h.state().config.timeoutSeconds,300);
 for(const value of [true,false,null,'300',29,1801,30.5])assert.throws(()=>saved.h.run(`{const p=projectArchive();p.state.config.timeoutSeconds=${JSON.stringify(value)};validateProject(p)}`),/30–1800/);
 console.log('重试离线测试通过：网络/超时/408/429/5xx、JSON/缺字段/严格校验反馈、共享预算与耗尽续写、不可恢复HTTP、默认关闭、退避取消、请求暂停/停止、脱敏、工程新旧往返。');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
