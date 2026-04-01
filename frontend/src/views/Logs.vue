<template>
  <div class="page-container">
    <el-card class="page-header">
      <h1>日志查看</h1>
      <p>系统运行日志和错误记录</p>
    </el-card>

    <el-card class="content-card">
      <div class="log-controls">
        <el-select v-model="logLevel" placeholder="日志级别" style="width: 120px">
          <el-option label="全部" value="all" />
          <el-option label="INFO" value="info" />
          <el-option label="WARN" value="warn" />
          <el-option label="ERROR" value="error" />
        </el-select>
        <el-button type="primary" @click="refreshLogs">刷新</el-button>
        <el-button @click="downloadLogs">下载日志</el-button>
      </div>

      <div class="log-container">
        <div v-for="(log, index) in logs" :key="index" class="log-line" :class="log.level">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-level">[{{ log.level.toUpperCase() }}]</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const logLevel = ref('all')
const logs = ref([
  { time: '16:40:26', level: 'error', message: 'Exec failed: python: command not found' },
  { time: '16:35:12', level: 'info', message: 'Gateway started successfully' },
  { time: '16:35:10', level: 'info', message: 'Loading configuration from ~/.openclaw/config.yaml' },
  { time: '16:35:08', level: 'warn', message: 'No Discord channel configured' },
  { time: '16:35:00', level: 'info', message: 'OpenClaw Gateway initializing...' },
])

const refreshLogs = async () => {
  ElMessage.success('日志已刷新')
}

const downloadLogs = () => {
  ElMessage.success('日志下载已开始')
}
</script>

<style scoped>
.page-container {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 24px;
  margin-bottom: 8px;
}

.page-header p {
  color: #909399;
}

.content-card {
  min-height: 500px;
}

.log-controls {
  margin-bottom: 16px;
  display: flex;
  gap: 8px;
}

.log-container {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 16px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
  max-height: 400px;
  overflow-y: auto;
}

.log-line {
  padding: 4px 0;
  color: #d4d4d4;
}

.log-line.error {
  color: #f56c6c;
}

.log-line.warn {
  color: #e6a23c;
}

.log-line.info {
  color: #67c23a;
}

.log-time {
  color: #909399;
  margin-right: 12px;
}

.log-level {
  margin-right: 8px;
  font-weight: 600;
}

.log-message {
  color: #d4d4d4;
}
</style>