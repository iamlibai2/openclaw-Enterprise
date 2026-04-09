<template>
  <div class="model-providers-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <h1>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
          </svg>
          模型提供商配置
        </h1>
        <p class="header-desc">管理外部模型服务商的 API 配置</p>
      </div>
      <button class="add-btn" @click="showAddDialog">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        添加提供商
      </button>
    </div>

    <!-- Provider 列表 -->
    <div class="providers-grid">
      <el-card
        v-for="provider in providers"
        :key="provider.id"
        class="provider-card"
        :class="{ disabled: !provider.enabled }"
        :body-style="{ padding: 0 }"
      >
        <div class="card-header">
          <div class="provider-info">
            <h3>{{ provider.display_name }}</h3>
            <span class="provider-name">{{ provider.name }}</span>
          </div>
          <div class="provider-status">
            <label class="switch">
              <input type="checkbox" v-model="provider.enabled" @change="toggleProvider(provider)">
              <span class="slider"></span>
            </label>
          </div>
        </div>

        <div class="card-body">
          <div class="info-row">
            <span class="label">API 类型</span>
            <span class="value">{{ provider.api_type }}</span>
          </div>
          <div class="info-row">
            <span class="label">Base URL</span>
            <span class="value truncate">{{ provider.base_url }}</span>
          </div>
          <div class="info-row">
            <span class="label">API Key</span>
            <span class="value env-var">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>
              </svg>
              {{ provider.api_key_env }}
            </span>
          </div>
          <div class="info-row">
            <span class="label">模型数量</span>
            <span class="value">{{ getModelCount(provider) }}</span>
          </div>
        </div>

        <div class="card-actions">
          <button class="action-btn" @click="editProvider(provider)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            编辑
          </button>
          <button class="action-btn danger" @click="deleteProvider(provider)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
            删除
          </button>
        </div>
      </el-card>

      <!-- 空状态 -->
      <div v-if="providers.length === 0" class="empty-state">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
        </svg>
        <p>暂无模型提供商配置</p>
        <button class="add-btn" @click="showAddDialog">添加第一个提供商</button>
      </div>
    </div>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingProvider ? '编辑提供商' : '添加提供商'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="form" ref="formRef" label-width="140px">
        <el-form-item label="提供商名称" required>
          <el-input v-model="form.name" placeholder="例如: volcengine" />
        </el-form-item>

        <el-form-item label="显示名称" required>
          <el-input v-model="form.display_name" placeholder="例如: 火山引擎" />
        </el-form-item>

        <el-form-item label="API 类型">
          <el-select v-model="form.api_type" style="width: 100%">
            <el-option value="image-generation" label="图片生成" />
            <el-option value="text-generation" label="文本生成" />
            <el-option value="speech-synthesis" label="语音合成" />
            <el-option value="other" label="其他" />
          </el-select>
        </el-form-item>

        <el-form-item label="Base URL" required>
          <el-input v-model="form.base_url" placeholder="例如: https://ark.cn-beijing.volces.com/api/v3" />
        </el-form-item>

        <el-form-item label="API Key 环境变量" required>
          <el-input v-model="form.api_key_env" placeholder="例如: VOLCENGINE_API_KEY" />
        </el-form-item>

        <el-form-item label="模型配置 (JSON)">
          <el-input
            v-model="form.config_json"
            type="textarea"
            :rows="6"
            placeholder='{"models": [{"id": "model-id", "name": "模型名称"}]}'
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveProvider">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
import { validateFields } from '../utils/rules'

const providers = ref<any[]>([])
const dialogVisible = ref(false)
const editingProvider = ref<any>(null)
const formRef = ref()

const form = ref({
  name: '',
  display_name: '',
  api_type: 'image-generation',
  base_url: '',
  api_key_env: '',
  config_json: '',
  enabled: true
})

// 表单校验 - 使用统一规则
const validateForm = () => {
  const result = validateFields(
    {
      providerName: form.value.name,
      displayName: form.value.display_name,
      baseUrl: form.value.base_url,
      apiKeyEnv: form.value.api_key_env
    },
    ['providerName', 'baseUrl', 'apiKeyEnv']
  )

  if (!result.valid) {
    const firstError = Object.values(result.errors)[0]
    ElMessage.warning(firstError)
    return false
  }

  // 显示名称校验
  if (!form.value.display_name) {
    ElMessage.warning('请输入显示名称')
    return false
  }

  // JSON 配置校验
  if (form.value.config_json && form.value.config_json.trim()) {
    try {
      JSON.parse(form.value.config_json)
    } catch {
      ElMessage.warning('模型配置 JSON 格式不正确')
      return false
    }
  }

  return true
}

