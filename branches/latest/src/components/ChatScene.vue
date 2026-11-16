<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { people, image } from '../content.js';
import { chatTime, replySchedule, MEETING_DELAY_MS } from '../chatTimeline.js';
const props=defineProps({player:String,paused:Boolean,notice:String});
const emit=defineEmits(['receive']);
const entries=ref([{id:'guo',at:0}]),sent=ref(false),messages=ref(null);
const canSend=computed(()=>!sent.value&&!props.paused);
const scheduled=replySchedule();
let elapsed=0,started=0,timer=null,transitionAt=Infinity,disposed=false,completed=false,principalClosed=false;
function now(){return elapsed+(props.paused?0:Math.max(0,performance.now()-started));}
function complete(){if(completed||disposed)return;completed=true;clearTimeout(timer);timer=null;emit('receive');}
function pump(){
  timer=null;if(disposed||props.paused||completed)return;
  const t=now();
  while(scheduled.length&&scheduled[0].at<=t){const reply=scheduled.shift();entries.value.push({id:reply.id,at:reply.at});}
  if(!scheduled.length&&sent.value&&!principalClosed){principalClosed=true;entries.value.push({id:'guo-close',person:'guo',at:t,text:'好，大家按时来开会'});transitionAt=t+900;}
  if(t>=MEETING_DELAY_MS||t>=transitionAt){complete();return;}
  const next=Math.min(scheduled[0]?.at??Infinity,MEETING_DELAY_MS,transitionAt);
  timer=setTimeout(pump,Math.max(0,next-t));
}
function send(){if(!canSend.value)return;const t=now();if(t>=MEETING_DELAY_MS){complete();return;}sent.value=true;entries.value.push({id:'player',at:t});transitionAt=Infinity;clearTimeout(timer);pump();}
watch(()=>props.paused,value=>{
  if(value){elapsed+=Math.max(0,performance.now()-started);clearTimeout(timer);timer=null;}
  else{started=performance.now();pump();}
},{flush:'sync'});
watch(()=>entries.value.length,async()=>{await nextTick();if(messages.value)messages.value.scrollTop=messages.value.scrollHeight;});
onMounted(()=>{started=performance.now();if(!props.paused)pump();});
onBeforeUnmount(()=>{disposed=true;clearTimeout(timer);});
</script>
<template>
<div class="chat-layout"><section class="chat-panel" aria-label="奖励执行委员会工作群">
<div class="chat-title"><span>奖励执行委员会（7人）</span><span>工作群</span></div>
<div ref="messages" class="messages" role="log" aria-live="polite" aria-relevant="additions">
<div v-for="entry in entries" :key="entry.id" class="message" :class="{'player-message':entry.id==='player'}">
<div v-if="entry.id==='player'" class="player-nameplate" aria-label="玩家名牌">{{ player||'你' }}</div>
<img v-else class="avatar" :src="image(people[entry.person||entry.id].thumb)" :alt="people[entry.person||entry.id].name" draggable="false">
<div class="message-content"><div class="message-name">{{ entry.id==='player'?(player||'你'):people[entry.person||entry.id].name }}　{{ chatTime(entry.at) }}</div><div class="bubble">{{ entry.text||(entry.id==='guo'?notice:'收到') }}</div></div>
</div></div>
<div class="chat-send"><label class="reply-label" for="chat-reply">回复</label><input id="chat-reply" value="收到" readonly aria-label="回复内容"><button class="primary" data-action="received" :disabled="!canSend" @click="send">发送</button></div>
</section></div>
</template>
<style scoped>
.chat-layout {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  padding: 40px 64px;
  gap: 0;
}
.chat-panel {
  display: flex;
  flex-direction: column;
  flex: none;
  width: 1120px;
  max-width: 100%;
  height: 100%;
  min-height: 0;
  margin: 0;
}
.messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.chat-send {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-shrink: 0;
}
.reply-label {
  font-size: 18px;
}
.chat-send input {
  flex: 1;
  min-width: 0;
  padding: 14px 18px;
  border: 1px solid var(--ink);
  font-size: 21px;
}
.player-nameplate {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 76px;
  min-height: 64px;
  padding: 8px;
  border: 1px solid var(--ink);
  background: var(--paper);
  font-size: 17px;
  overflow-wrap: anywhere;
}
</style>
