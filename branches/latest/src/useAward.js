import { reactive, ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { coupleCandidates } from './coupleCandidates.js';
import { getAward } from './awards.js';
const KEY='excellent-couple-v2';
const fresh=()=>({awardId:'couple',sessionId:globalThis.crypto?.randomUUID?.()||`session-${Date.now()}`,scene:'chat',line:0,noticePublished:false,noticeContext:null,selected:[],defenseIndex:0,defenseStep:0,profile:{playerName:'吴主任',schoolName:''}});
function load(){try{const x=JSON.parse(localStorage.getItem(KEY));if(!x||!getAward().scenes.includes(x.scene))return fresh();const s={...fresh(),...x,awardId:'couple'};s.selected=coupleCandidates.filter(c=>Array.isArray(x.selected)&&x.selected.includes(c.id)).map(c=>c.id);s.defenseIndex=Math.max(0,Math.min(s.selected.length-1,Number(x.defenseIndex)||0));const c=coupleCandidates.find(c=>c.id===s.selected[s.defenseIndex]);s.defenseStep=Math.max(0,Math.min((c?.speech.length||1)-1,Number(x.defenseStep)||0));s.line=Math.max(0,Math.min(getAward().meetings.length-1,Number(x.line)||0));return s;}catch{return fresh();}}
export function useAward(){
 const state=reactive(load()),title=ref(true),modal=ref(''),scale=ref(1),draft=reactive({playerName:'',schoolName:''});
 const award=computed(()=>getAward()),paused=computed(()=>Boolean(modal.value));
 const candidates=coupleCandidates;
 const player=computed(()=>state.profile.playerName||'吴主任'),school=computed(()=>state.profile.schoolName||'本校');
 const current=computed(()=>candidates.find(c=>c.id===state.selected[state.defenseIndex]));
 function go(scene){if(award.value.scenes.includes(scene)){state.scene=scene;modal.value='';}}
 function startGame(){title.value=false;}
 function returnTitle(){title.value=true;modal.value='';}
 function receive(){state.line=0;go('meeting');}
 function advance(){if(state.scene!=='meeting')return;if(state.line<award.value.meetings.length-1)state.line++;else go('notice');}
 function publishNotice(){if(state.scene==='notice'&&!state.noticePublished){state.noticeContext={school:school.value,player:player.value};state.noticePublished=true;}}
 function collectForms(){if(state.scene==='notice'&&state.noticePublished)go('review');}
 function toggleCouple(id){if(state.scene==='review'&&candidates.some(c=>c.id===id))state.selected=state.selected.includes(id)?state.selected.filter(x=>x!==id):[...state.selected,id];}
 function startDefense(){if(state.scene==='review'&&state.selected.length){state.defenseIndex=0;state.defenseStep=0;go('defense');}}
 function advanceCouple(){if(state.scene!=='defense'||!current.value)return;if(state.defenseStep<current.value.speech.length-1)state.defenseStep++;else if(state.defenseIndex<state.selected.length-1){state.defenseIndex++;state.defenseStep=0;}else go('coupleEnd');}
 function resume(){modal.value='';}
 function closeSubmenu(){modal.value='pause';}
 function settings(){Object.assign(draft,state.profile);modal.value='settings';}
 function saveSettings(){state.profile={playerName:draft.playerName.trim().slice(0,16)||'吴主任',schoolName:draft.schoolName.trim().slice(0,24)};modal.value='pause';}
 function reset(){Object.assign(state,fresh());modal.value='';title.value=true;}
 function keydown(e){if(e.key==='Escape'){e.preventDefault();if(modal.value==='pause')resume();else if(modal.value)closeSubmenu();else modal.value='pause';}}
 function resize(){scale.value=Math.min(innerWidth/1920,innerHeight/1080);}
 async function fullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{}}
 watch(state,()=>{try{localStorage.setItem(KEY,JSON.stringify(state));}catch{}},{deep:true,flush:'sync'});
 onMounted(()=>{resize();window.addEventListener('resize',resize);window.addEventListener('keydown',keydown);});
 onUnmounted(()=>{window.removeEventListener('resize',resize);window.removeEventListener('keydown',keydown);});
 return {state,title,modal,scale,draft,award,paused,candidates,player,school,current,go,startGame,returnTitle,receive,advance,publishNotice,collectForms,toggleCouple,startDefense,advanceCouple,resume,closeSubmenu,settings,saveSettings,reset,fullscreen};
}
