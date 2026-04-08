<template>
  <div class="scheduled-tasks-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>定时任务</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog" v-if="canEdit">
          <el-icon><Plus /></el-icon>
          新增任务
        </el-button>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="tasks-list" v-loading="loading">
      <div
        class="task-card"
        v-for="task in tasks"
        :key="task.id"
        :class="{ disabled: !task.enabled }"
      >
        <div class="card-header">
          <div class="task-info">
            <h3 class="task-name">{{ task.name }}</h3>
            <el-tag size="small" :type="getTaskTypeTag(task.task_type)">
              {{ getTaskTypeLabel(task.task_type) }}
            </el-tag>
          </div>
          <div class="task-status">
            <el-switch
              v-model="task.enabled"
              @change="toggleTask(task)"
              :disabled="!canEdit"
            />
          </div>
        </div>

        <div class="card-body">
          <div class="task-meta">
            <span class="meta-item">
              <el-icon><User /></el-icon>
              {{ getAgentName(task.agent_id) }}
            </span>
            <span class="meta-item">
              <el-icon><Timer /></el-icon>
              {{ getIntervalLabel(task.interval_minutes) }}
            </span>
          </div>

          <div class="task-stats">
            <span>执行次数: {{ task.execution_count || 0 }}</span>
            <span v-if="task.last_run_at">
              上次执行: {{ formatTime(task.last_run_at) }}
            </span>
            <span v-if="task.next_run_at">
              下次执行: {{ formatTime(task.next_run_at) }}
            </span>
          </div>

          <div class="last-execution" v-if="task.last_execution">
            <span :class="['status-dot', task.last_execution.status]"></span>
            <span class="status-text">{{ getStatusLabel(task.last_execution.status) }}</span>
            <span class="exec-time">{{ formatTime(task.last_execution.created_at) }}</span>
          </div>
        </div>

        <div class="card-footer">
          <el-button size="small" @click="viewExecutions(task)">
            <el-icon><List /></el-icon>
            执行记录
          </el-button>
          <el-button size="small" type="primary" plain @click="runTaskNow(task)" :loading="task._running" v-if="canEdit">
            <el-icon><VideoPlay /></el-icon>
            立即执行
          </el-button>
          <el-button size="small" @click="editTask(task)" v-if="canEdit">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
          <el-button size="small" type="danger" @click="deleteTask(task)" v-if="canEdit">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div class="empty-state" v-if="!loading && tasks.length === 0">
      <el-icon :size="64"><Clock /></el-icon>
      <p>暂无定时任务</p>
      <p class="hint">创建任务后，系统将自动按计划执行</p>
    </div>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑任务' : '新增任务'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="formData.name" placeholder="例如：每日日志检查" />
        </el-form-item>

        <el-form-item label="执行 Agent" prop="agent_id">
          <el-select v-model="formData.agent_id" placeholder="选择 Agent" style="width: 100%">
            <el-option
              v-for="agent in agents"
              :key="agent.id"
              :label="agent.name || agent.id"
              :value="agent.id"
            >
              <span>{{ agent.name || agent.id }}</span>
              <span style="color: #999; margin-left: 8px; font-size: 12px;">{{ agent.modelName }}</span>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="formData.task_type" placeholder="选择任务类型" style="width: 100%" @change="onTaskTypeChange">
            <el-option
              v-for="(config, key) in taskTypes"
              :key="key"
              :label="config.name"
              :value="key"
            >
              <div>
                <span>{{ config.name }}</span>
                <div style="color: #999; font-size: 12px;">{{ config.description }}</div>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="执行频率" prop="interval_minutes">
          <el-select v-model="formData.interval_minutes" placeholder="选择执行频率" style="width: 100%">
            <el-option
              v-for="opt in intervalOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="自定义消息">
          <el-input
            v-model="formData.task_params.message"
            type="textarea"
            :rows="3"
            placeholder="可选，自定义发送给 Agent 的消息内容"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 执行记录对话框 -->
    <el-dialog
      v-model="executionsDialogVisible"
      :title="`${currentTask?.name} - 执行记录`"
      width="700px"
    >
      <div class="executions-list" v-loading="executionsLoading">
        <div
          class="execution-item"
          v-for="exec in executions"
          :key="exec.id"
        >
          <div class="exec-header">
            <span :class="['status-dot', exec.status]"></span>
            <span class="status-label">{{ getStatusLabel(exec.status) }}</span>
            <span class="exec-time">{{ formatTime(exec.created_at) }}</span>
          </div>
          <div class="exec-body" v-if="exec.result || exec.error_message">
            <pre v-if="exec.result">{{ formatResult(exec.result) }}</pre>
            <pre v-if="exec.error_message" class="error">{{ exec.error_message }}</pre>
          </div>
          <div class="exec-footer" v-if="exec.started_at && exec.finished_at">
            耗时: {{ getDuration(exec.started_at, exec.finished_at) }}
          </div>
        </div>

        <div class="empty-state" v-if="!executionsLoading && executions.length === 0">
          <p>暂无执行记录</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { Plus, User, Timer, List, VideoPlay, Edit, Delete, Clock } from '@element-plus/icons-vue'
