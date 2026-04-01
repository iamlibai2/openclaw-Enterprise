<template>
  <div class="config-page">
    <div class="page-header">
      <h1>系统配置</h1>
      <el-button type="primary" @click="loadConfig" :loading="loading">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

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
        <el-collapse-item title="模型配置" name="models">
          <pre class="config-json">{{ modelsConfig }}</pre>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { configApi } from '../api'

const loading = ref(false)
const fullConfig = ref<any>({})
const activeCollapse = ref(['gateway'])

const gatewayConfig = computed(() => JSON.stringify(fullConfig.value.gateway || {}, null, 2))
const agentsConfig = computed(() => JSON.stringify(fullConfig.value.agents || {}, null, 2))
const bindingsConfig = computed(() => JSON.stringify(fullConfig.value.bindings || [], null, 2))
const modelsConfig = computed(() => JSON.stringify(fullConfig.value.models || {}, null, 2))

async function loadConfig() {
  loading.value = true
  try {
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
  margin-bottom: 20px;
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
