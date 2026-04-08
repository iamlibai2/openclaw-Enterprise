<template>
  <div class="config-page">
    <div class="page-header">
      <h1>系统配置</h1>
      <div class="header-actions">
        <el-button @click="checkConfig" :loading="checking">
          <el-icon><CircleCheck /></el-icon>
          检查配置
        </el-button>
        <el-button type="primary" @click="loadConfig" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 配置检查结果 -->
    <el-card v-if="checkResult" class="check-card">
      <div class="check-header">
        <div class="check-score">
          <el-progress
            type="circle"
            :percentage="checkResult.score"
            :status="checkResult.score === 100 ? 'success' : checkResult.score >= 60 ? 'warning' : 'exception'"
            :width="80"
          />
          <span class="score-label">配置完整性</span>
        </div>
        <div class="check-summary">
          <div class="summary-item success">
            <el-icon><SuccessFilled /></el-icon>
            {{ checkResult.checks.length }} 项正常
          </div>
          <div class="summary-item warning" v-if="checkResult.warnings.length">
            <el-icon><WarningFilled /></el-icon>
            {{ checkResult.warnings.length }} 项警告
          </div>
          <div class="summary-item error" v-if="checkResult.errors.length">
            <el-icon><CircleCloseFilled /></el-icon>
            {{ checkResult.errors.length }} 项错误
          </div>
        </div>
      </div>

      <!-- 正常项 -->
      <div v-if="checkResult.checks.length" class="check-section">
        <h4>正常项</h4>
        <div class="check-items">
          <div v-for="item in checkResult.checks" :key="item.field" class="check-item success">
            <el-icon><SuccessFilled /></el-icon>
            <span>{{ item.message }}</span>
          </div>
        </div>
      </div>

      <!-- 警告项 -->
      <div v-if="checkResult.warnings.length" class="check-section">
        <h4>警告</h4>
        <div class="check-items">
          <div v-for="item in checkResult.warnings" :key="item.field" class="check-item warning">
            <el-icon><WarningFilled /></el-icon>
            <span>{{ item.message }}</span>
          </div>
        </div>
      </div>

      <!-- 错误项 -->
      <div v-if="checkResult.errors.length" class="check-section">
        <h4>错误</h4>
        <div class="check-items">
          <div v-for="item in checkResult.errors" :key="item.field" class="check-item error">
            <el-icon><CircleCloseFilled /></el-icon>
            <span>{{ item.message }}</span>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 配置预览 -->
    <el-card class="preview-card">
      <template #header>
        <div class="preview-header">
          <span>配置预览 (openclaw.json)</span>
          <el-button size="small" @click="copyConfig">
            <el-icon><CopyDocument /></el-icon>
            复制
          </el-button>
        </div>
      </template>
      <div class="config-preview">
        <pre ref="configPreviewRef">{{ configJson }}</pre>
      </div>
    </el-card>

    <!-- 详细配置折叠 -->
    <el-card class="config-card">
      <el-collapse v-model="activeCollapse">
        <el-collapse-item title="Gateway 配置" name="gateway">
          <pre class="config-json">{{ gatewayConfig }}</pre>
        </el-collapse-item>
        <el-collapse-item title="Agent 列表" name="agents">
          <pre class="config-json">{{ agentsConfig }}</pre>
        </el-collapse-item>
        <el-collapse-item title="绑定配置" name="bindings">
          <pre class="config-json">{{ bindingsConfig }}</pre>
        </el-collapse-item>
        <el-collapse-item title="系统用模型配置" name="models">
          <pre class="config-json">{{ modelsConfig }}</pre>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Refresh, CircleCheck, CopyDocument,
  SuccessFilled, WarningFilled, CircleCloseFilled
} from '@element-plus/icons-vue'
import { configApi } from '../api'

const loading = ref(false)
const checking = ref(false)
const fullConfig = ref<any>({})
const configJson = ref('')
const checkResult = ref<any>(null)
const activeCollapse = ref(['gateway'])
const configPreviewRef = ref<HTMLElement>()

const gatewayConfig = computed(() => JSON.stringify(fullConfig.value.gateway || {}, null, 2))
const agentsConfig = computed(() => JSON.stringify(fullConfig.value.agents || {}, null, 2))
const bindingsConfig = computed(() => JSON.stringify(fullConfig.value.bindings || [], null, 2))
const modelsConfig = computed(() => JSON.stringify(fullConfig.value.models || {}, null, 2))

async function loadConfig() {
  loading.value = true
  try {
    // 加载配置预览
    const previewRes = await fetch('/api/config/preview', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    })
    const previewData = await previewRes.json()
    if (previewData.success) {
      configJson.value = previewData.data.json
    }

    // 加载详细配置
    const res = await configApi.get()
    if (res.data.success) {
      fullConfig.value = res.data.data
    } else {
      ElMessage.error(res.data.error)
    }
  } catch (e: any) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function checkConfig() {
  checking.value = true
  try {
    const res = await fetch('/api/config/check', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    })
    const data = await res.json()
    if (data.success) {
      checkResult.value = data.data
    }
  } catch (e: any) {
    ElMessage.error('检查失败')
  } finally {
    checking.value = false
  }
}

function copyConfig() {
  if (configJson.value) {
    navigator.clipboard.writeText(configJson.value)
    ElMessage.success('已复制到剪贴板')
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.config-page {
  max-width: 1200px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.check-card {
  margin-bottom: 20px;
}

.check-header {
  display: flex;
  align-items: center;
  gap: 40px;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

.check-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.score-label {
  font-size: 13px;
  color: #606266;
}

.check-summary {
  display: flex;
  gap: 24px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
}

.summary-item.success {
  color: #67c23a;
}

.summary-item.warning {
  color: #e6a23c;
}

.summary-item.error {
  color: #f56c6c;
}

.check-section {
  margin-bottom: 16px;
}

.check-section h4 {
  font-size: 14px;
  margin-bottom: 8px;
  color: #606266;
}

.check-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 13px;
}

.check-item.success {
  background: #f0f9eb;
  color: #67c23a;
}

.check-item.warning {
  background: #fdf6ec;
  color: #e6a23c;
}

.check-item.error {
  background: #fef0f0;
  color: #f56c6c;
}

.preview-card {
  margin-bottom: 20px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-preview {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 16px;
  overflow: auto;
  max-height: 400px;
}

.config-preview pre {
  margin: 0;
  color: #d4d4d4;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.config-card {
  border-radius: 8px;
}

.config-json {
  background: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  overflow-x: auto;
  white-space: pre-wrap;
}
</style>