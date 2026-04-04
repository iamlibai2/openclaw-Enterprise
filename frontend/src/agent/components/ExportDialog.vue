<template>
  <el-dialog
    v-model="visible"
    title="导出 Agent"
    width="400px"
    :close-on-click-modal="false"
  >
    <div class="export-dialog" v-if="agent">
      <div class="export-info">
        <span class="export-label">Agent:</span>
        <span class="export-name">{{ agent.name }}</span>
      </div>

      <el-divider>导出选项</el-divider>

      <div class="export-options">
        <el-checkbox v-model="includeMemory">包含记忆文件</el-checkbox>
        <el-checkbox v-model="includeHistory">包含对话历史</el-checkbox>
      </div>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-top: 16px"
      >
        <template #title>
          导出为 .openclaw-agent 文件，可用于备份或分享
        </template>
      </el-alert>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleExport" :loading="exporting">
        导出
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { AgentProfile } from '../types'
import { exportAgent } from '../api'

const props = defineProps<{
  visible: boolean
  agent?: AgentProfile | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const visible = ref(props.visible)
const exporting = ref(false)
const includeMemory = ref(false)
const includeHistory = ref(false)

watch(() => props.visible, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:visible', val)
})

async function handleExport() {
  if (!props.agent) return

  exporting.value = true
  try {
    const blob = await exportAgent(props.agent.id, {
      includeMemory: includeMemory.value,
      includeHistory: includeHistory.value
    })

    if (blob) {
      // 创建下载链接
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${props.agent.name}_${new Date().toISOString().slice(0, 10)}.openclaw-agent`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      ElMessage.success('导出成功')
      visible.value = false
    } else {
      ElMessage.error('导出失败')
    }
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped>
.export-dialog {
  padding: 0 10px;
}

.export-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.export-label {
  font-size: 13px;
  color: #999;
}

.export-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.export-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>