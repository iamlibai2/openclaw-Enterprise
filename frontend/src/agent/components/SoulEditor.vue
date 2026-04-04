<template>
  <el-dialog
    v-model="visible"
    title="编辑灵魂"
    width="700px"
    :close-on-click-modal="false"
  >
    <div class="soul-editor">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      >
        <template #title>
          灵魂文件定义了 Agent 的核心价值观、行为准则和个性特征
        </template>
      </el-alert>

      <el-input
        v-model="content"
        type="textarea"
        :rows="20"
        placeholder="编辑 SOUL.md 内容..."
        class="code-editor"
      />

      <div class="editor-footer">
        <span class="char-count">{{ content.length }} 字符</span>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { SoulConfig } from '../types'
import { updateAgentSoul } from '../api'

const props = defineProps<{
  visible: boolean
  soul?: SoulConfig
  agentId: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'saved': []
}>()

const visible = ref(props.visible)
const saving = ref(false)
const content = ref('')

// 同步
watch(() => props.visible, (val) => {
  visible.value = val
  if (val && props.soul) {
    content.value = props.soul.content || ''
  }
})

watch(visible, (val) => {
  emit('update:visible', val)
})

async function handleSave() {
  saving.value = true
  try {
    const success = await updateAgentSoul(props.agentId, content.value)
    if (success) {
      ElMessage.success('保存成功')
      emit('saved')
      visible.value = false
    } else {
      ElMessage.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.soul-editor {
  display: flex;
  flex-direction: column;
}

.code-editor :deep(textarea) {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.editor-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.char-count {
  font-size: 12px;
  color: #999;
}
</style>