import { agentApi, scheduledTaskApi, type ScheduledTask, type TaskExecution, type IntervalOption } from '../api'
import { useUserStore } from '../stores/user'

interface Agent {
  id: string
  name?: string
  modelName?: string
}

const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const tasks = ref<(ScheduledTask & { _running?: boolean })[]>([])
const agents = ref<Agent[]>([])
const taskTypes = ref<Record<string, { name: string; description: string }>>({})
const intervalOptions = ref<IntervalOption[]>([])

const canEdit = computed(() => userStore.hasPermission('tasks', 'write'))

// 对话框
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(0)
const formRef = ref<FormInstance>()
const formData = ref({
  name: '',
  agent_id: '',
  task_type: '',
  interval_minutes: 60,
  task_params: { message: '' }
})

const formRules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  agent_id: [{ required: true, message: '请选择 Agent', trigger: 'change' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  interval_minutes: [{ required: true, message: '请选择执行频率', trigger: 'change' }]
}

// 执行记录对话框
const executionsDialogVisible = ref(false)
const executionsLoading = ref(false)
const executions = ref<TaskExecution[]>([])
const currentTask = ref<ScheduledTask | null>(null)

async function loadTasks() {
  loading.value = true
  try {
    const res = await scheduledTaskApi.list()
    if (res.data.success) {
      tasks.value = res.data.data || []
      taskTypes.value = res.data.task_types || {}
      intervalOptions.value = res.data.interval_options || []
    }
  } catch (e: any) {
    ElMessage.error('加载失败：' + e.message)
  } finally {
    loading.value = false
  }
}

async function loadAgents() {
  try {
    const res = await agentApi.list()
    if (res.data.success) {
      agents.value = res.data.data || []
    }
  } catch (e: any) {
    console.error('Failed to load agents:', e)
  }
}

function showCreateDialog() {
  isEdit.value = false
  formData.value = {
    name: '',
    agent_id: '',
    task_type: '',
    interval_minutes: 60,
    task_params: { message: '' }
  }
  dialogVisible.value = true
}

function editTask(task: ScheduledTask) {
  isEdit.value = true
  editingId.value = task.id

  let taskParams = { message: '' }
  if (task.task_params) {
    try {
      taskParams = typeof task.task_params === 'string' ? JSON.parse(task.task_params) : task.task_params
    } catch {}
  }

  formData.value = {
    name: task.name,
    agent_id: task.agent_id,
    task_type: task.task_type,
    interval_minutes: task.interval_minutes,
    task_params: taskParams
  }
  dialogVisible.value = true
}

function onTaskTypeChange() {
  // 重置自定义消息
  const config = taskTypes.value[formData.value.task_type]
  if (config && (config as any).default_message) {
    formData.value.task_params.message = (config as any).default_message
  }
}

async function submitForm() {
  if (!formRef.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    const data = {
      name: formData.value.name,
      agent_id: formData.value.agent_id,
      task_type: formData.value.task_type,
      interval_minutes: formData.value.interval_minutes,
      task_params: formData.value.task_params.message ? formData.value.task_params : undefined
    }

    if (isEdit.value) {
      const res = await scheduledTaskApi.update(editingId.value, data)
      if (res.data.success) {
        ElMessage.success('更新成功')
        dialogVisible.value = false
        loadTasks()
      } else {
        ElMessage.error(res.data.error || '更新失败')
      }
    } else {
      const res = await scheduledTaskApi.create(data)
      if (res.data.success) {
        ElMessage.success('创建成功')
        dialogVisible.value = false
        loadTasks()
      } else {
        ElMessage.error(res.data.error || '创建失败')
      }
    }
  } catch (e: any) {
    ElMessage.error('操作失败：' + e.message)
  } finally {
    submitting.value = false
  }
}

async function toggleTask(task: ScheduledTask) {
  try {
    const res = await scheduledTaskApi.update(task.id, { enabled: task.enabled })
    if (!res.data.success) {
      ElMessage.error('操作失败')
      loadTasks()
    }
  } catch (e: any) {
    ElMessage.error('操作失败：' + e.message)
    loadTasks()
  }
}

async function runTaskNow(task: ScheduledTask & { _running?: boolean }) {
  try {
    task._running = true
    const res = await scheduledTaskApi.runNow(task.id)
    if (res.data.success) {
      ElMessage.success('任务已触发执行')
      loadTasks()
    } else {
      ElMessage.error(res.data.error || '执行失败')
    }
  } catch (e: any) {
    ElMessage.error('执行失败：' + e.message)
  } finally {
    task._running = false
  }
}

async function deleteTask(task: ScheduledTask) {
  try {
    await ElMessageBox.confirm(`确定删除任务「${task.name}」？`, '删除确认', { type: 'warning' })
    const res = await scheduledTaskApi.delete(task.id)
    if (res.data.success) {
      ElMessage.success('删除成功')
      loadTasks()
    } else {
      ElMessage.error(res.data.error || '删除失败')
    }
  } catch {
    // 用户取消
  }
}

async function viewExecutions(task: ScheduledTask) {
  currentTask.value = task
  executionsDialogVisible.value = true
  executionsLoading.value = true

  try {
    const res = await scheduledTaskApi.getExecutions(task.id, 20)
    if (res.data.success) {
      executions.value = res.data.data || []
    }
  } catch (e: any) {
    ElMessage.error('加载失败：' + e.message)
  } finally {
    executionsLoading.value = false
  }
}

function getAgentName(agentId: string): string {
  const agent = agents.value.find(a => a.id === agentId)
  return agent?.name || agentId
}

function getTaskTypeLabel(type: string): string {
  return taskTypes.value[type]?.name || type
}

function getTaskTypeTag(type: string): string {
  const map: Record<string, string> = {
    check_logs: 'warning',
    summarize: 'info'
  }
  return map[type] || ''
}

function getIntervalLabel(minutes: number): string {
  const opt = intervalOptions.value.find(o => o.value === minutes)
  return opt?.label || `每 ${minutes} 分钟`
}

function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '执行中',
    success: '成功',
    failed: '失败'
  }
  return map[status] || status
}

