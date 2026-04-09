<template>
  <div class="models-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>模型管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog" :disabled="isRestarting" v-if="permissions.can_edit">
          <el-icon><Plus /></el-icon>
          添加模型
        </el-button>
      </div>
    </div>

    <!-- 模型列表 -->
    <el-card class="table-card" v-loading="loading || isRestarting" element-loading-text="Gateway 正在重启，请稍候...">
      <el-table :data="paginatedModels" stripe>
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
              :disabled="isRestarting"
              v-if="permissions.can_edit"
            >
              编辑
            </el-button>
            <el-button
              link
              type="success"
              @click="showCloneDialog(row)"
              :disabled="isRestarting"
              v-if="permissions.can_edit"
            >
              克隆
            </el-button>
            <el-button
              link
              type="danger"
              @click="deleteModel(row)"
              :disabled="isRestarting"
              v-if="permissions.can_delete"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredModels.length"
          layout="total, sizes, prev, pager, next, jumper"
          background
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑模型' : isClone ? '克隆模型' : '添加模型'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="提供商" prop="provider">
          <el-select
            v-model="formData.provider"
            placeholder="选择提供商"
            @change="onProviderChange"
            :disabled="isEdit || isRestarting"
            style="width: 100%"
          >
            <el-option
              v-for="provider in providers"
              :key="provider.id"
              :label="provider.name"
              :value="provider.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="模型名称" prop="model_name">
          <el-input
            v-model="formData.model_name"
            placeholder="输入模型名称（如 glm-5）"
            :disabled="isEdit || isRestarting"
          />
          <div class="form-tip" v-if="!isEdit">
            模型名称是唯一标识，创建后不可修改
          </div>
        </el-form-item>

        <el-form-item label="显示名称" prop="name">
          <el-input v-model="formData.name" placeholder="输入显示名称" autocomplete="off" :disabled="isRestarting" />
        </el-form-item>

        <el-form-item label="API Key" prop="api_key">
          <el-input
            v-model="formData.api_key"
            type="password"
            placeholder="输入 API Key"
            show-password
            autocomplete="new-password"
            :disabled="isRestarting"
          />
        </el-form-item>

        <el-form-item label="API 地址">
          <el-input v-model="formData.api_base" placeholder="使用默认地址或自定义" :disabled="isRestarting" />
        </el-form-item>

        <el-form-item label="状态">
          <el-switch v-model="formData.enabled" active-text="启用" inactive-text="禁用" :disabled="isRestarting" />
        </el-form-item>
      </el-form>

      <template #footer>
        <!-- 编辑模式：单按钮"保存" -->
        <template v-if="isEdit">
          <el-button @click="dialogVisible = false" :disabled="isRestarting">取消</el-button>
          <el-button type="primary" @click="submitEdit" :loading="submitting" :disabled="isRestarting">
            保存
          </el-button>
        </template>
        <!-- 创建模式：单按钮"创建"，会自动重启 -->
        <template v-else>
          <el-button @click="dialogVisible = false" :disabled="isRestarting">取消</el-button>
          <el-button type="primary" @click="submitCreate" :loading="submitting">
            {{ isClone ? '克隆' : '创建' }}
          </el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { modelApi, type ModelProvider, type ModelConfig } from '../api'
import { createFormRules, sanitizeData } from '../utils/rules'

// 基础校验规则
const baseRules = createFormRules({
  name: 'modelDisplayName',
  provider: 'providerName',
  model_name: 'modelName'
})

