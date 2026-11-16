<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { campusApi, campusError } from '../campusApi.js';
const props=defineProps({sessionId:String,school:String,player:String,awardId:{type:String,default:'couple'},resultPublication:Object,initialTab:{type:String,default:'forum'}});
const emit=defineEmits(['close']);
const tab=ref(props.initialTab), data=ref({threads:[],jobs:[],history:[],announcement:null}), health=ref(null), error=ref(''), busy=ref(false), activeId=ref(''), historyId=ref('');
const nickname=ref('匿名同学'), postTitle=ref(''), postBody=ref(''), replyBody=ref(''), replyTo=ref(null), composing=ref(false), root=ref(null);
let timer=null, disposed=false, loading=false;
const active=computed(()=>data.value.threads.find(t=>t.id===activeId.value));
const volume=computed(()=>data.value.history.find(v=>v.id===historyId.value));
const pending=computed(()=>data.value.jobs.some(j=>['queued','running'].includes(j.status)));
const statusText={queued:'等待生成',running:'学生正在讨论',succeeded:'已完成',failed:'生成失败'};
async function refresh(){
 if(loading)return;loading=true;
 try{const result=await campusApi(`/api/campus?session_id=${encodeURIComponent(props.sessionId)}`);if(!disposed){data.value=result;error.value='';}}
 catch(e){if(!disposed)error.value=e.message;}finally{loading=false;}
}
async function action(path,payload,clear){
 if(busy.value)return;busy.value=true;error.value='';
 try{await campusApi(path,{session_id:props.sessionId,...payload});if(!disposed){clear?.();await refresh();}}
 catch(e){if(!disposed)error.value=e.message;}finally{if(!disposed)busy.value=false;}
}
function generate(){return action('/api/campus/notice',{school:props.school,player:props.player,award_id:props.awardId});}
function generateResult(){if(props.resultPublication)return action('/api/campus/result',props.resultPublication);}
function post(){if(!postTitle.value.trim()||!postBody.value.trim())return;return action('/api/campus/threads',{title:postTitle.value,body:postBody.value,nickname:nickname.value},()=>{postTitle.value='';postBody.value='';composing.value=false;});}
function reply(){if(!replyBody.value.trim()||!active.value)return;return action('/api/campus/comments',{thread_id:active.value.id,body:replyBody.value,nickname:nickname.value,reply_to:replyTo.value},()=>{replyBody.value='';replyTo.value=null;});}
function floor(t,id){const i=t.comments.findIndex(c=>c.id===id);return i<0?'原帖':`${i+2}楼`;}
function trap(event){if(event.key!=='Tab')return;const nodes=[...root.value.querySelectorAll('button,input,textarea,a')].filter(n=>!n.disabled&&n.getClientRects().length);const first=nodes[0],last=nodes.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}}
onMounted(async()=>{await nextTick();root.value?.querySelector('button')?.focus();campusApi('/api/health').then(v=>{if(!disposed)health.value=v;}).catch(()=>{});await refresh();if(!disposed)timer=setInterval(()=>{if(pending.value)refresh();},1800);});
onUnmounted(()=>{disposed=true;clearInterval(timer);});
</script>
<template>
 <div ref="root" class="campus-overlay" role="dialog" aria-modal="true" aria-label="校园公共空间" @keydown="trap">
  <section class="campus-window">
   <header><div><span class="eyebrow">{{ school }} · 校园公共空间</span><h1>校史与论坛</h1></div><button data-action="close-campus" @click="emit('close')">返回游戏 · Esc</button></header>
   <nav aria-label="校园栏目"><button :class="{chosen:tab==='forum'}" data-action="campus-forum" @click="tab='forum'">校园论坛</button><button :class="{chosen:tab==='history'}" data-action="campus-history" @click="tab='history'">校史馆</button><span>{{ health?.mock?'测试桩模式 · 非真实 AI':health?.ai_configured?'统一 AI 接口已配置':'未配置 AI · 可浏览已有内容' }}</span><button :disabled="busy" @click="refresh">刷新状态</button></nav>
   <p v-if="error" class="campus-error" role="alert">{{ error }}</p>
   <main>
    <template v-if="tab==='history'">
     <p class="hint">历史展品为交付项目的既有演示馆藏，不是本局结果；不会把内部纪实送给论坛 AI。</p>
     <template v-if="volume"><button @click="historyId=''">← 馆藏目录</button><h2>{{ volume.title }}</h2><p class="source">{{ volume.source }}</p><div class="plain-text history-text">{{ volume.body }}</div></template>
     <template v-else><button v-for="v in data.history" :key="v.id" class="volume-row" @click="historyId=v.id"><strong>{{ v.title }}</strong><span>{{ v.source }} →</span></button><p v-if="!data.history.length" class="empty">暂无馆藏，或校园服务尚未启动。</p></template>
    </template>
    <template v-else>
     <section v-if="data.announcement" class="announcement"><span class="eyebrow">已公开公文</span><h2>{{ data.announcement.title }}</h2><details><summary>阅读通知全文</summary><div class="plain-text">{{ data.announcement.body }}</div></details></section>
     <section v-if="data.result_announcement" class="announcement result-announcement"><span class="eyebrow">已公开评选结果</span><h2>{{ data.result_announcement.title }}</h2><details><summary>阅读结果公告全文</summary><div class="plain-text">{{ data.result_announcement.body }}</div></details></section>
     <div v-if="resultPublication" class="forum-tools"><button data-action="generate-result-feedback" :disabled="busy||pending" @click="generateResult">同步评选结果反馈</button><span class="hint">讨论已公布的最终获奖结果；失败任务请在下方明确重试。</span></div>
     <div class="forum-tools"><button data-action="generate-off-topic" :disabled="busy||pending" @click="action('/api/campus/off-topic',{})">同步开局日常帖</button><span class="hint">开局生成的校园闲聊，每局一次；不涉及评奖和候选人。</span></div>
     <div class="forum-tools"><button class="primary" data-action="generate-notice-feedback" :disabled="busy||pending" @click="generate">{{ pending?'学生正在生成反馈…':'生成 / 同步公文反馈' }}</button><button :disabled="busy" @click="composing=!composing;activeId=''">{{ composing?'取消发帖':'发表新帖' }}</button><span class="hint">只讨论已公开信息；初始通知与结果公告各自去重。失败后须明确重试。</span></div>
     <div v-for="j in data.jobs.filter(j=>j.status!=='succeeded')" :key="j.id" class="job" role="status"><span>{{ j.kind==='off_topic'?'开局日常帖 · ':j.kind==='result'?'结果公告 · ':j.kind==='notice'?'评选通知 · ':'' }}{{ statusText[j.status]||j.status }}{{ j.error?' · '+campusError(j.error):'' }}</span><button v-if="j.status==='failed'" :disabled="busy||pending" @click="action('/api/campus/retry',{job_id:j.id})">重试（将调用 AI）</button></div>
     <form v-if="composing" class="campus-form" @submit.prevent="post"><h2>发表新帖</h2><label>昵称<input v-model="nickname" maxlength="16" required></label><label>标题<input v-model="postTitle" maxlength="100" required></label><label>正文<textarea v-model="postBody" maxlength="3000" required></textarea></label><button class="primary" :disabled="busy">保存帖子并请求 AI 回应</button></form>
     <template v-else-if="active"><button @click="activeId='';replyTo=null">← 返回帖子列表</button><article class="forum-post"><h2>{{ active.title }}</h2><p class="source">{{ active.author.nickname }} · {{ active.author.kind==='ai'?'AI 学生':'玩家' }} · {{ active.created_at }}</p><div class="plain-text">{{ active.body }}</div></article><article v-for="(c,i) in active.comments" :key="c.id" class="forum-comment"><p class="source">{{ i+2 }}楼 · {{ c.author.nickname }} · {{ c.author.kind==='ai'?'AI 学生':'玩家' }}<span v-if="c.reply_to"> · 回复 {{ floor(active,c.reply_to) }}</span></p><div class="plain-text">{{ c.body }}</div><button class="small" @click="replyTo=c.id">回复这层</button></article><form class="campus-form" @submit.prevent="reply"><h3>{{ replyTo?'回复 '+floor(active,replyTo):'回复主题' }} <button v-if="replyTo" type="button" class="small" @click="replyTo=null">取消指定</button></h3><label>昵称<input v-model="nickname" maxlength="16" required></label><label>内容<textarea v-model="replyBody" maxlength="1200" required></textarea></label><button :disabled="busy" class="primary">保存回复并请求 AI 接话</button></form></template>
     <template v-else><button v-for="t in [...data.threads].reverse()" :key="t.id" class="thread-row" @click="activeId=t.id;replyTo=null"><strong>{{ t.title }}</strong><span>{{ t.author.nickname }} · {{ t.comments.length }} 条回复</span></button><p v-if="!data.threads.length" class="empty">还没有帖子。通知发布后会请求生成公文反馈；未成功时可检查配置后再次同步。</p></template>
    </template>
   </main><footer>本局论坛独立保存 · AI 内容可能有误，不代表校方裁定 · 关闭窗口不取消已提交的生成任务</footer>
  </section>
 </div>