function formatTime(time?: string): string {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatResult(result: string): string {
  try {
    const parsed = JSON.parse(result)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return result
  }
}

function getDuration(start: string, end: string): string {
  const ms = new Date(end).getTime() - new Date(start).getTime()
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}min`
}

onMounted(() => {
  loadTasks()
  loadAgents()
})
</script>

<style scoped>
.scheduled-tasks-page {
  min-height: calc(100vh - 96px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

/* 任务列表 */
.tasks-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 16px;
}

.task-card {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  overflow: hidden;
  transition: all 0.3s;
}

.task-card.disabled {
  opacity: 0.6;
}

.task-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.card-header {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f0f0f0;
}

.task-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.card-body {
  padding: 16px;
}

.task-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #606266;
}

.task-stats {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #909399;
  margin-bottom: 12px;
}

.last-execution {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.success {
  background: #67c23a;
}

.status-dot.failed {
  background: #f56c6c;
}

.status-dot.running {
  background: #409eff;
  animation: pulse 1.5s infinite;
}

.status-dot.pending {
  background: #909399;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-weight: 500;
}

.exec-time {
  color: #909399;
}

.card-footer {
  padding: 12px 16px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #c0c4cc;
}

.empty-state p {
  margin: 8px 0 0;
}

.empty-state .hint {
  font-size: 13px;
  color: #c0c4cc;
}

/* 执行记录 */
.executions-list {
  max-height: 500px;
  overflow-y: auto;
}

.execution-item {
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.execution-item:last-child {
  border-bottom: none;
}

.exec-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.status-label {
  font-weight: 500;
}

.exec-body {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 8px 12px;
  margin-bottom: 8px;
}

.exec-body pre {
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.exec-body pre.error {
  color: #f56c6c;
}

.exec-footer {
  font-size: 12px;
  color: #909399;
}
</style>