<template>
  <div class="page-container">
    <el-card class="page-header">
      <div class="header-content">
        <div>
          <h1>任务管理</h1>
          <p>查看和管理 Agent 工作任务</p>
        </div>
      </div>
    </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.total || 0 }}</div>
          <div class="stat-label">总任务数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.today || 0 }}</div>
          <div class="stat-label">今日任务</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value success">{{ stats.by_status?.completed || 0 }}</div>
          <div class="stat-label">已完成</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ formatDuration(stats.avg_duration_seconds) }}</div>
          <div class="stat-label">平均耗时</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选区 -->
    <el-card class="filter-card">
      <el-form inline>
        <el-form-item label="Agent">
          <el-select v-model="filters.agent_id" placeholder="全部" clearable style="width: 150px">
            <el-option v-for="agent in agents" :key="agent.id" :label="agent.id" :value="agent.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="待处理" value="pending" />
            <el-option label="进行中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="filters.task_type" placeholder="全部" clearable style="width: 150px">
            <el-option label="对话" value="chat" />
            <el-option label="文档处理" value="document" />
            <el-option label="代码生成" value="code" />
            <el-option label="数据分析" value="analysis" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadTasks">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 任务列表 -->
    <el-card class="content-card">
      <el-table :data="tasks" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="任务标题" min-width="200">
          <template #default="{ row }">
            <div class="task-title">
              {{ row.title || `任务 #${row.id}` }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="agent_id" label="Agent" width="120" />
        <el-table-column prop="task_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="getTypeTagType(row.task_type)">
              {{ getTypeName(row.task_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">
              {{ getStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration_seconds" label="耗时" width="100">
          <template #default="{ row }">
            {{ row.duration_seconds ? formatDuration(row.duration_seconds) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="showTaskDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <span class="total-count">共 {{ tasks.length }} 条记录</span>
      </div>
    </el-card>

    <!-- 任务详情对话框 -->
    <el-dialog v-model="detailVisible" title="任务详情" width="600px">
      <el-descriptions :column="2" border v-if="currentTask">
        <el-descriptions-item label="任务ID">{{ currentTask.id }}</el-descriptions-item>
        <el-descriptions-item label="Agent">{{ currentTask.agent_id }}</el-descriptions-item>
        <el-descriptions-item label="标题" :span="2">{{ currentTask.title || '-' }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ getTypeName(currentTask.task_type) }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusTagType(currentTask.status)" size="small">
            {{ getStatusName(currentTask.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(currentTask.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ formatTime(currentTask.started_at) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ formatTime(currentTask.completed_at) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ currentTask.duration_seconds ? formatDuration(currentTask.duration_seconds) : '-' }}</el-descriptions-item>
        <el-descriptions-item label="用户ID">{{ currentTask.user_id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="会话ID">{{ currentTask.session_id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="交付物类型">{{ currentTask.deliverable_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="交付物路径" :span="2">{{ currentTask.deliverable_path || '-' }}</el-descriptions-item>
        <el-descriptions-item label="详情" :span="2">
          <pre class="details-pre">{{ formatDetails(currentTask.details) }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

interface Task {
  id: number
  agent_id: string
  title: string
  task_type: string
  status: string
  created_at: string
  started_at: string
  completed_at: string
  duration_seconds: number
  deliverable_type: string
  deliverable_path: string
  user_id: string
  session_id: string
  details: string
}

const loading = ref(false)
const tasks = ref<Task[]>([])
const agents = ref<{ id: string }[]>([])
const stats = ref<any>({})
const detailVisible = ref(false)
const currentTask = ref<Task | null>(null)

const filters = reactive({
  agent_id: '',
  status: '',
  task_type: ''
})

const getAuthHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('access_token')}`
})

const loadAgents = async () => {
  try {
    const res = await axios.get('/api/agents', { headers: getAuthHeaders() })
    if (res.data.success) {
      agents.value = res.data.data.map((a: any) => ({ id: a.id }))
    }
  } catch (error) {
    console.error('加载 Agent 失败:', error)
  }
}

const loadStats = async () => {
  try {
    const res = await axios.get('/api/tasks/stats', { headers: getAuthHeaders() })
    if (res.data.success) {
      stats.value = res.data.data
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

const loadTasks = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (filters.agent_id) params.append('agent_id', filters.agent_id)
    if (filters.status) params.append('status', filters.status)
    if (filters.task_type) params.append('task_type', filters.task_type)

    const res = await axios.get(`/api/tasks?${params.toString()}`, { headers: getAuthHeaders() })
    if (res.data.success) {
      tasks.value = res.data.data
    }
  } catch (error) {
    ElMessage.error('加载任务列表失败')
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.agent_id = ''
  filters.status = ''
  filters.task_type = ''
  loadTasks()
}

const showTaskDetail = (task: Task) => {
  currentTask.value = task
  detailVisible.value = true
}

const getStatusName = (status: string) => {
  const names: Record<string, string> = {
    pending: '待处理',
    running: '进行中',
    completed: '已完成',
    failed: '失败'
  }
  return names[status] || status
}

const getStatusTagType = (status: string) => {
  const types: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getTypeName = (type: string) => {
  const names: Record<string, string> = {
    chat: '对话',
    document: '文档处理',
    code: '代码生成',
    analysis: '数据分析'
  }
  return names[type] || type || '其他'
}

const getTypeTagType = (type: string) => {
  const types: Record<string, string> = {
    chat: '',
    document: 'success',
    code: 'warning',
    analysis: 'info'
  }
  return types[type] || 'info'
}

const formatTime = (time: string) => {
  if (!time) return ''
  return time.replace('T', ' ').substring(0, 19)
}

const formatDuration = (seconds: number) => {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
  return `${Math.floor(seconds / 3600)}小时${Math.floor((seconds % 3600) / 60)}分`
}

const formatDetails = (details: string) => {
  if (!details) return '-'
  try {
    return JSON.stringify(JSON.parse(details), null, 2)
  } catch {
    return details
  }
}

onMounted(() => {
  loadAgents()
  loadStats()
  loadTasks()
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

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  padding: 10px 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #409eff;
}

.stat-value.success {
  color: #67c23a;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.filter-card {
  margin-bottom: 20px;
}

.content-card {
  min-height: 400px;
}

.task-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pagination-container {
  margin-top: 16px;
  text-align: right;
}

.total-count {
  font-size: 13px;
  color: #909399;
}

.details-pre {
  margin: 0;
  font-size: 12px;
  max-height: 200px;
  overflow: auto;
  background: #f5f7fa;
  padding: 8px;
  border-radius: 4px;
}
</style>