</template>
<style scoped>
.campus-overlay{position:absolute;inset:0;z-index:80;padding:55px 110px;background:#171513c9;display:flex}.campus-window{width:100%;height:100%;background:#eeeae1;border:1px solid var(--ink);box-shadow:0 15px 60px #0006;display:flex;flex-direction:column;color:var(--ink);font-size:23px}.campus-window header{display:flex;align-items:center;justify-content:space-between;padding:25px 40px;border-bottom:2px solid var(--ink)}h1{margin:7px 0 0;font-size:38px;font-weight:400}h2{font-size:29px;margin:12px 0}h3{font-size:25px}.campus-window nav{display:flex;gap:18px;align-items:center;padding:16px 40px;border-bottom:1px solid #aaa}.campus-window nav span{margin-left:auto;font-size:18px;color:#625c55}.chosen{background:var(--ink);color:#fff}.campus-window main{flex:1;overflow:auto;padding:22px 40px;min-height:0}.campus-window footer{padding:13px 40px;border-top:1px solid #aaa;font-size:17px;color:#625c55}.campus-error{background:#f9e3de;color:#8b241b;padding:14px 40px;margin:0;font-size:20px}.hint,.source{font-size:18px;line-height:1.6;color:#676058}.forum-tools{display:flex;gap:15px;align-items:center;margin:20px 0}.forum-tools .hint{flex:1}.announcement{background:#fffaf0;padding:20px 26px;border-left:4px solid var(--red)}summary{cursor:pointer;font-size:20px}.plain-text{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.85;font-size:22px}.history-text{max-width:1200px;margin:20px auto}.thread-row,.volume-row{display:flex;justify-content:space-between;align-items:center;gap:20px;width:100%;text-align:left;border:0;border-bottom:1px solid #bdb7ac;padding:24px 20px;background:transparent}.thread-row strong,.volume-row strong{font-size:25px;font-weight:400}.thread-row span,.volume-row span{font-size:18px;color:#6c6256}.thread-row:hover,.volume-row:hover{background:#fff9ed}.forum-post{padding:18px 22px;background:#fffaf0;margin:20px 0}.forum-comment{padding:15px 22px;border-bottom:1px solid #bdb7ac}.forum-comment .small{margin-top:8px}.campus-form{padding:20px 24px;background:#e4ded2;margin:22px 0}.campus-form label{display:block;font-size:20px;margin-bottom:15px}.campus-form input,.campus-form textarea{display:block;width:100%;padding:12px;font:inherit;margin-top:7px;background:#fffcf6;border:1px solid #a79d8b}.campus-form textarea{height:130px;resize:vertical}.campus-form input{max-width:700px}.empty{text-align:center;color:#786b5c;padding:60px}.job{display:flex;justify-content:space-between;align-items:center;padding:12px 20px;background:#e1dbce;font-size:19px;margin:10px 0}
</style>
