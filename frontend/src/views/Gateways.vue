<template>
  <div class="page-container">
    <el-card class="page-header">
      <div class="header-content">
        <div>
          <h1>Gateway 管理</h1>
          <p>管理 OpenClaw Gateway 连接配置，支持多 Gateway 切换</p>
        </div>
        <el-button type="primary" @click="showCreateDialog" :icon="Plus">
          添加 Gateway
        </el-button>
      </div>
    </el-card>

    <!-- 当前 Gateway -->
    <el-card class="current-gateway" v-if="currentGateway">
      <template #header>
        <div class="card-header">
          <span>当前使用</span>
          <el-tag :type="getStatusType(currentGateway.status)">
            {{ getStatusText(currentGateway.status) }}
          </el-tag>
        </div>
      </template>
      <div class="gateway-info">
        <div class="info-item">
          <span class="label">名称：</span>
          <span class="value">{{ currentGateway.name }}</span>
        </div>
        <div class="info-item">
          <span class="label">地址：</span>
          <span class="value">{{ currentGateway.url }}</span>
        </div>
        <div class="info-item">
          <span class="label">最后连接：</span>
          <span class="value">{{ currentGateway.last_connected_at || '未连接' }}</span>
        </div>
      </div>
    </el-card>

    <!-- Gateway 列表 -->
    <el-card>
      <el-table :data="gateways" stripe>
        <el-table-column prop="name" label="名称" width="180">
          <template #default="{ row }">
            <div class="gateway-name">
              {{ row.name }}
              <el-tag v-if="row.is_default" type="success" size="small">默认</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="url" label="WebSocket 地址" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_connected_at" label="最后连接" width="180">
          <template #default="{ row }">
            {{ row.last_connected_at || '从未连接' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button size="small" @click="testConnection(row)" :loading="row.testing">
              测试连接
            </el-button>
            <el-button size="small" @click="switchGateway(row)" v-if="!row.is_default">
              切换
            </el-button>
            <el-button size="small" @click="showEditDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteGateway(row)"
                       :disabled="gateways.length <= 1">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingGateway ? '编辑 Gateway' : '添加 Gateway'" width="500px">
      <el-form :model="formData" label-width="100px">
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
import { Plus } from '@element-plus/icons-vue'

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

const getStatusType = (status: string) => {
  switch (status) {
    case 'online': return 'success'
    case 'error': return 'danger'
    case 'unknown': return 'info'
    default: return 'info'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'online': return '在线'
    case 'error': return '错误'
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
  if (!formData.value.name || !formData.value.url) {
    ElMessage.error('请填写名称和地址')
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

.current-gateway {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.gateway-info {
  display: flex;
  gap: 40px;
}

.info-item {
  display: flex;
  align-items: center;
}

.info-item .label {
  color: #909399;
  margin-right: 8px;
}

.info-item .value {
  font-weight: 500;
}

.gateway-name {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>