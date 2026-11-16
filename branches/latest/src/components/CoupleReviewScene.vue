<script setup>
defineProps({ candidates: Array, selected: Array });
defineEmits(['toggle', 'submit']);
</script>

<template>
  <section class="couple-review" aria-label="情侣报名材料审阅">
    <header><div class="eyebrow">2025年5月5日 周一 ／ 报名审阅</div><h1>优秀情侣奖 · 双人报名</h1>
      <p>共收到{{ candidates.length }}对完整报名。是否入围由玩家决定，不沿用源包的入围事件，不由委员会干预。</p>
      <p>材料仅用于游戏内核阅；公开授权“未授权”不等于不同意参与，不可当作宣传许可。未提供的信息保持“待补充”。</p></header>
    <div class="applications">
      <article v-for="candidate in candidates" :key="candidate.id" :data-couple="candidate.id">
        <h2>{{ candidate.name }}</h2><p>提交日期：{{ candidate.submittedAt }} ／ 游戏内已提交</p><p>{{ candidate.notice }}</p><p v-if="candidate.revision" class="revision">{{ candidate.revision }}</p>
        <div class="applicants"><section v-for="page in candidate.pages" :key="page.studentId">
          <h3>{{ page.fields['姓名'] }}</h3>
          <dl><template v-for="(value, field) in page.fields" :key="field"><dt>{{ field }}</dt><dd>{{ value }}</dd></template></dl>
          <h4>个人陈述</h4><p>{{ page.statement }}</p>
          <p>参与确认：{{ page.participation }}</p><p>公开授权：{{ page.publicity }}</p><p>提交状态：{{ page.status }}</p>
        </section></div>
        <button :data-action="'toggle-'+candidate.id" :aria-pressed="selected.includes(candidate.id)" @click="$emit('toggle',candidate.id)">{{ selected.includes(candidate.id)?'取消入围':'由玩家列入入围名单' }}</button>
      </article>
    </div>
    <footer><span>拟入围：{{ selected.length }}对</span><button class="primary" data-action="start-defense" :disabled="!selected.length" @click="$emit('submit')">确认本局入围名单，进入5月10日答辩 →</button></footer>
  </section>
</template>

<style scoped>
.couple-review{position:absolute;inset:0;padding:38px 90px;background:var(--paper);display:flex;flex-direction:column;gap:16px}h1{font-size:34px;margin:12px 0}header p{font-size:20px;margin:8px 0}.applications{flex:1;overflow:auto;padding:0 20px 20px 0}article{border:1px solid var(--ink);padding:24px}h2{font-size:30px;margin:0}article>p{font-size:18px}.applicants{display:grid;grid-template-columns:1fr 1fr;gap:32px}.applicants section{padding:20px;background:#fff9}.applicants p{font-size:20px;line-height:1.8}dl{display:grid;grid-template-columns:110px 1fr;gap:10px;font-size:19px;line-height:1.7}dd{margin:0;white-space:pre-wrap}dt{font-weight:bold}footer{display:flex;justify-content:space-between;align-items:center;font-size:24px}
</style>