// 动态校验规则 - 检查模型名称是否已存在
const formRules = computed<FormRules>(() => ({
  ...baseRules,
  model_name: [
    ...baseRules.model_name,
    {
      validator: (rule: any, value: string, callback: any) => {
        if (!value) {
          callback()
          return
        }
        // 编辑模式下不检查（原模型名已存在）
        if (isEdit.value && currentModel.value?.model_name === value) {
          callback()
          return
        }
        // 克隆和新建模式下检查是否已存在
        const exists = models.value.some(m => m.model_name === value)
        if (exists) {
          callback(new Error('模型名称已存在，请使用其他名称'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}))

// 状态
const loading = ref(false)
const submitting = ref(false)
const isRestarting = ref(false)  // Gateway 是否正在重启
const models = ref<ModelConfig[]>([])
const providers = ref<ModelProvider[]>([])
const selectedProvider = ref('')
const permissions = ref({ can_read: true, can_edit: true, can_delete: true })

// 分页
const currentPage = ref(1)
const pageSize = ref(10)

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

const filteredModels = computed(() => {
  if (!selectedProvider.value) {
    return models.value
  }
  return models.value.filter(m => m.provider === selectedProvider.value)
})

const paginatedModels = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredModels.value.slice(start, end)
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

  // 复制所有配置，但模型名称需要用户输入新的
  formData.name = model.name + ' (副本)'
  formData.provider = model.provider
  formData.model_name = ''  // 清空，让用户输入新的模型名称
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

const submitEdit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      const cleanData = sanitizeData({
        name: formData.name,
        api_key: formData.api_key,
        api_base: formData.api_base,
        parameters: formData.parameters,
        enabled: formData.enabled
      })

      const updateData: any = {
        name: cleanData.name,
        api_base: cleanData.api_base,
        parameters: cleanData.parameters,
        enabled: cleanData.enabled
      }
      if (cleanData.api_key) {
        updateData.api_key = cleanData.api_key
      }

      const res = await modelApi.update(currentModel.value!.id, updateData)
      if (res.data.success) {
        ElMessage.success('保存成功')
        dialogVisible.value = false
        loadModels()
      }
    } catch (error: any) {
      ElMessage.error(error.response?.data?.error || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

const submitCreate = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    // 先弹出确认框
    try {
      await ElMessageBox.confirm(
        '创建模型将会自动重启 Gateway，预计需要 10-30 秒。是否继续？',
        '创建确认',
        {
          type: 'warning',
          confirmButtonText: '确定创建',
          cancelButtonText: '取消'
        }
      )
    } catch {
      return // 用户取消
    }

    submitting.value = true
    isRestarting.value = true  // 开始重启，禁用界面
    const loadingMsg = ElMessage({
      message: '正在创建模型并重启 Gateway，请稍候...',
      type: 'info',
      duration: 0,
      showClose: false
    })

    try {
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

      const res = await modelApi.create(cleanData)
      loadingMsg.close()

      if (res.data.success) {
        ElMessage.success('创建成功')
        dialogVisible.value = false
        loadModels()
      } else {
        ElMessage.error(res.data.error || '创建失败')
      }
    } catch (error: any) {
      loadingMsg.close()
      ElMessage.error(error.response?.data?.error || '创建失败')
    } finally {
      submitting.value = false
      isRestarting.value = false  // 重启完成，恢复界面
    }
  })
}

const deleteModel = async (model: ModelConfig) => {
  try {
    await ElMessageBox.confirm(
      `删除模型 "${model.name}" 将会自动重启 Gateway，是否继续？`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    )

    isRestarting.value = true  // 开始重启，禁用界面
    const loadingMsg = ElMessage({
      message: '正在删除模型并重启 Gateway，请稍候...',
      type: 'info',
      duration: 0,
      showClose: false
    })

    const res = await modelApi.delete(model.id)
    loadingMsg.close()

    if (res.data.success) {
      ElMessage.success('删除成功')
      loadModels()
    } else {
      ElMessage.error(res.data.error || '删除失败')
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.error || '删除失败')
    }
  } finally {
    isRestarting.value = false  // 重启完成，恢复界面
  }
}

// 生命周期
onMounted(() => {
  loadProviders()
  loadModels()
})
</script>

<style scoped>
.models-page {
  max-width: 1200px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 24px;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.table-card {
  border-radius: 8px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
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
</style>