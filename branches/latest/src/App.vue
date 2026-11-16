<script setup>
import { watch, nextTick } from 'vue';
import { useAward } from './useAward.js';
import CoupleNoticeScene from './components/CoupleNoticeScene.vue';
import CoupleReviewScene from './components/CoupleReviewScene.vue';
import CoupleDefenseScene from './components/CoupleDefenseScene.vue';
import CampusPanel from './components/CampusPanel.vue';
import { campusApi } from './campusApi.js';
import { ref } from 'vue';
import TitleScreen from './components/TitleScreen.vue';import PauseMenu from './components/PauseMenu.vue';
import ChatScene from './components/ChatScene.vue';import MeetingScene from './components/MeetingScene.vue';
const {toggleCouple,advanceCouple,award,publishNotice,collectForms,title,paused,startGame,returnTitle,resume,closeSubmenu,state,modal,scale,draft,player,school,candidates,current,advance,receive,startDefense,settings,saveSettings,reset,fullscreen}=useAward();
const chapters=['第一幕 · 开会','第二幕 · 审阅','第三幕 · 答辩','第四幕 · 颁奖'];
const campusTab=ref('forum'), campusMessage=ref('');
function startWithCampus(){
 startGame();
 // Server event is idempotent per session; do not block chat or retry implicitly.
 if(!award.value.campusEnabled||!['http:','https:'].includes(location.protocol))return;
 const session=state.sessionId;
 campusApi('/api/campus/off-topic',{session_id:session}).catch(e=>{
  if(state.sessionId===session)campusMessage.value='开局日常帖未能生成：'+e.message;
 });
}
function openCampus(tab){if(!award.value.campusEnabled||!state.noticePublished||title.value)return;campusTab.value=tab;modal.value='campus';}
async function publishAndNotify(){
 publishNotice();
 campusMessage.value='通知已发布，正在提交论坛反馈任务…';
 const session=state.sessionId;
 try{await campusApi('/api/campus/notice',{session_id:session,...state.noticeContext,award_id:award.value.id});if(state.sessionId===session)campusMessage.value='论坛反馈已提交，可在校园论坛查看进度。';}
 catch(e){if(state.sessionId===session)campusMessage.value=e.message;}
}
watch(()=>state.sessionId,()=>{campusMessage.value='';});
// Keep keyboard focus inside the active overlay; background scene is inert while paused.
watch(modal,async value=>{await nextTick();if(value)document.querySelector('.pause-overlay button, .modal-layer input, .modal-layer button')?.focus();});
</script>
<template><div id="viewport"><main id="game" aria-label="优秀情侣奖" :data-scene="title?'title':state.scene" :style="{transform:`scale(${scale})`}">
<section id="stage" :inert="paused">
<TitleScreen v-if="title" :award="award" @start="startWithCampus" />
<template v-else>
<ChatScene v-if="state.scene==='chat'" :notice="award.chatNotice" :player="player" :paused="paused" @receive="receive" />
<MeetingScene v-else-if="state.scene==='meeting'" :award="award" :line="state.line" :player="player" @next="advance" />
<CoupleNoticeScene v-else-if="state.scene==='notice'&&award.id==='couple'" :school="state.noticeContext?.school||school" :player="player" :published="state.noticePublished" :campus-message="campusMessage" @publish="publishAndNotify" @forum="openCampus('forum')" @history="openCampus('history')" @continue="collectForms" @title="returnTitle" />
<CoupleReviewScene v-else-if="state.scene==='review'&&award.id==='couple'" :candidates="candidates" :selected="state.selected" @toggle="toggleCouple" @submit="startDefense" />
<CoupleDefenseScene v-else-if="award.id==='couple'&&['defense','coupleEnd'].includes(state.scene)&&current" :candidate="current" :step="state.defenseStep" :ended="state.scene==='coupleEnd'" @next="advanceCouple" @title="returnTitle" />
</template></section>
<div id="overlay">
<div v-if="!title&&award.campusEnabled&&state.noticePublished&&!modal&&state.scene!=='notice'" class="campus-shortcuts"><button class="small" data-action="open-history" @click="openCampus('history')">校史馆</button><button class="small" data-action="open-forum" @click="openCampus('forum')">校园论坛</button></div>
<CampusPanel v-if="modal==='campus'" :award-id="award.id" :key="state.sessionId" :session-id="state.sessionId" :school="state.noticeContext?.school||school" :player="state.noticeContext?.player||player" :initial-tab="campusTab" :result-publication="state.resultPublication" @close="resume" />
<PauseMenu v-if="modal==='pause'" :award-name="award.name" :chapter="title?'标题画面':state.scene==='coupleEnd'?'情侣答辩已结束':state.scene==='meetingEnd'?'第一幕 · 会议结束':(state.scene==='review'?'第二幕 · 审阅':state.scene==='defense'?'第三幕 · 答辩':chapters[0])" :player="player" :school="school" @resume="resume" @settings="settings" @fullscreen="fullscreen" @restart="modal='restart'" @title="returnTitle" />
<div v-else-if="modal&&modal!=='campus'" class="overlay-back modal-layer" role="dialog" aria-modal="true" :aria-label="modal==='settings'?'名称设置':'重新开始'">
<form v-if="modal==='settings'" class="confirm-box" @submit.prevent="saveSettings"><h2>名称设置</h2><p>修改称呼，不改变当前评选进度。校名留空时显示“本校”。</p><label>玩家称呼<input id="player-name" v-model="draft.playerName" maxlength="16"></label><label>学校名称<input id="school-name" v-model="draft.schoolName" maxlength="24" placeholder="本校"></label><div class="actions"><button type="button" data-action="cancel-restart" @click="closeSubmenu">取消</button><button class="primary" data-action="save-settings" type="submit">保存设置</button></div></form>
<div v-else class="confirm-box"><h2>重新开始本次评选？</h2><p>“{{ award.name }}”的进度与名称设置将清除，其他奖项存档不受影响。</p><div class="actions"><button data-action="cancel-restart" @click="closeSubmenu">取消</button><button class="primary" data-action="reset" @click="reset">清除并重新开始</button></div></div></div>
</div></main></div></template>
<style scoped>
.campus-shortcuts{position:absolute;top:20px;right:28px;display:flex;gap:12px;z-index:25}.campus-shortcuts button{background:#eeeae1e8}
</style>