async function loadProviders() {
  try {
    const res = await api.get('/model-providers')
    if (res.data.success) {
      providers.value = res.data.data
    }
  } catch (err) {
    ElMessage.error('加载失败')
  }
}

function showAddDialog() {
  editingProvider.value = null
  form.value = {
    name: '',
    display_name: '',
    api_type: 'image-generation',
    base_url: '',
    api_key_env: '',
    config_json: '',
    enabled: true
  }
  dialogVisible.value = true
}

function editProvider(provider: any) {
  editingProvider.value = provider
  form.value = {
    name: provider.name,
    display_name: provider.display_name,
    api_type: provider.api_type,
    base_url: provider.base_url,
    api_key_env: provider.api_key_env,
    config_json: provider.config_json || '',
    enabled: provider.enabled
  }
  dialogVisible.value = true
}

async function saveProvider() {
  // 表单校验
  if (!validateForm()) {
    return
  }

  try {
    if (editingProvider.value) {
      // 更新
      await api.put(`/model-providers/${editingProvider.value.id}`, form.value)
      ElMessage.success('更新成功')
    } else {
      // 新增
      await api.post('/model-providers', form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    loadProviders()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '操作失败')
  }
}

async function toggleProvider(provider: any) {
  try {
    await api.patch(`/model-providers/${provider.id}`, { enabled: provider.enabled })
    ElMessage.success(provider.enabled ? '已启用' : '已禁用')
  } catch (err) {
    provider.enabled = !provider.enabled
    ElMessage.error('操作失败')
  }
}

async function deleteProvider(provider: any) {
  try {
    await ElMessageBox.confirm(`确定删除 ${provider.display_name} 吗？`, '确认删除', {
      type: 'warning'
    })
    await api.delete(`/model-providers/${provider.id}`)
    ElMessage.success('删除成功')
    loadProviders()
  } catch (err) {
    // 用户取消
  }
}

function getModelCount(provider: any) {
  try {
    const config = JSON.parse(provider.config_json || '{}')
    return config.models?.length || 0
  } catch {
    return 0
  }
}

onMounted(() => {
  loadProviders()
})
</script>

<style scoped>
.model-providers-page {
  padding: 32px;
  max-width: 1400px;
  margin: 0 auto;
}

/* 页面标题 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.header-content h1 {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px;
}

.header-content h1 svg {
  color: #6366f1;
}

.header-desc {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.add-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.add-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(99, 102, 241, 0.3);
}

/* Provider 网格 */
.providers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 24px;
}

.provider-card {
  border-radius: 16px !important;
  border: 1px solid #e5e7eb !important;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: none !important;
}

.provider-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0,0,0,0.08) !important;
}

.provider-card.disabled {
  opacity: 0.6;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: linear-gradient(135deg, #f9fafb, #f3f4f6);
  border-bottom: 1px solid #e5e7eb;
}

.provider-info h3 {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
}

.provider-name {
  font-size: 12px;
  color: #9ca3af;
  font-family: monospace;
}

/* 开关 */
.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background-color: #d1d5db;
  transition: 0.3s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

input:checked + .slider {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
}

input:checked + .slider:before {
  transform: translateX(20px);
}

.card-body {
  padding: 20px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-row .label {
  font-size: 13px;
  color: #6b7280;
}

.info-row .value {
  font-size: 13px;
  color: #1f2937;
  font-weight: 500;
}

.value.truncate {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.value.env-var {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.1);
  padding: 4px 10px;
  border-radius: 6px;
}

.card-actions {
  display: flex;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid #f3f4f6;
  background: #fafafa;
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  border-color: #6366f1;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.05);
}

.action-btn.danger:hover {
  border-color: #ef4444;
  color: #ef4444;
  background: rgba(239, 68, 68, 0.05);
}

/* 空状态 */
.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
  color: #9ca3af;
}

.empty-state svg {
  color: #d1d5db;
  margin-bottom: 16px;
}

.empty-state p {
  font-size: 16px;
  margin: 0 0 20px;
}
</style>