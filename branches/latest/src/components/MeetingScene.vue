<script setup>
import { computed } from 'vue';
import { people,image } from '../content.js';
import DialogueBox from './DialogueBox.vue';
const props=defineProps({line:Number,player:String,award:Object});defineEmits(['next']);
const entry=computed(()=>props.award.meetings[props.line]);
const speaker=computed(()=>people[entry.value[0]]);
const other=computed(()=>people[entry.value[0]==='guo'?'zhao':'guo']);
</script>
<template><img :src="image('meeting_room')" class="meeting-bg" alt="308会议室" draggable="false"><div class="scene-tag">第一幕　／　12:00　／　308会议室</div><img :src="image(other.whole)" class="cast left" :alt="other.name" draggable="false"><img :src="image(speaker.whole)" class="speaker-cast" :alt="speaker.name" draggable="false"><aside class="side-note"><span class="eyebrow">议题 01</span><br>关于开展<br>“{{ award.name }}”<br>试点评选</aside><DialogueBox :speaker="speaker.name" :text="entry[1].replaceAll('吴主任',player)"><button class="primary" data-action="next-line" @click="$emit('next')">{{ line===award.meetings.length-1?award.meetingEndLabel:'继续 →' }}</button></DialogueBox></template>
