<template>
  <el-drawer
    v-model="visible"
    title="记忆管理"
    size="600px"
    :close-on-click-modal="false"
  >
    <div class="memory-manager" v-if="memory">
      <!-- 长期记忆 -->
      <div class="memory-section">
        <div class="section-header">
          <h3>📚 长期记忆</h3>
          <el-button text type="primary" @click="editLongTermMemory = true">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
        </div>
        <div class="memory-preview">
          <div class="memory-stats-row">
            <span>大小: {{ formatSize(memory.longTermMemorySize) }}</span>
            <span>更新: {{ formatDate(memory.lastUpdated) }}</span>
          </div>
          <div class="memory-content-preview">
            {{ memory.longTermMemory?.slice(0, 300) }}{{ memory.longTermMemory?.length > 300 ? '...' : '' }}
          </div>
        </div>
      </div>

      <!-- 日期记忆 -->
      <div class="memory-section">
        <div class="section-header">
          <h3>📅 日期记忆</h3>
          <span class="count-tag">{{ memory.dailyMemories?.length || 0 }} 天</span>
        </div>
        <div class="daily-memories">
          <div
            v-for="dm in memory.dailyMemories"
            :key="dm.date"
            class="daily-memory-item"
            @click="viewDailyMemory(dm)"
          >
            <span class="dm-date">{{ dm.date }}</span>
            <span class="dm-size">{{ formatSize(dm.size) }}</span>
            <el-icon class="dm-arrow"><ArrowRight /></el-icon>
          </div>
          <el-empty v-if="!memory.dailyMemories?.length" description="暂无日期记忆" :image-size="60" />
        </div>
      </div>

      <!-- 统计 -->
      <div class="memory-section">
        <h3>📊 记忆统计</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-value">{{ formatSize(memory.totalSize) }}</span>
            <span class="stat-label">总大小</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ memory.dailyMemories?.length || 0 }}</span>
            <span class="stat-label">记忆天数</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 长期记忆编辑器 -->
    <el-dialog
      v-model="editLongTermMemory"
      title="编辑长期记忆"
      width="700px"
      append-to-body
    >
      <el-input
        v-model="longTermContent"
        type="textarea"
        :rows="20"
        class="code-editor"
      />
      <template #footer>
        <el-button @click="editLongTermMemory = false">取消</el-button>
        <el-button type="primary" @click="saveLongTermMemory" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 日期记忆查看 -->
    <el-dialog
      v-model="viewDailyDialog"
      :title="selectedDailyMemory?.date"
      width="600px"
      append-to-body
    >
      <div class="daily-content">
        <pre>{{ dailyMemoryContent || '加载中...' }}</pre>
      </div>
    </el-dialog>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Edit, ArrowRight } from '@element-plus/icons-vue'
import type { MemoryConfig, DailyMemory } from '../types'
import { updateAgentMemory, getDailyMemory } from '../api'

const props = defineProps<{
  visible: boolean
  memory?: MemoryConfig
  agentId: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'saved': []
}>()

const visible = ref(props.visible)
const saving = ref(false)
const editLongTermMemory = ref(false)
const longTermContent = ref('')

const viewDailyDialog = ref(false)
const selectedDailyMemory = ref<DailyMemory | null>(null)
const dailyMemoryContent = ref('')

watch(() => props.visible, (val) => {
  visible.value = val
  if (val && props.memory) {
    longTermContent.value = props.memory.longTermMemory || ''
  }
})

watch(visible, (val) => {
  emit('update:visible', val)
})

async function saveLongTermMemory() {
  saving.value = true
  try {
    const success = await updateAgentMemory(props.agentId, longTermContent.value)
    if (success) {
      ElMessage.success('保存成功')
      emit('saved')
      editLongTermMemory.value = false
    } else {
      ElMessage.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}

async function viewDailyMemory(dm: DailyMemory) {
  selectedDailyMemory.value = dm
  viewDailyDialog.value = true
  dailyMemoryContent.value = ''

  const content = await getDailyMemory(props.agentId, dm.date)
  dailyMemoryContent.value = content || '无法加载'
}

function formatSize(bytes: number): string {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '未知'
  try {
    return new Date(dateStr).toLocaleDateString('zh-CN')
  } catch {
    return dateStr
  }
}
</script>

<style scoped>
.memory-manager {
  padding: 0 20px;
}

.memory-section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h3 {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.count-tag {
  font-size: 12px;
  color: #999;
  background: #f5f5f5;
  padding: 2px 8px;
  border-radius: 10px;
}

.memory-preview {
  background: #fafafa;
  border-radius: 8px;
  padding: 12px;
}

.memory-stats-row {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.memory-content-preview {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
  white-space: pre-wrap;
}

.daily-memories {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.daily-memory-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.daily-memory-item:hover {
  background: #f0f0f0;
}

.dm-date {
  flex: 1;
  font-size: 14px;
  color: #333;
}

.dm-size {
  font-size: 12px;
  color: #999;
  margin-right: 8px;
}

.dm-arrow {
  color: #ccc;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.stat-item {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: #999;
}

.code-editor :deep(textarea) {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
}

.daily-content pre {
  margin: 0;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>