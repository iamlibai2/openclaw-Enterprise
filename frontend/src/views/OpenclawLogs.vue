<template>
  <div class="openclaw-logs-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>OpenClaw 日志</h1>
      <div class="header-actions">
        <el-select v-model="levelFilter" placeholder="日志级别" style="width: 120px" @change="onFilterChange" clearable>
          <el-option label="全部" value="" />
          <el-option label="ERROR" value="error" />
          <el-option label="WARN" value="warn" />
          <el-option label="INFO" value="info" />
          <el-option label="DEBUG" value="debug" />
        </el-select>
        <el-button @click="toggleAutoRefresh">
          <el-icon><Refresh /></el-icon>
          {{ autoRefresh ? '停止刷新' : '自动刷新' }}
        </el-button>
        <el-button type="primary" @click="loadLogs">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 日志文件信息 -->
    <div class="log-info" v-if="logFile">
      <span class="info-item">
        <el-icon><Document /></el-icon>
        {{ logFile }}
      </span>
      <span class="info-item" v-if="logSize">
        大小: {{ formatSize(logSize) }}
      </span>
      <span class="info-item" v-if="lines.length">
        行数: {{ lines.length }}
      </span>
      <el-tag v-if="truncated" type="warning" size="small">已截断</el-tag>
      <el-tag v-if="reset" type="info" size="small">已重置</el-tag>
    </div>

    <!-- 日志内容 -->
    <div class="log-container" ref="logContainer" v-loading="loading">
      <div class="log-lines">
        <div
          v-for="(line, index) in parsedLines"
          :key="index"
          class="log-line"
        >
          <span class="log-level" :class="getLevelClass(line.level)">{{ line.level }}</span>
          <span class="log-time">{{ line.time }}</span>
          <span class="log-subsystem" v-if="line.subsystem">[{{ line.subsystem }}]</span>
          <span class="log-message">{{ line.message }}</span>
        </div>
      </div>

      <!-- 空状态 -->
      <div class="empty-state" v-if="!loading && lines.length === 0">
        <el-icon :size="48"><Document /></el-icon>
        <p>暂无日志</p>
      </div>
    </div>

    <!-- 底部操作 -->
    <div class="log-footer">
      <el-button @click="scrollToBottom">
        <el-icon><Bottom /></el-icon>
        滚动到底部
      </el-button>
      <el-button @click="clearView">
        <el-icon><Delete /></el-icon>
        清空视图
      </el-button>
      <el-checkbox v-model="autoScroll" label="自动滚动" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Document, Bottom, Delete } from '@element-plus/icons-vue'
import { openclawLogsApi } from '../api'

interface ParsedLine {
  time: string
  level: string
  subsystem?: string
  message: string
  raw: string
}

const loading = ref(false)
const lines = ref<string[]>([])
const cursor = ref(0)
const logFile = ref('')
const logSize = ref(0)
const truncated = ref(false)
const reset = ref(false)
const levelFilter = ref('')
const autoRefresh = ref(false)
const autoScroll = ref(true)
const logContainer = ref<HTMLElement | null>(null)

let refreshTimer: ReturnType<typeof setInterval> | null = null

const parsedLines = computed(() => {
  return lines.value.map(line => {
    try {
      const obj = JSON.parse(line)
      return {
        time: obj.time || '',
        level: (obj.level || 'info').toUpperCase(),
        subsystem: obj.subsystem,
        message: obj.message || line,
        raw: line
      }
    } catch {
      return {
        time: '',
        level: 'INFO',
        subsystem: undefined,
        message: line,
        raw: line
      }
    }
  })
})

async function loadLogs() {
  loading.value = true
  try {
    const params: any = {
      limit: 1000,
      maxBytes: 500000
    }

    // 如果有 cursor 且没有重置，使用增量读取
    if (cursor.value > 0 && !reset.value) {
      params.cursor = cursor.value
    }

    if (levelFilter.value) {
      params.level = levelFilter.value
    }

    const res = await openclawLogsApi.tail(params)
    if (res.data.success) {
      const data = res.data.data

      // 如果重置或首次加载，替换所有行
      if (data.reset || cursor.value === 0) {
        lines.value = data.lines
      } else {
        // 增量追加
        lines.value = [...lines.value, ...data.lines]
      }

      cursor.value = data.cursor
      logFile.value = data.file
      logSize.value = data.size
      truncated.value = data.truncated
      reset.value = data.reset

      // 自动滚动到底部
      if (autoScroll.value && data.lines.length > 0) {
        scrollToBottom()
      }
    }
  } catch (e: any) {
    ElMessage.error('加载日志失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  cursor.value = 0
  reset.value = true
  lines.value = []
  loadLogs()
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value

  if (autoRefresh.value) {
    refreshTimer = setInterval(loadLogs, 3000)
    ElMessage.success('已开启自动刷新（每 3 秒）')
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
    ElMessage.info('已停止自动刷新')
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

function clearView() {
  lines.value = []
  cursor.value = 0
  reset.value = true
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function getLevelClass(level: string): string {
  const levelMap: Record<string, string> = {
    'DEBUG': 'debug',
    'INFO': 'info',
    'WARNING': 'warning',
    'WARN': 'warning',
    'ERROR': 'error',
    'FATAL': 'error'
  }
  return levelMap[level] || 'info'
}

onMounted(() => {
  loadLogs()
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.openclaw-logs-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h1 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.log-info {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #606266;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.log-container {
  flex: 1;
  background: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.log-lines {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.log-line {
  display: flex;
  gap: 12px;
  padding: 4px 0;
  color: #d4d4d4;
  border-bottom: 1px solid #333;
}

.log-line:hover {
  background: #252525;
}

.log-level {
  min-width: 70px;
  padding: 2px 8px;
  border-radius: 3px;
  font-weight: bold;
  font-size: 12px;
  text-align: center;
}

.log-level.debug {
  background: #4a5568;
  color: #a0aec0;
}

.log-level.info {
  background: #3182ce;
  color: #fff;
}

.log-level.warning {
  background: #d69e2e;
  color: #fff;
}

.log-level.error {
  background: #e53e3e;
  color: #fff;
}

.log-time {
  color: #68d391;
  min-width: 140px;
  flex-shrink: 0;
}

.log-subsystem {
  color: #b794f4;
  flex-shrink: 0;
}

.log-message {
  color: #e2e8f0;
  flex: 1;
  word-break: break-word;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #6b7280;
}

.empty-state p {
  margin-top: 12px;
}

.log-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 0;
}

/* 滚动条样式 */
.log-lines::-webkit-scrollbar {
  width: 8px;
}

.log-lines::-webkit-scrollbar-track {
  background: #2d2d2d;
}

.log-lines::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}

.log-lines::-webkit-scrollbar-thumb:hover {
  background: #666;
}
</style>