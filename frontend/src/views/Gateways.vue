<template>
  <div class="gateways-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <h1>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
            <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
            <line x1="6" y1="6" x2="6.01" y2="6"/>
            <line x1="6" y1="18" x2="6.01" y2="18"/>
          </svg>
          Gateway 管理
        </h1>
        <p class="header-desc">管理 OpenClaw Gateway 连接配置</p>
      </div>
      <button class="add-btn" @click="showCreateDialog">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        添加 Gateway
      </button>
    </div>

    <!-- Gateway 卡片列表 -->
    <div class="gateways-grid">
      <el-card
        v-for="gateway in gateways"
        :key="gateway.id"
        class="gateway-card"
        :class="{
          'is-current': currentGateway?.id === gateway.id,
          'is-offline': gateway.status === 'error'
        }"
        :body-style="{ padding: 0 }"
      >
        <!-- 当前使用标识 -->
        <div v-if="currentGateway?.id === gateway.id" class="current-badge">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          当前使用
        </div>

        <div class="card-header">
          <div class="gateway-info">
            <h3>{{ gateway.name }}</h3>
            <span class="gateway-status" :class="gateway.status">
              <span class="status-dot"></span>
              {{ getStatusText(gateway.status) }}
            </span>
          </div>
          <el-tag v-if="gateway.is_default" type="success" size="small">默认</el-tag>
        </div>

        <div class="card-body">
          <div class="info-row">
            <span class="label">WebSocket 地址</span>
            <span class="value truncate">{{ gateway.url }}</span>
          </div>
          <div class="info-row">
            <span class="label">最后连接</span>
            <span class="value">{{ gateway.last_connected_at || '从未连接' }}</span>
          </div>
          <div class="info-row" v-if="gateway.auth_token_masked">
            <span class="label">认证 Token</span>
            <span class="value token">{{ gateway.auth_token_masked }}</span>
          </div>
        </div>

        <div class="card-actions">
          <button
            v-if="currentGateway?.id !== gateway.id"
            class="action-btn primary"
            @click="switchGateway(gateway)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="17 1 21 5 17 9"/>
              <path d="M3 11V9a4 4 0 014-4h14"/>
              <polyline points="7 23 3 19 7 15"/>
              <path d="M21 13v2a4 4 0 01-4 4H3"/>
            </svg>
            切换
          </button>
          <span v-else class="current-tag">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            已激活
          </span>
          <button class="action-btn" @click="testConnection(gateway)" :disabled="gateway.testing">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            {{ gateway.testing ? '测试中...' : '测试' }}
          </button>
          <button class="action-btn" @click="showEditDialog(gateway)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            编辑
          </button>
          <button class="action-btn danger" @click="deleteGateway(gateway)" :disabled="gateways.length <= 1">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
            删除
          </button>
        </div>
      </el-card>

      <!-- 空状态 -->
      <div v-if="gateways.length === 0" class="empty-state">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
          <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
          <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
          <line x1="6" y1="6" x2="6.01" y2="6"/>
          <line x1="6" y1="18" x2="6.01" y2="18"/>
        </svg>
        <p>暂无 Gateway 配置</p>
        <button class="add-btn" @click="showCreateDialog">添加第一个 Gateway</button>
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingGateway ? '编辑 Gateway' : '添加 Gateway'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" label-width="120px">
        <el-form-item label="名称" required>
          <el-input v-model="formData.name" placeholder="例如：生产环境 Gateway" />
        </el-form-item>
        <el-form-item label="WebSocket 地址" required>
          <el-input v-model="formData.url" placeholder="ws://127.0.0.1:18789 或 wss://gateway.example.com" />
        </el-form-item>
        <el-form-item label="认证 Token">
          <el-input v-model="formData.auth_token" type="password" placeholder="可选，用于远程认证" show-password />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="formData.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveGateway" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { validateFields } from '../utils/rules'

interface Gateway {
  id: number
  name: string
  url: string
  auth_token?: string
  auth_token_masked?: string
  is_default: boolean
  status: string
  last_connected_at?: string
  testing?: boolean
}

const gateways = ref<Gateway[]>([])
const currentGateway = ref<Gateway | null>(null)
const dialogVisible = ref(false)
const editingGateway = ref<Gateway | null>(null)
const saving = ref(false)

// 状态轮询定时器
let statusTimer: ReturnType<typeof setInterval> | null = null
const STATUS_CHECK_INTERVAL = 60000 // 60秒检查一次

const formData = ref({
  name: '',
  url: '',
  auth_token: '',
  is_default: false
})

// 表单校验 - 使用统一规则
const validateForm = () => {
  const result = validateFields(
    { gatewayName: formData.value.name, gatewayUrl: formData.value.url },
    ['gatewayName', 'gatewayUrl']
  )

  if (!result.valid) {
    const firstError = Object.values(result.errors)[0]
    ElMessage.warning(firstError)
    return false
  }
  return true
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'online': return '在线'
    case 'error': return '离线'
    case 'unknown': return '未知'
    default: return status
  }
}

const fetchGateways = async () => {
  try {
    const res = await fetch('/api/gateways', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    })
    const data = await res.json()
    if (data.success) {
      gateways.value = data.data
    }
  } catch (e) {
    console.error('获取 Gateway 列表失败', e)
  }
}

