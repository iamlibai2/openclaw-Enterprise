<template>
  <div class="page-container">
    <el-card class="page-header">
      <h1>运行状态</h1>
      <p>Gateway 运行状态和系统资源监控</p>
    </el-card>

    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon running">
            <el-icon size="32"><CircleCheck /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">Gateway</div>
            <div class="stat-value">{{ gatewayStatus }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon sessions">
            <el-icon size="32"><ChatDotRound /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">活跃会话</div>
            <div class="stat-value">{{ activeSessions }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon uptime">
            <el-icon size="32"><Timer /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">运行时长</div>
            <div class="stat-value">{{ uptime }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon version">
            <el-icon size="32"><InfoFilled /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">版本</div>
            <div class="stat-value">v1.0.0</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="detail-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="系统信息" name="system">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="主机名">{{ systemInfo.hostname }}</el-descriptions-item>
            <el-descriptions-item label="操作系统">{{ systemInfo.os }}</el-descriptions-item>
            <el-descriptions-item label="Node 版本">{{ systemInfo.nodeVersion }}</el-descriptions-item>
            <el-descriptions-item label="启动时间">{{ systemInfo.startTime }}</el-descriptions-item>
            <el-descriptions-item label="内存使用">{{ systemInfo.memory }}</el-descriptions-item>
            <el-descriptions-item label="CPU 使用">{{ systemInfo.cpu }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
        <el-tab-pane label="连接状态" name="connections">
          <el-table :data="connections" stripe>
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'connected' ? 'success' : 'info'">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { CircleCheck, ChatDotRound, Timer, InfoFilled } from '@element-plus/icons-vue'

const gatewayStatus = ref('运行中')
const activeSessions = ref(0)
const uptime = ref('0h 0m')
const activeTab = ref('system')

const systemInfo = ref({
  hostname: 'LAPTOP-80G5G0ES',
  os: 'Linux WSL2',
  nodeVersion: 'v22.22.1',
  startTime: '2026-03-30 16:00:00',
  memory: '256MB / 8GB',
  cpu: '12%'
})

const connections = ref([
  { type: 'Node', name: 'iPhone 15 Pro', status: 'connected' },
  { type: 'Channel', name: 'Telegram', status: 'connected' },
  { type: 'Channel', name: 'Discord', status: 'disconnected' },
])

onMounted(async () => {
  // 获取真实数据
  try {
    const res = await fetch('/api/gateway/status')
    const data = await res.json()
    if (data.status === 'ok') {
      activeSessions.value = data.activeSessions || 0
      uptime.value = data.uptime || '0h 0m'
    }
  } catch {
    // 使用默认值
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

.page-header h1 {
  font-size: 24px;
  margin-bottom: 8px;
}

.page-header p {
  color: #909399;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
}

.stat-icon.running {
  background: #e8f5e9;
  color: #67c23a;
}

.stat-icon.sessions {
  background: #e3f2fd;
  color: #409eff;
}

.stat-icon.uptime {
  background: #fff3e0;
  color: #e6a23c;
}

.stat-icon.version {
  background: #f3e5f5;
  color: #909399;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.detail-card {
  margin-top: 20px;
}
</style>