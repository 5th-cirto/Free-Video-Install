<script setup>
const props = defineProps({
  visible: { type: Boolean, default: false },
  svg: { type: String, default: '' },
})

const emit = defineEmits(['update:visible', 'close'])

function onClose() {
  emit('update:visible', false)
  emit('close')
}
</script>

<template>
  <el-dialog :model-value="visible" fullscreen destroy-on-close @close="onClose">
    <template #header>
      <div class="dialog-header">
        <strong>思维导图全屏预览</strong>
        <el-button @click="onClose">关闭</el-button>
      </div>
    </template>
    <div class="preview-wrap" v-html="svg"></div>
  </el-dialog>
</template>

<style scoped>
.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.preview-wrap {
  width: 100%;
  min-height: 70vh;
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  overflow: auto;
}
</style>
