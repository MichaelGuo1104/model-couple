'use strict';
// 真实作者闭包与原始日志渲染共同执行；网络仅使用内存工程，不读配置。
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {setup}=require('./test_student_foundry.cjs');
async function main(){
 const h=setup();await h.el('start').onclick();
 const originalCount=h.state().logs.length;
 const nodes=new Map();
 const node=()=>({value:'all',checked:false,children:[],classList:{toggle(){}},append(...children){this.children.push(...children);},replaceChildren(){this.children=[];},scrollIntoView(){},click(){}});
 const authorEl=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);};
 for(let i=0;i<4;i++)authorEl('stages').children.push(node());
 const p={project_id:'offline',mode:'demo',status:'paused',award_enabled:true,stage:'chronos',calls:0,locks:{},results:{},logs:[],task:{stage:'chronos',agent:'Chronos'}};
 h.context.authorEl=authorEl;h.context.document.createElement=node;h.context.localStorage={getItem(){},setItem(){}};
 h.context.fetch=async(url,options)=>{const action=url.split('/').at(-1);assert(!url.includes('config'));if(action==='step'){p.calls++;p.logs.push({kind:'response_committed',task:{...p.task},detail:'<img src=x onerror=alert(1)>'});}if(action==='stop')p.status='stopped';if(action==='resume'||action==='import')p.status='paused';return {ok:true,json:async()=>structuredClone(p)};};
 const author=fs.readFileSync(__dirname+'/author-panel.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
 h.run('(()=>{'+author.replace('const $=id=>document.getElementById(id);','const $=authorEl;')+'\nglobalThis.a={run,render,get project(){return project},set project(v){project=v}};})()');
 const unified=fs.readFileSync(__dirname+'/unified.js','utf8');
 h.run("Object.assign(traceStages,{chronos:'生活与报名',disclosure:'本人披露',script:'共同剧本',attitude:'读稿态度'});");
 h.run(unified.match(/globalThis\.unifiedLogs=\(\)=>[^\n]+/)[0]);
 h.run('globalThis.unifiedAuthorChanged=()=>renderLog("append");a.project='+JSON.stringify(p)+';a.render()');
 h.el('follow').checked=true;await h.run('a.run("step")');
 assert.equal(h.run('traceLogs().length'),originalCount+1);assert.equal(h.state().logs.length,originalCount);
 assert(h.el('log').innerHTML.includes('group-person'));assert(h.el('log').innerHTML.includes('group-chronos'));assert(!h.el('log').innerHTML.includes('<img'));assert(h.el('log').innerHTML.includes('&lt;img'));
 h.run('a.render();a.render()');assert.equal(h.run('traceLogs().length'),originalCount+1);
 h.el('stageFilter').value='chronos';h.el('stageFilter').onchange();assert.equal(h.run('traceFiltered().length'),1);assert.equal(h.run('a.project.task.stage'),'chronos');
 h.run('a.project.logs.push({kind:"failure",task:{stage:"script",agent:"Muse"},detail:"失败哨兵"});a.render()');
 h.el('kindFilter').value='error';h.el('stageFilter').value='all';h.el('kindFilter').onchange();assert.equal(h.run('traceFiltered().length'),1);h.el('locateError').onclick();assert(h.el('log').innerHTML.includes('失败哨兵'));
 const archive=h.run('JSON.stringify({creation:state,author:a.project})');h.run('a.project=JSON.parse('+JSON.stringify(archive)+').author;a.render();a.render()');assert.equal(h.run('traceLogs().length'),originalCount+2);
 h.run('state=null;a.render()');assert.equal(h.run('traceLogs().length'),2);assert(h.el('log').innerHTML.includes('失败哨兵'));
 h.run('a.project.logs.push({kind:"project_imported",detail:"无任务系统事件"});a.render()');assert.equal(h.run('traceLogs().at(-1).metadata.stage'),'system');assert(h.el('log').innerHTML.includes('group-system'));h.el('stageFilter').value='chronos';h.el('kindFilter').value='all';h.el('stageFilter').onchange();assert.equal(h.run('traceFiltered().length'),1);
 await authorEl('stop').onclick();assert.equal(h.run('a.project.status'),'stopped');await authorEl('resume').onclick();assert.equal(h.run('a.project.status'),'paused');
 console.log('真实作者与原日志联合VM通过：连续追加、保留历史、筛选不改任务、XSS、错误定位、重复渲染及往返无重复、作者独立导入、停止恢复。');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
