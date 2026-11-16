// 使用独立无头浏览器临时档案；仅访问 Vite 开发服务，不构建。
const assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const {mkdtempSync}=require('node:fs');
const {tmpdir}=require('node:os');
const path=require('node:path');
(async()=>{
  const profile=mkdtempSync(path.join(tmpdir(),'couple-test-'));
  const browser=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=9367',`--user-data-dir=${profile}`,'about:blank'],{stdio:'ignore'});
  let ws;
  try {
    await new Promise((resolve,reject)=>{
      const deadline=Date.now()+15000;
      const check=()=>fetch('http://127.0.0.1:9367/json').then(r=>r.json()).then(resolve).catch(e=>{if(Date.now()>deadline)reject(e);else setTimeout(check,100);});check();
    });
    const tabs=await(await fetch('http://127.0.0.1:9367/json')).json();
    ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
    await new Promise(r=>ws.addEventListener('open',r,{once:true}));
    let seq=0;const pending=new Map(),errors=[],requests=[];
    ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}if(m.method==='Runtime.exceptionThrown')errors.push(m.params);if(m.method==='Network.requestWillBeSent')requests.push(m.params.request.url);};
    const cmd=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
    const ev=async expression=>{const r=await cmd('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
    const until=async expression=>{for(let i=0;i<100;i++){if(await ev(expression))return;await new Promise(r=>setTimeout(r,50));}throw Error('等待失败 '+expression);};
    const click=async action=>{await ev(`document.querySelector('[data-action="${action}"]').click()`);};
    const scene=()=>ev('document.getElementById("game").dataset.scene');
    const saved=()=>ev('JSON.parse(localStorage.getItem("excellent-couple-v2"))');
    const reload=async()=>{await cmd('Page.reload');await until('!!document.querySelector("[data-action=start-game]")');await click('start-game');};
    await cmd('Runtime.enable');await cmd('Network.enable');await cmd('Page.enable');
    // 阻断论坛请求，确保无真实 AI 调用；答辩网络检测另行检查。
    await cmd('Network.setBlockedURLs',{urls:['*/api/*']});
    await cmd('Emulation.setDeviceMetricsOverride',{width:1920,height:1080,deviceScaleFactor:1,mobile:false});
    await cmd('Page.navigate',{url:process.env.AWARD_TEST_ENTRY||'http://127.0.0.1:5173'});
    await until('!!document.querySelector("[data-action=start-game]")');
    await click('start-game');assert.equal(await scene(),'chat');
    await click('received');await until('document.getElementById("game").dataset.scene==="meeting"');
    for(let i=0;i<12;i++)await click('next-line');
    assert.equal(await scene(),'notice');
    assert.ok(await ev('document.querySelector(".official-notice").innerText.includes("2025年4月24日")'));
    assert.equal(await ev('document.querySelector(".couple-notice-scene").innerText.includes("华清")'),false);
    await click('publish-notice');await click('preview-couple-form');
    assert.equal(await ev('document.querySelectorAll(".form-page").length'),4);
    await click('collect-forms');assert.equal(await scene(),'review');
    assert.equal(await ev('document.querySelectorAll("[data-couple]").length'),1);
    assert.ok(await ev('document.querySelector(".couple-review").innerText.includes("苏晚棠 & 郑亦航")'));
    for(const text of ['研一（2024级）','大二（2023级，五年制）','待补充','未授权','非学生签署'])assert.ok(await ev(`document.querySelector('.couple-review').innerText.includes(${JSON.stringify(text)})`));
    assert.equal((await saved()).selected.length,0);assert.equal(await ev('document.querySelector("[data-action=start-defense]").disabled'),true);
    await click('toggle-c1');await reload();assert.equal(await scene(),'review');assert.deepEqual((await saved()).selected,['c1']);
    await click('toggle-c1');assert.equal(await ev('document.querySelector("[data-action=start-defense]").disabled'),true);await click('toggle-c1');
    await click('start-defense');assert.equal(await scene(),'defense');
    const requestStart=requests.length;
    const total=Number((await ev('document.querySelector(".progress").innerText')).split('/')[1].trim());
    for(let i=0;i<total;i++){
      if(i===10){await reload();assert.equal((await saved()).defenseStep,10);}
      assert.ok(await ev(`document.querySelector('.progress').innerText.includes('${i+1} / ${total}')`));
      assert.equal(await ev('/\\bs[34]\\b/.test(document.querySelector(".couple-defense").innerText)'),false);
      await click('next-couple-speech');
    }
    assert.equal(await scene(),'coupleEnd');assert.ok(await ev('!!document.querySelector("[data-status=couple-defense-ended]")'));
    await reload();assert.equal(await scene(),'coupleEnd');
    assert.equal(requests.slice(requestStart).filter(url=>url.includes('/api/')).length,2,'只有刷新启动原有日常论坛请求，无答辩AI请求');
    assert.equal(requests.filter(url=>/successful-run|role_private|\/api\/defense/.test(url)).length,0);
    await click('back-title');assert.equal(await ev('document.querySelector(".title-logo").innerText'),'优秀情侣奖');
    assert.equal(await ev('document.querySelectorAll(".award-option").length'),0);
    assert.equal((await saved()).scene,'coupleEnd');assert.equal(errors.length,0,JSON.stringify(errors));
    console.log('PASS 浏览器：筹备会议、2025通知、报名白名单、玩家入围/撤销、刷新恢复、动态条数纯文本发言、答辩结束恢复、无答辩AI请求、单奖项标题。临时浏览器档案：'+profile);
    await cmd('Browser.close');
  }finally{ws?.close();browser.kill();}
})().catch(error=>{console.error(error);process.exitCode=1;});
