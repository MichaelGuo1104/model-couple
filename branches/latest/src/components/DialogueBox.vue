<script setup>
defineProps({ speaker: String, text: String });
</script>
<template><div class="dialogue"><div class="speaker">{{ speaker }}</div><p class="speech">{{ text }}</p><div class="actions"><slot /></div></div></template>
