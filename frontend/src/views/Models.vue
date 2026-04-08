<template>
  <div class="page-container">
    <el-card class="page-header">
      <div class="header-content">
        <div>
          <h1>模型管理</h1>
          <p>配置和管理 AI 模型，支持 API Key 加密存储</p>
        </div>
        <el-button type="primary" @click="showCreateDialog" v-if="permissions.can_edit" :disabled="gatewayRestarting">
          <el-icon><Plus /></el-icon>
          添加模型
        </el-button>
      </div>
    </el-card>

    <!-- Gateway 重启提示 -->
    <el-alert
      v-if="gatewayRestarting"
      title="Gateway 正在重启生效，正在等待恢复..."
      type="warning"
      :closable="false"
      show-icon
      class="restart-alert"
    >
      <template #default>
        <span>配置已保存，系统正在自动等待 Gateway 恢复并刷新数据...</span>
      </template>
    </el-alert>

    <!-- 提供商筛选 -->
    <el-card class="filter-card">
      <div class="filter-content">
        <span class="filter-label">提供商筛选：</span>
        <el-radio-group v-model="selectedProvider" @change="filterModels">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button
            v-for="provider in providers"
            :key="provider.id"
            :label="provider.id"
          >
            {{ provider.name }}
          </el-radio-button>
        </el-radio-group>
      </div>
    </el-card>

    <!-- 模型列表 -->
    <el-card class="content-card">
      <el-table :data="filteredModels" stripe v-loading="loading || gatewayRestarting">
        <el-table-column prop="name" label="名称" width="180">
          <template #default="{ row }">
            <div class="model-name">
              {{ row.name }}
              <el-tag v-if="!row.enabled" type="info" size="small">已禁用</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="provider" label="提供商" width="120">
          <template #default="{ row }">
            {{ getProviderName(row.provider) }}
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="模型" width="150" />
        <el-table-column prop="api_key_masked" label="API Key" width="80">
          <template #default="{ row }">
            <span class="api-key-hidden" v-if="row.has_api_key">已隐藏</span>
            <span class="api-key-none" v-else>未配置</span>
          </template>
        </el-table-column>
        <el-table-column prop="api_base" label="API 地址" min-width="200">
          <template #default="{ row }">
            <el-tooltip :content="row.api_base" placement="top">
              <span class="api-base">{{ truncateUrl(row.api_base) }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              @click="showEditDialog(row)"
              :disabled="gatewayRestarting"
              v-if="permissions.can_edit"
            >
              编辑
            </el-button>
            <el-button
              link
              type="success"
              @click="showCloneDialog(row)"
              :disabled="gatewayRestarting"
              v-if="permissions.can_edit"
            >
              克隆
            </el-button>
            <el-button
              link
              type="danger"
              @click="deleteModel(row)"
              :disabled="gatewayRestarting"
              v-if="permissions.can_delete"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑模型' : isClone ? '克隆模型' : '添加模型'"
      width="600px"
      destroy-on-close
    >
      <div class="clone-hint" v-if="isClone">
        <el-icon><InfoFilled /></el-icon>
        <span>基于现有模型创建新配置，可修改提供商和模型名称</span>
      </div>
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="提供商" prop="provider">
          <el-select
            v-model="formData.provider"
            placeholder="选择提供商"
            @change="onProviderChange"
            :disabled="isEdit"
          >
            <el-option
              v-for="provider in providers"
              :key="provider.id"
              :label="provider.name"
              :value="provider.id"
            >
              <div class="provider-option">
                <span>{{ provider.name }}</span>
                <span class="provider-desc">{{ provider.description }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="模型名称" prop="model_name">
          <el-select
            v-model="formData.model_name"
            placeholder="选择模型"
            :disabled="isEdit"
            filterable
            allow-create
          >
            <el-option
              v-for="model in currentProviderModels"
              :key="model"
              :label="model"
              :value="model"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="显示名称" prop="name">
          <el-input v-model="formData.name" placeholder="输入显示名称" />
        </el-form-item>

        <el-form-item label="API Key" prop="api_key">
          <el-input
            v-model="formData.api_key"
            type="password"
            placeholder="输入 API Key"
            show-password
          />
          <div class="form-tip" v-if="isEdit && currentModel?.has_api_key">
            当前已配置（留空保持不变）
          </div>
        </el-form-item>

        <el-form-item label="API 地址">
          <el-input v-model="formData.api_base" placeholder="使用默认地址或自定义" />
          <div class="form-tip" v-if="currentProviderTemplate">
            默认：{{ currentProviderTemplate.api_base }}
          </div>
        </el-form-item>

        <el-form-item label="参数配置">
          <div class="params-config">
            <div class="param-item">
              <span class="param-label">Temperature:</span>
              <el-slider
                v-model="formData.parameters.temperature"
                :min="0"
                :max="1"
                :step="0.1"
                show-input
                :show-input-controls="false"
              />
            </div>
            <div class="param-item">
              <span class="param-label">Max Tokens:</span>
              <el-input-number
                v-model="formData.parameters.max_tokens"
                :min="1"
                :max="128000"
                :step="1000"
              />
            </div>
            <div class="param-item">
              <span class="param-label">Context Window:</span>
              <el-input-number
                v-model="formData.parameters.context_window"
                :min="1000"
                :max="200000"
                :step="1000"
              />
            </div>
          </div>
        </el-form-item>

        <el-form-item label="状态">
          <el-switch v-model="formData.enabled" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { Plus, InfoFilled } from '@element-plus/icons-vue'
import { modelApi, type ModelProvider, type ModelConfig } from '../api'
import { createFormRules, sanitizeData } from '../utils/rules'

// 使用统一校验规则
const formRules = createFormRules({
  name: 'modelDisplayName',
  provider: 'providerName',
  model_name: 'modelName'
})

// 状态
const loading = ref(false)
const submitting = ref(false)
const models = ref<ModelConfig[]>([])
const providers = ref<ModelProvider[]>([])
const selectedProvider = ref('')
const permissions = ref({ can_read: true, can_edit: true, can_delete: true })
const gatewayRestarting = ref(false) // Gateway 重启等待状态

// 对话框
const dialogVisible = ref(false)
const isEdit = ref(false)
const isClone = ref(false) // 区分克隆场景
const currentModel = ref<ModelConfig | null>(null)

// 表单
const formRef = ref<FormInstance>()
const formData = reactive({
  name: '',
  provider: '',
  model_name: '',
  api_key: '',
  api_base: '',
  model_type: 'chat',
  parameters: {
    temperature: 0.7,
    max_tokens: 4096,
    context_window: 16000
  },
  enabled: true
})

// 计算属性
const currentProviderTemplate = computed(() => {
  return providers.value.find(p => p.id === formData.provider)
})

const currentProviderModels = computed(() => {
  return currentProviderTemplate.value?.models || []
})

const filteredModels = computed(() => {
  if (!selectedProvider.value) {
    return models.value
  }
  return models.value.filter(m => m.provider === selectedProvider.value)
})

// 方法
const loadProviders = async () => {
  try {
    const res = await modelApi.getProviders()
    if (res.data.success) {
      providers.value = res.data.data
    }
  } catch (error) {
    console.error('加载提供商失败:', error)
  }
}

const loadModels = async () => {
  loading.value = true
  try {
    const res = await modelApi.list()
    if (res.data.success) {
      models.value = res.data.data
    }
  } catch (error) {
    console.error('加载模型失败:', error)
    ElMessage.error('加载模型失败')
  } finally {
    loading.value = false
  }
}

const filterModels = () => {
  // 筛选由 computed 处理
}

const getProviderName = (providerId: string) => {
  const provider = providers.value.find(p => p.id === providerId)
  return provider?.name || providerId
}

const truncateUrl = (url: string) => {
  if (!url) return ''
  if (url.length <= 40) return url
  return url.substring(0, 40) + '...'
}

const resetForm = () => {
  formData.name = ''
  formData.provider = ''
  formData.model_name = ''
  formData.api_key = ''
  formData.api_base = ''
  formData.model_type = 'chat'
  formData.parameters = { temperature: 0.7, max_tokens: 4096, context_window: 16000 }
  formData.enabled = true
  currentModel.value = null
  isClone.value = false
}

const showCreateDialog = () => {
  resetForm()
  isEdit.value = false
  isClone.value = false
  dialogVisible.value = true
}

const showCloneDialog = (model: ModelConfig) => {
  resetForm()
  isEdit.value = false // 克隆是创建新模型，不是编辑
  isClone.value = true
  currentModel.value = null

  // 复制所有配置，但允许修改关键字段
  formData.name = model.name + ' (副本)'
  formData.provider = model.provider
  formData.model_name = model.model_name
  formData.api_key = '' // API Key 需要重新输入（敏感信息不复制）
  formData.api_base = model.api_base
  formData.model_type = model.model_type
  formData.parameters = { ...model.parameters }
  formData.enabled = true // 新模型默认启用

  dialogVisible.value = true
}

const showEditDialog = (model: ModelConfig) => {
  resetForm()
  isEdit.value = true
  currentModel.value = model

  formData.name = model.name
  formData.provider = model.provider
  formData.model_name = model.model_name
  formData.api_key = '' // 清空，用户可以输入新的
  formData.api_base = model.api_base
  formData.model_type = model.model_type
  formData.parameters = { ...model.parameters }
  formData.enabled = model.enabled

  dialogVisible.value = true
}

const onProviderChange = (providerId: string) => {
  // 重置模型选择
  formData.model_name = ''
  // 填充默认 API Base
  const template = currentProviderTemplate.value
  if (template) {
    formData.api_base = template.api_base
  }
}

// Gateway 重启等待
const waitForGatewayRestart = async () => {
  gatewayRestarting.value = true
  ElMessage({
    message: '配置已保存，Gateway 正在重启生效...',
    type: 'success',
    duration: 3000
  })

  // 轮询等待 Gateway 恢复（最多等待 30 秒）
  const maxAttempts = 15
  let attempts = 0

  while (attempts < maxAttempts) {
    try {
      await new Promise(resolve => setTimeout(resolve, 2000)) // 等待 2 秒
      attempts++

      // 尝试加载模型列表
      const res = await modelApi.list()
      if (res.data.success) {
        models.value = res.data.data
        gatewayRestarting.value = false
        ElMessage.success('Gateway 已恢复，数据已刷新')
        return
      }
    } catch (e) {
      // Gateway 还未恢复，继续等待
      console.log(`等待 Gateway 恢复... (${attempts}/${maxAttempts})`)
    }
  }

  // 超时
  gatewayRestarting.value = false
  ElMessage.warning('Gateway 恢复超时，请手动刷新页面')
}

const submitForm = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      // 统一清理输入
      const cleanData = sanitizeData({
        name: formData.name,
        provider: formData.provider,
        model_name: formData.model_name,
        api_key: formData.api_key,
        api_base: formData.api_base,
        model_type: formData.model_type,
        parameters: formData.parameters,
        enabled: formData.enabled
      })

      if (isEdit.value && currentModel.value) {
        // 更新
        const updateData: any = {
          name: cleanData.name,
          api_base: cleanData.api_base,
          parameters: cleanData.parameters,
          enabled: cleanData.enabled
        }
        if (cleanData.api_key) {
          updateData.api_key = cleanData.api_key
        }

        const res = await modelApi.update(currentModel.value.id, updateData)
        if (res.data.success) {
          dialogVisible.value = false
          waitForGatewayRestart()
        }
      } else {
        // 创建
        const res = await modelApi.create(cleanData)
        if (res.data.success) {
          dialogVisible.value = false
          waitForGatewayRestart()
        }
      }
    } catch (error: any) {
      ElMessage.error(error.response?.data?.error || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

const deleteModel = async (model: ModelConfig) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除模型 "${model.name}" 吗？`,
      '删除确认',
      { type: 'warning' }
    )

    const res = await modelApi.delete(model.id)
    if (res.data.success) {
      waitForGatewayRestart()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.error || '删除失败')
    }
  }
}

// 生命周期
onMounted(() => {
  loadProviders()
  loadModels()
})
</script>

<style scoped>
.page-container {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h1 {
  font-size: 24px;
  margin-bottom: 8px;
}

.page-header p {
  color: #909399;
}

.restart-alert {
  margin-bottom: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-label {
  color: #606266;
  font-weight: 500;
}

.content-card {
  min-height: 500px;
}

.model-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.api-key-hidden {
  font-family: monospace;
  color: #909399;
  font-style: italic;
}

.api-key-none {
  color: #c0c4cc;
}

.api-base {
  color: #606266;
  font-size: 13px;
}

.provider-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.provider-desc {
  font-size: 12px;
  color: #909399;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.params-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.param-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.param-label {
  min-width: 100px;
  color: #606266;
}

.param-item .el-slider {
  flex: 1;
}

.clone-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #e6f7ff;
  border-radius: 8px;
  margin-bottom: 16px;
  color: #1890ff;
  font-size: 14px;
}
</style>