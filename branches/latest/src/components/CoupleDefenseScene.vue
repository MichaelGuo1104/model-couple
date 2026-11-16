<script setup>
import { computed } from 'vue';
const props=defineProps({ candidate:Object, step:Number, ended:Boolean });
defineEmits(['next','title']);
const line=computed(()=>props.candidate?.speech[props.step]);
</script>

<template>
  <section class="couple-defense" :aria-label="ended?'情侣答辩结束':'情侣答辩发言'">
    <div class="eyebrow">2025年5月10日 周六 ／ 优秀情侣奖</div>
    <h1>{{ candidate.name }}</h1>
    <template v-if="!ended && line">
      <p class="progress">答辩发言 {{ step+1 }} / {{ candidate.speech.length }}</p>
      <article :key="step" aria-live="polite"><h2>{{ line.speaker }}</h2><p>{{ line.text }}</p></article>
      <button class="primary" data-action="next-couple-speech" @click="$emit('next')">{{ step===candidate.speech.length-1?'结束答辩':'下一条发言 →' }}</button>
    </template>
    <template v-else>
      <h2 data-status="couple-defense-ended">情侣答辩已结束</h2>
      <p>本局入围情侣的发言已全部完成，进度已保存。</p>
      <p>本阶段到此为止，不进行自由提问、评分、获奖决定或颁奖。</p>
      <button class="primary" data-action="back-title" @click="$emit('title')">返回标题</button>
    </template>
  </section>
</template>

<style scoped>
.couple-defense{position:absolute;inset:0;background:var(--paper);padding:100px 180px;display:flex;flex-direction:column;align-items:flex-start;gap:24px}h1{font-size:42px;margin:0}h2{font-size:32px;margin:0}p{font-size:28px;line-height:1.9;margin:0}.progress{font-size:22px}article{width:100%;flex:1;border-top:1px solid var(--ink);padding:40px 20px;overflow:auto}article p{margin-top:26px;white-space:pre-wrap}button{align-self:flex-end}
</style>
