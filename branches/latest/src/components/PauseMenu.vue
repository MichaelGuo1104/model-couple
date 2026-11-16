<script setup>
defineProps({ chapter:String, player:String, school:String, awardName:String });
defineEmits(['resume','settings','fullscreen','restart','title']);
</script>
<template>
  <div class="overlay-back pause-overlay" role="dialog" aria-modal="true" aria-label="暂停设置">
    <section class="pause-menu">
      <div class="logo"><em>颁</em>什么<em>奖</em></div>
      <h2>暂停</h2>
      <p class="pause-context">{{ chapter }}<br>{{ school }} · 奖励执行委员会<br>{{ player }}　／　2026年度 · {{ awardName }}</p>
      <nav class="pause-actions" aria-label="暂停菜单">
        <button data-action="resume" autofocus @click="$emit('resume')">继续游戏</button>
        <button data-action="settings" @click="$emit('settings')">名称设置</button>
        <button data-action="fullscreen" @click="$emit('fullscreen')">全屏切换</button>
        <button data-action="restart" @click="$emit('restart')">重新开始</button>
        <button data-action="return-title" @click="$emit('title')">返回标题画面</button>
      </nav>
      <p class="pause-hint">Esc 返回　／　进度自动保存在本机</p>
    </section>
  </div>
</template>
