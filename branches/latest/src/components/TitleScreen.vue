<script setup>
defineProps({ award:Object });
defineEmits(['start','select-award']);
</script>
<template>
  <section class="title-screen" aria-label="标题画面">
    <h1 class="title-logo">优秀情侣奖</h1>
    <p class="award-picker">{{ award.description }}</p>
    <button class="title-start" data-action="start-game" @click="$emit('start')">开始游戏</button>
    <p class="save-hint">进度自动保存 · 继续本次评选</p>
  </section>
</template>
<style scoped>
.title-logo{top:130px}.award-picker{position:absolute;top:400px;width:1140px;border:0;padding:0;display:flex;gap:28px}.award-picker legend{width:100%;text-align:center;font-size:24px;letter-spacing:6px;margin-bottom:28px}.award-option{width:50%;padding:28px 32px;text-align:left;display:flex;flex-direction:column;gap:14px;min-height:168px;letter-spacing:2px}.award-option strong{font-size:30px;font-weight:400}.award-option span{font-size:18px;line-height:1.7;letter-spacing:1px}.award-option.selected{border:2px solid var(--red);box-shadow:inset 0 5px var(--red)}.title-start{top:770px}.save-hint{position:absolute;top:900px;font-size:18px;color:#68615b;letter-spacing:2px}
</style>
