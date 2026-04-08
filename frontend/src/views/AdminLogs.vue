<template>
  <div class="admin-logs-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>Admin UI 日志</h1>
      <div class="header-actions">
        <el-select v-model="logType" style="width: 120px" @change="onTypeChange">
          <el-option label="全部日志" value="app" />
          <el-option label="错误日志" value="error" />
        </el-select>
        <el-select v-model="levelFilter" style="width: 120px" clearable placeholder="级别过滤" @change="onFilterChange">
          <el-option label="ERROR+" value="ERROR" />
          <el-option label="WARN+" value="WARNING" />
          <el-option label="INFO+" value="INFO" />
          <el-option label="DEBUG" value="DEBUG" />
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
      <span class="info-item" v-if="fileSize">
        大小: {{ formatSize(fileSize) }}
      </span>
      <span class="info-item" v-if="logs.length">
        行数: {{ logs.length }}
      </span>
      <el-tag v-if="!fileExists" type="warning" size="small">文件不存在</el-tag>
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
          <span class="log-time">{{ line.timestamp }}</span>
          <span class="log-logger" v-if="line.logger">[{{ line.logger }}]</span>
          <span class="log-message">{{ line.message }}</span>
          <el-button
            v-if="line.exception"
            size="small"
            text
            class="exception-btn"
            @click="showException(line)"
          >
            <el-icon><Warning /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 空状态 -->
      <div class="empty-state" v-if="!loading && logs.length === 0">
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

    <!-- 异常详情弹窗 -->
    <el-dialog v-model="exceptionDialogVisible" title="异常详情" width="600px">
      <div class="exception-detail">
        <p><strong>类型:</strong> {{ currentException?.type }}</p>
        <p><strong>消息:</strong> {{ currentException?.message }}</p>
        <div class="traceback">
          <strong>堆栈追踪:</strong>
          <pre>{{ currentException?.traceback?.join('\n') }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Document, Bottom, Delete, Warning } from '@element-plus/icons-vue'
import api from '../api'

interface LogEntry {
  timestamp: string
  level: string
  logger: string
  message: string
  module?: string
  function?: string
  line?: number
  exception?: {
    type: string
    message: string
    traceback: string[]
  }
}

const loading = ref(false)
const logs = ref<string[]>([])
const logType = ref('app')
const levelFilter = ref('')
const autoRefresh = ref(false)
const autoScroll = ref(true)
const logFile = ref('')
const fileSize = ref(0)
const fileExists = ref(true)
const logContainer = ref<HTMLElement | null>(null)

const exceptionDialogVisible = ref(false)
const currentException = ref<any>(null)

let refreshTimer: ReturnType<typeof setInterval> | null = null

const parsedLines = computed(() => {
  return logs.value.map(line => {
    try {
      const obj = JSON.parse(line)
      return {
        timestamp: obj.timestamp ? obj.timestamp.replace('T', ' ').replace('Z', '').substring(0, 19) : '',
        level: (obj.level || 'INFO').toUpperCase(),
        logger: obj.logger || '',
        message: obj.message || '',
        module: obj.module,
        function: obj.function,
        line: obj.line,
        exception: obj.exception
      }
    } catch {
      return {
        timestamp: '',
        level: 'INFO',
        logger: '',
        message: line
      }
    }
  })
})

async function loadLogs() {
  loading.value = true
  try {
    const params: any = {
      type: logType.value,
      limit: 500
    }
    if (levelFilter.value) {
      params.level = levelFilter.value
    }

    const res = await api.get('/admin-logs', { params })
    if (res.data.success) {
      logs.value = res.data.data.lines || []
      logFile.value = res.data.data.file || ''
      fileSize.value = res.data.data.size || 0
      fileExists.value = res.data.data.exists

      // 自动滚动到底部
      if (autoScroll.value && logs.value.length > 0) {
        scrollToBottom()
      }
    }
  } catch (e: any) {
    ElMessage.error('加载失败：' + e.message)
  } finally {
    loading.value = false
  }
}

function onTypeChange() {
  loadLogs()
}

function onFilterChange() {
  loadLogs()
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value

  if (autoRefresh.value) {
    refreshTimer = setInterval(loadLogs, 5000)
    ElMessage.success('已开启自动刷新（每 5 秒）')
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
  logs.value = []
}

function getLevelClass(level: string): string {
  const levelMap: Record<string, string> = {
    'DEBUG': 'debug',
    'INFO': 'info',
    'WARNING': 'warning',
    'WARN': 'warning',
    'ERROR': 'error',
    'CRITICAL': 'critical'
  }
  return levelMap[level] || 'info'
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function showException(log: LogEntry) {
  currentException.value = log.exception
  exceptionDialogVisible.value = true
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
.admin-logs-page {
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

.log-level.critical {
  background: #c53030;
  color: #fff;
}

.log-time {
  color: #68d391;
  min-width: 160px;
  flex-shrink: 0;
}

.log-logger {
  color: #b794f4;
  flex-shrink: 0;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.log-message {
  color: #e2e8f0;
  flex: 1;
  word-break: break-word;
}

.exception-btn {
  color: #f56565;
  flex-shrink: 0;
  padding: 0 4px;
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

.exception-detail {
  font-size: 14px;
}

.exception-detail p {
  margin-bottom: 12px;
}

.traceback {
  margin-top: 16px;
}

.traceback pre {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  overflow-x: auto;
  max-height: 300px;
  white-space: pre-wrap;
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