const fetchCurrentGateway = async () => {
  try {
    const res = await fetch('/api/gateways/current', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    })
    const data = await res.json()
    if (data.success) {
      currentGateway.value = data.data
    }
  } catch (e) {
    console.error('获取当前 Gateway 失败', e)
  }
}

const showCreateDialog = () => {
  editingGateway.value = null
  formData.value = {
    name: '',
    url: '',
    auth_token: '',
    is_default: false
  }
  dialogVisible.value = true
}

const showEditDialog = (gateway: Gateway) => {
  editingGateway.value = gateway
  formData.value = {
    name: gateway.name,
    url: gateway.url,
    auth_token: '', // 编辑时不显示原 token
    is_default: gateway.is_default
  }
  dialogVisible.value = true
}

const saveGateway = async () => {
  // 表单校验
  if (!validateForm()) {
    return
  }

  saving.value = true
  try {
    const url = editingGateway.value
      ? `/api/gateways/${editingGateway.value.id}`
      : '/api/gateways'
    const method = editingGateway.value ? 'PUT' : 'POST'

    const body: Record<string, any> = {
      name: formData.value.name,
      url: formData.value.url,
      is_default: formData.value.is_default
    }

    // 只有填写了 token 才发送
    if (formData.value.auth_token) {
      body.auth_token = formData.value.auth_token
    }

    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      },
      body: JSON.stringify(body)
    })

    const data = await res.json()
    if (data.success) {
      ElMessage.success(data.message || '保存成功')
      dialogVisible.value = false
      fetchGateways()
      fetchCurrentGateway()
    } else {
      ElMessage.error(data.error || '保存失败')
    }
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const testConnection = async (gateway: Gateway) => {
  gateway.testing = true
  try {
    const res = await fetch(`/api/gateways/${gateway.id}/test`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    })
    const data = await res.json()
    if (data.success) {
      ElMessage.success(data.message || '连接成功')
      gateway.status = 'online'
      fetchGateways()
    } else {
      ElMessage.error(data.error || '连接失败')
      gateway.status = 'error'
    }
  } catch (e) {
    ElMessage.error('测试失败')
  } finally {
    gateway.testing = false
  }
}

const switchGateway = async (gateway: Gateway) => {
  try {
    const res = await fetch('/api/gateways/current', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      },
      body: JSON.stringify({ gateway_id: gateway.id })
    })
    const data = await res.json()
    if (data.success) {
      ElMessage.success(data.message || '切换成功')
      fetchGateways()
      fetchCurrentGateway()
    } else {
      ElMessage.error(data.error || '切换失败')
    }
  } catch (e) {
    ElMessage.error('切换失败')
  }
}

const deleteGateway = async (gateway: Gateway) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除 Gateway "${gateway.name}" 吗？`,
      '删除确认',
      { type: 'warning' }
    )

    const res = await fetch(`/api/gateways/${gateway.id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    })
    const data = await res.json()
    if (data.success) {
      ElMessage.success('删除成功')
      fetchGateways()
      fetchCurrentGateway()
    } else {
      ElMessage.error(data.error || '删除失败')
    }
  } catch (e) {
    // 用户取消
  }
}

onMounted(() => {
  fetchGateways()
  fetchCurrentGateway()

  // 启动状态轮询
  statusTimer = setInterval(() => {
    fetchCurrentGateway()
  }, STATUS_CHECK_INTERVAL)
})

onUnmounted(() => {
  // 清除定时器
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
})
</script>

<style scoped>
.gateways-page {
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

/* Gateway 网格 */
.gateways-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 24px;
}

/* Gateway 卡片 */
.gateway-card {
  border-radius: 16px !important;
  border: 1px solid #e5e7eb !important;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
  box-shadow: none !important;
  position: relative;
}

.gateway-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0,0,0,0.08) !important;
}

/* 当前使用的 Gateway 特殊样式 */
.gateway-card.is-current {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
}

.gateway-card.is-current:hover {
  box-shadow: 0 12px 24px rgba(99, 102, 241, 0.15), 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
}

/* 当前使用标识 */
.current-badge {
  position: absolute;
  top: 0;
  right: 0;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  padding: 6px 12px;
  border-radius: 0 16px 0 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 离线状态 */
.gateway-card.is-offline {
  opacity: 0.7;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: linear-gradient(135deg, #f9fafb, #f3f4f6);
  border-bottom: 1px solid #e5e7eb;
}

.gateway-info h3 {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
}

.gateway-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #6b7280;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #9ca3af;
}

.gateway-status.online {
  color: #10b981;
}

.gateway-status.online .status-dot {
  background: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
}

.gateway-status.error {
  color: #ef4444;
}

.gateway-status.error .status-dot {
  background: #ef4444;
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

.value.token {
  font-family: monospace;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.card-actions {
  display: flex;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid #f3f4f6;
  background: #fafafa;
  flex-wrap: wrap;
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
  min-width: 70px;
}

.action-btn:hover:not(:disabled) {
  border-color: #6366f1;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.05);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn.primary {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
  color: #fff;
}

.action-btn.primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.action-btn.danger:hover:not(:disabled) {
  border-color: #ef4444;
  color: #ef4444;
  background: rgba(239, 68, 68, 0.05);
}

.current-tag {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px;
  font-size: 13px;
  color: #10b981;
  font-weight: 500;
  background: rgba(16, 185, 129, 0.1);
  border-radius: 8px;
  min-width: 70px;
  flex: 1;
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