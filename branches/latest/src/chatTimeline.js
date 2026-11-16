export const CHAT_START_SECONDS=8*3600+50;
export const MEETING_DELAY_MS=(12*3600-CHAT_START_SECONDS)*1000;
export function chatTime(elapsedMs){const seconds=CHAT_START_SECONDS+Math.floor(Math.max(0,elapsedMs)/1000);return `${String(Math.floor(seconds/3600)%24).padStart(2,'0')}:${String(Math.floor(seconds/60)%60).padStart(2,'0')}`;}
// Five independent uniform offsets measured from the principal's notice, not from one another.
export function replySchedule(random=Math.random){return ['zhao','qian','sun','li','zhou'].map((id,index)=>({id,at:2000+random()*2000,index})).sort((a,b)=>a.at-b.at||a.index-b.index);}
