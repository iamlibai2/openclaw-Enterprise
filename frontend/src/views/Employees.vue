<template>
  <div class="employees-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>员工管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog" v-if="canEdit">
          <el-icon><Plus /></el-icon>
          新增员工
        </el-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索员工姓名/邮箱"
        style="width: 200px"
        clearable
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-select v-model="filterDepartment" placeholder="部门筛选" clearable style="width: 150px">
        <el-option
          v-for="dept in flatDepartments"
          :key="dept.id"
          :label="dept.name"
          :value="dept.id"
        />
      </el-select>
      <el-select v-model="filterBinding" placeholder="绑定状态" clearable style="width: 120px">
        <el-option label="已绑定" value="bound" />
        <el-option label="未绑定" value="unbound" />
      </el-select>
      <div class="filter-stats">
        <el-tag type="info">{{ filteredEmployees.length }} 人</el-tag>
      </div>
    </div>

    <!-- 员工卡片列表 -->
    <div class="employee-grid" v-loading="loading">
      <div
        class="employee-card"
        v-for="emp in filteredEmployees"
        :key="emp.id"
      >
        <div class="card-header">
          <el-avatar :size="56" class="employee-avatar">
            {{ emp.name.charAt(0) }}
          </el-avatar>
        </div>

        <div class="card-body">
          <h3 class="employee-name">{{ emp.name }}</h3>
          <p class="employee-email" v-if="emp.email">{{ emp.email }}</p>

          <div class="info-row" v-if="emp.department_name">
            <el-icon><OfficeBuilding /></el-icon>
            <span>{{ emp.department_name }}</span>
          </div>

          <div class="info-row" v-if="emp.manager_name">
            <el-icon><User /></el-icon>
            <span>上级: {{ emp.manager_name }}</span>
          </div>

          <div class="agent-info" v-if="emp.agent_ids && emp.agent_ids.length">
            <el-icon><Monitor /></el-icon>
            <div class="agent-details">
              <div class="agent-tags">
                <el-tag v-for="agent in emp.agents" :key="agent.id" size="small" type="primary" style="margin-right: 4px;">
                  {{ agent.name }}
                </el-tag>
              </div>
            </div>
          </div>
          <div class="agent-info unbound" v-else>
            <el-icon><Warning /></el-icon>
            <span>未绑定 Agent</span>
          </div>
        </div>

        <div class="card-footer">
          <el-button size="small" text @click="showEditDialog(emp)" v-if="canEdit">
            <el-icon><Edit /></el-icon>
          </el-button>
          <el-button size="small" text type="primary" @click="showDetailDialog(emp)">
            <el-icon><View /></el-icon>
          </el-button>
          <el-button size="small" text type="danger" @click="deleteEmployee(emp)" v-if="canDelete">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div class="empty-state" v-if="!loading && filteredEmployees.length === 0">
      <el-icon :size="64"><User /></el-icon>
      <p>暂无员工数据</p>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑员工' : '新增员工'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="formData.name" placeholder="员工姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="formData.email" placeholder="邮箱地址" />
        </el-form-item>
        <el-form-item label="电话" prop="phone">
          <el-input v-model="formData.phone" placeholder="联系电话" />
        </el-form-item>
        <el-form-item label="部门" prop="department_id">
          <el-cascader
            v-model="formData.department_id"
            :options="departmentTree"
            :props="{ value: 'id', label: 'name', children: 'children', checkStrictly: true, emitPath: false }"
            placeholder="选择部门"
            clearable
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="上级" prop="manager_id">
          <el-select v-model="formData.manager_id" placeholder="选择直属上级" clearable style="width: 100%">
            <el-option
              v-for="emp in employees.filter(e => e.id !== editingId)"
              :key="emp.id"
              :label="emp.name"
              :value="emp.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Agents" prop="agent_ids">
          <div class="agent-selector">
            <div class="selected-agents" @click="showAgentSelector = true" :class="{ 'all-bound': allAgentsBound && !formData.agent_ids.length }">
              <template v-if="formData.agent_ids.length">
                <el-tag v-for="id in formData.agent_ids" :key="id" size="small" closable @close="removeAgent(id)" style="margin: 2px;">
                  {{ getAgentName(id) }}
                </el-tag>
              </template>
              <template v-else-if="allAgentsBound">
                <span class="placeholder warning">所有 Agent 已被认领完</span>
              </template>
              <span v-else class="placeholder">点击选择 Agent</span>
            </div>
            <el-dialog v-model="showAgentSelector" title="选择 Agent" width="500px" append-to-body>
              <div class="agent-cards">
                <div
                  v-for="agent in allAgents"
                  :key="agent.id"
                  class="agent-card"
                  :class="{ selected: formData.agent_ids.includes(agent.id), disabled: agent.bound && !formData.agent_ids.includes(agent.id) }"
                  @click="toggleAgent(agent.id, agent.bound)"
                >
                  <el-checkbox :model-value="formData.agent_ids.includes(agent.id)" @click.stop />
                  <div class="agent-card-info">
                    <div class="agent-card-name">{{ agent.name }}</div>
                    <div class="agent-card-id">{{ agent.id }}</div>
                    <div class="agent-card-model" v-if="agent.model">{{ agent.model }}</div>
                  </div>
                  <el-tag v-if="agent.bound && !formData.agent_ids.includes(agent.id)" size="small" type="info">已绑定</el-tag>
                </div>
              </div>
              <div v-if="allAgentsBound && !formData.agent_ids.length" class="all-bound-tip">
                <el-icon><Warning /></el-icon>
                <span>所有 Agent 都已被其他员工认领</span>
              </div>
              <template #footer>
                <el-button @click="showAgentSelector = false">确定</el-button>
              </template>
            </el-dialog>
          </div>
        </el-form-item>

        <!-- Agent 配置（仅绑定了 Agent 时显示） -->
        <el-divider v-if="formData.agent_ids.length" content-position="left">
          <span style="font-size: 13px; color: #606266;">Agent 配置</span>
        </el-divider>
        <div class="agent-config-in-form" v-if="formData.agent_ids.length">
          <!-- 自主性 -->
          <div class="config-row">
            <span class="config-title">
              自主性级别
              <el-tooltip content="high: 不需确认就执行；medium: 需确认后执行；low: 每步确认" placement="top">
                <el-icon class="config-help"><QuestionFilled /></el-icon>
              </el-tooltip>
            </span>
            <el-radio-group v-model="editAgentConfig.autonomy" size="small">
              <el-radio-button value="high">高度自主</el-radio-button>
              <el-radio-button value="medium">中等自主</el-radio-button>
              <el-radio-button value="low">低自主</el-radio-button>
            </el-radio-group>
          </div>

          <!-- 汇报设置 -->
          <div class="config-row">
            <span class="config-title">汇报设置</span>
            <div class="config-inline">
              <el-select v-model="editAgentConfig.reportStyle.detailLevel" size="small" style="width: 90px">
                <el-option label="摘要" value="summary" />
                <el-option label="详细" value="detail" />
              </el-select>
              <el-select v-model="editAgentConfig.reportStyle.timing" size="small" style="width: 110px">
                <el-option label="完成后汇报" value="on_complete" />
                <el-option label="实时汇报" value="realtime" />
              </el-select>
            </div>
          </div>

          <!-- 学习设置 -->
          <div class="config-row">
            <span class="config-title">学习设置</span>
            <div class="config-inline">
              <div class="switch-item">
                <span class="switch-label">记住反馈</span>
                <el-switch v-model="editAgentConfig.learning.rememberFeedback" size="small" />
              </div>
              <div class="switch-item">
                <span class="switch-label">自动改进</span>
                <el-switch v-model="editAgentConfig.learning.autoImprove" size="small" />
              </div>
            </div>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="员工详情" size="450px">
      <div class="detail-content" v-if="currentEmployee">
        <div class="detail-header">
          <el-avatar :size="80" class="detail-avatar">
            {{ currentEmployee.name.charAt(0) }}
          </el-avatar>
          <h2 class="detail-name">{{ currentEmployee.name }}</h2>
          <p class="detail-email" v-if="currentEmployee.email">{{ currentEmployee.email }}</p>
          <el-tag :type="currentEmployee.status === 'active' ? 'success' : 'info'">
            {{ currentEmployee.status === 'active' ? '在职' : '离职' }}
          </el-tag>
        </div>

        <el-divider />

        <el-descriptions :column="1" border>
          <el-descriptions-item label="部门">
            {{ currentEmployee.department_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="直属上级">
            {{ currentEmployee.manager_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="电话">
            {{ currentEmployee.phone || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="绑定 Agent">
            <template v-if="currentEmployee.agent_ids && currentEmployee.agent_ids.length">
              <el-tag v-for="agent in currentEmployee.agents" :key="agent.id" type="primary" size="small" style="margin-right: 4px;">
                {{ agent.name }}
              </el-tag>
            </template>
            <span v-else style="color: #909399;">未绑定</span>
          </el-descriptions-item>
        </el-descriptions>

        <!-- Agent 配置区域（只展示） -->
        <el-divider content-position="left" v-if="currentEmployee.agent_ids && currentEmployee.agent_ids.length">
          <span style="font-size: 13px; color: #606266;">Agent 配置</span>
        </el-divider>

        <div class="agent-config-card" v-if="currentEmployee.agent_ids && currentEmployee.agent_ids.length && agentConfig">
          <div class="config-group">
            <div class="config-group-title">自主性</div>
            <div class="config-group-value">
              <el-tag :type="agentConfig.autonomy === 'high' ? 'success' : agentConfig.autonomy === 'medium' ? 'warning' : 'info'" size="small">
                {{ agentConfig.autonomy === 'high' ? '高度自主' : agentConfig.autonomy === 'medium' ? '中等自主' : '低自主' }}
              </el-tag>
            </div>
          </div>
          <div class="config-group">
            <div class="config-group-title">汇报</div>
            <div class="config-group-value">
              <span>{{ agentConfig.reportStyle.detailLevel === 'summary' ? '摘要' : '详细' }} · {{ agentConfig.reportStyle.timing === 'on_complete' ? '完成后' : '实时' }}</span>
            </div>
          </div>
          <div class="config-group">
            <div class="config-group-title">学习</div>
            <div class="config-group-value">
              <el-tag v-if="agentConfig.learning.rememberFeedback" type="success" size="small" style="margin-right: 4px">记住反馈</el-tag>
              <el-tag v-if="agentConfig.learning.autoImprove" type="success" size="small">自动改进</el-tag>
              <span v-if="!agentConfig.learning.rememberFeedback && !agentConfig.learning.autoImprove" style="color: #909399">未开启</span>
            </div>
          </div>
        </div>

        <!-- 绑定渠道信息 -->
        <el-divider content-position="left" v-if="currentEmployee.agent_id">
          <span>绑定渠道</span>
          <el-button
            link
            type="primary"
            size="small"
            @click="router.push('/bindings')"
            style="margin-left: 8px;"
          >
            <el-icon><Link /></el-icon>
            配置
          </el-button>
        </el-divider>
        <div class="bindings-section" v-if="currentEmployee.agent_id">
          <div v-if="agentBindings.length === 0" class="no-bindings">
            <el-tag type="warning" size="small">该 Agent 为默认 Agent，接收所有未匹配消息</el-tag>
          </div>
          <div v-else class="bindings-list">
            <div class="binding-item" v-for="(binding, idx) in agentBindings" :key="idx">
              <span class="binding-index">#{{ idx + 1 }}</span>
              <span class="binding-channel" v-if="binding.match.channel">{{ binding.match.channel }}</span>
              <span class="binding-account" v-if="binding.match.accountId">/ {{ binding.match.accountId }}</span>
              <el-tag size="small" v-if="binding.match.peer?.kind">
                {{ binding.match.peer.kind === 'direct' ? '单聊' : '群聊' }}
              </el-tag>
              <span class="binding-all" v-if="!binding.match.channel && !binding.match.accountId && !binding.match.peer">
                匹配所有
              </span>
            </div>
          </div>
        </div>

        <el-divider content-position="left" v-if="subordinates.length">下属员工</el-divider>
        <div class="subordinates-list" v-if="subordinates.length">
          <div class="subordinate-item" v-for="sub in subordinates" :key="sub.id">
            <el-avatar :size="32">{{ sub.name.charAt(0) }}</el-avatar>
            <div class="sub-info">
              <span class="sub-name">{{ sub.name }}</span>
              <span class="sub-agent" v-if="sub.agent_id">{{ sub.agent_id }}</span>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Search, Edit, View, Delete, User, OfficeBuilding, Monitor, Warning, Link, QuestionFilled, Promotion, Operation, ChatLineSquare } from '@element-plus/icons-vue'
import { employeeApi, departmentApi, bindingApi, employeeAgentApi, type Employee, type Department, type UnboundAgent, type BindingConfig, type EmployeeAgentConfig } from '../api'
import { useUserStore } from '../user/stores'
import { createFormRules } from '../utils/rules'

const router = useRouter()

const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const employees = ref<Employee[]>([])
const departments = ref<Department[]>([])
const unboundAgents = ref<UnboundAgent[]>([])

const searchKeyword = ref('')
const filterDepartment = ref<number | null>(null)
const filterBinding = ref('')

const dialogVisible = ref(false)
const detailVisible = ref(false)
const showAgentSelector = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const currentEmployee = ref<Employee | null>(null)
const subordinates = ref<Employee[]>([])
const agentBindings = ref<BindingConfig[]>([])
const agentConfig = ref<EmployeeAgentConfig | null>(null)
const editAgentConfig = ref<EmployeeAgentConfig>({
  autonomy: 'high',
  reportStyle: { detailLevel: 'summary', timing: 'on_complete' },
  learning: { rememberFeedback: true, autoImprove: true }
})

const canEdit = computed(() => userStore.hasPermission('employees', 'write'))
const canDelete = computed(() => userStore.hasPermission('employees', 'delete'))

const formData = ref({
  name: '',
  email: '',
  phone: '',
  department_id: null as number | null,
  manager_id: null as number | null,
  agent_ids: [] as string[],
  status: 'active'
})

// 使用统一校验规则
const rules: FormRules = createFormRules({
  name: 'employeeName',
  email: 'email',
  phone: 'phone'
})

// 扁平化部门列表（用于筛选）
const flatDepartments = computed(() => {
  const result: { id: number; name: string }[] = []
  function flatten(depts: Department[], prefix = '') {
    for (const dept of depts) {
      result.push({ id: dept.id, name: prefix + dept.name })
      if (dept.children?.length) {
        flatten(dept.children, prefix + '  ')
      }
    }
  }
  flatten(departments.value)
  return result
})

// 部门树（用于级联选择）
const departmentTree = computed(() => departments.value)

// 所有 Agent 列表（标记绑定状态）
const allAgents = computed(() => {
  const allBoundAgentIds = new Set<string>()
  for (const emp of employees.value) {
    if (emp.agent_ids && emp.id !== editingId.value) {
      emp.agent_ids.forEach((aid: string) => allBoundAgentIds.add(aid))
    }
  }
  return unboundAgents.value.map(a => ({
    ...a,
    bound: allBoundAgentIds.has(a.id),
    model: a.model?.primary
  }))
})

// 获取 Agent 名称
function getAgentName(id: string) {
  const agent = allAgents.value.find(a => a.id === id)
  return agent?.name || id
}

// 切换 Agent 选择
function toggleAgent(id: string, bound: boolean) {
  if (bound) return // 已被其他人绑定，不可选
  const idx = formData.value.agent_ids.indexOf(id)
  if (idx > -1) {
    formData.value.agent_ids.splice(idx, 1)
  } else {
    formData.value.agent_ids.push(id)
  }
}

// 移除已选 Agent
function removeAgent(id: string) {
  const idx = formData.value.agent_ids.indexOf(id)
  if (idx > -1) {
    formData.value.agent_ids.splice(idx, 1)
  }
}

// 判断是否所有 agent 都已被绑定
const allAgentsBound = computed(() => {
  return allAgents.value.length > 0 && allAgents.value.every(a => a.bound)
})

// 筛选后的员工列表
const filteredEmployees = computed(() => {
  let result = employees.value

  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(e =>
      e.name.toLowerCase().includes(keyword) ||
      e.email?.toLowerCase().includes(keyword)
    )
  }

  if (filterDepartment.value) {
    result = result.filter(e => e.department_id === filterDepartment.value)
  }

  if (filterBinding.value) {
    if (filterBinding.value === 'bound') {
      result = result.filter(e => e.agent_ids && e.agent_ids.length > 0)
    } else {
      result = result.filter(e => !e.agent_ids || e.agent_ids.length === 0)
    }
  }

  return result
})

async function loadData() {
  loading.value = true
  try {
    const [empRes, deptRes] = await Promise.all([
      employeeApi.list(),
      departmentApi.list()
    ])

    if (empRes.data.success) {
      employees.value = empRes.data.data
      unboundAgents.value = empRes.data.unbound_agents
    }

    if (deptRes.data.success) {
      departments.value = deptRes.data.data
    }
  } catch (e: any) {
    ElMessage.error('加载失败：' + e.message)
  } finally {
    loading.value = false
  }
}

function showCreateDialog() {
  isEdit.value = false
  editingId.value = null
  formData.value = {
    name: '',
    email: '',
    phone: '',
    department_id: null,
    manager_id: null,
    agent_ids: [],
    status: 'active'
  }
  editAgentConfig.value = {
    autonomy: 'high',
    reportStyle: { detailLevel: 'summary', timing: 'on_complete' },
    learning: { rememberFeedback: true, autoImprove: true }
  }
  dialogVisible.value = true
}

async function showEditDialog(emp: Employee) {
  isEdit.value = true
  editingId.value = emp.id
  formData.value = {
    name: emp.name,
    email: emp.email || '',
    phone: emp.phone || '',
    department_id: emp.department_id,
    manager_id: emp.manager_id,
    agent_ids: emp.agent_ids || [],
    status: emp.status
  }
  // 加载现有 Agent 配置
  if (emp.agent_ids && emp.agent_ids.length) {
    try {
      const res = await employeeAgentApi.getConfig(emp.id)
      if (res.data.success && res.data.data) {
        editAgentConfig.value = res.data.data
      } else {
        editAgentConfig.value = {
          autonomy: 'high',
          reportStyle: { detailLevel: 'summary', timing: 'on_complete' },
          learning: { rememberFeedback: true, autoImprove: true }
        }
      }
    } catch {
      editAgentConfig.value = {
        autonomy: 'high',
        reportStyle: { detailLevel: 'summary', timing: 'on_complete' },
        learning: { rememberFeedback: true, autoImprove: true }
      }
    }
  } else {
    editAgentConfig.value = {
      autonomy: 'high',
      reportStyle: { detailLevel: 'summary', timing: 'on_complete' },
      learning: { rememberFeedback: true, autoImprove: true }
    }
  }
  dialogVisible.value = true
}

async function showDetailDialog(emp: Employee) {
  currentEmployee.value = emp
  detailVisible.value = true
  agentBindings.value = []
  agentConfig.value = null

  // 加载 Agent 配置
  if (emp.agent_ids && emp.agent_ids.length) {
    try {
      const res = await employeeAgentApi.getConfig(emp.id)
      if (res.data.success) {
        agentConfig.value = res.data.data
      }
    } catch {
      // 使用默认配置
      agentConfig.value = {
        autonomy: 'high',
        reportStyle: { detailLevel: 'summary', timing: 'on_complete' },
        learning: { rememberFeedback: true, autoImprove: true }
      }
    }
  }

  // 加载下属
  try {
    const res = await employeeApi.get(emp.id)
    if (res.data.success) {
      subordinates.value = res.data.subordinates
    }
  } catch {
    subordinates.value = []
  }

  // 加载该员工 Agent 的绑定配置
  if (emp.agent_ids && emp.agent_ids.length) {
    try {
      const res = await bindingApi.list()
      if (res.data.success) {
        agentBindings.value = res.data.data.filter(b => emp.agent_ids.includes(b.agentId))
      }
    } catch {
      agentBindings.value = []
    }
  }
}

async function saveAgentConfig() {
  if (!currentEmployee.value || !agentConfig.value) return

  try {
    const res = await employeeAgentApi.updateConfig(currentEmployee.value.id, agentConfig.value)
    if (res.data.success) {
      ElMessage.success('配置已保存')
    } else {
      ElMessage.error(res.data.error || '保存失败')
    }
  } catch (e: any) {
    ElMessage.error('保存失败：' + e.message)
  }
}

async function submitForm() {
  if (!formRef.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    const data: any = {
      name: formData.value.name,
      email: formData.value.email || null,
      phone: formData.value.phone || null,
      department_id: formData.value.department_id,
      manager_id: formData.value.manager_id,
      agent_ids: formData.value.agent_ids
    }

    if (isEdit.value) {
      data.status = formData.value.status
      const res = await employeeApi.update(editingId.value!, data)
      if (res.data.success) {
        // 同时保存 Agent 配置
        if (formData.value.agent_ids.length) {
          await employeeAgentApi.updateConfig(editingId.value!, editAgentConfig.value)
        }
        ElMessage.success('更新成功')
        dialogVisible.value = false
        loadData()
      } else {
        ElMessage.error(res.data.error)
      }
    } else {
      const res = await employeeApi.create(data)
      if (res.data.success) {
        // 新建员工后保存 Agent 配置
        if (formData.value.agent_ids.length && res.data.data?.id) {
          await employeeAgentApi.updateConfig(res.data.data.id, editAgentConfig.value)
        }
        ElMessage.success('创建成功')
        dialogVisible.value = false
        loadData()
      } else {
        ElMessage.error(res.data.error)
      }
    }
  } catch (e: any) {
    ElMessage.error('操作失败：' + e.message)
  } finally {
    submitting.value = false
  }
}

async function deleteEmployee(emp: Employee) {
  try {
    await ElMessageBox.confirm(`确定删除员工「${emp.name}」？`, '删除确认', { type: 'warning' })
    const res = await employeeApi.delete(emp.id)
    if (res.data.success) {
      ElMessage.success('删除成功')
      loadData()
    } else {
      ElMessage.error(res.data.error)
    }
  } catch {
    // 用户取消
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.employees-page {
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

.header-actions {
  display: flex;
  gap: 10px;
}

/* 筛选栏 */
.filter-bar {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.filter-stats {
  margin-left: auto;
}

/* 员工卡片网格 */
.employee-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.employee-card {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  overflow: hidden;
  transition: all 0.2s;
}

.employee-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.card-header {
  position: relative;
  padding: 20px 20px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.employee-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 24px;
  font-weight: 600;
}

.card-body {
  padding: 0 16px 16px;
  text-align: center;
}

.employee-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.employee-email {
  font-size: 13px;
  color: #909399;
  margin-bottom: 12px;
}

.info-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
  margin-bottom: 6px;
}

.info-row .el-icon {
  color: #909399;
}

.agent-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
}

.agent-info .el-icon {
  color: #409eff;
}

.agent-info.unbound .el-icon {
  color: #e6a23c;
}

.agent-details {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.agent-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.agent-model {
  font-size: 11px;
  color: #909399;
}

.agent-info.unbound span {
  font-size: 13px;
  color: #e6a23c;
}

.card-footer {
  padding: 8px 16px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: center;
  gap: 8px;
}

/* 详情抽屉 */
.detail-content {
  padding: 0 20px;
}

.detail-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0;
}

.detail-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 32px;
  font-weight: 600;
  margin-bottom: 16px;
}

.detail-name {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.detail-email {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.subordinates-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.subordinate-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
}

.subordinate-item .el-avatar {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: #fff;
}

.sub-info {
  display: flex;
  flex-direction: column;
}

.sub-name {
  font-size: 14px;
  color: #303133;
}

.sub-agent {
  font-size: 12px;
  color: #909399;
}

/* 绑定渠道信息 */
.agent-config-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;
  padding: 0 12px;
}

/* Agent 配置（详情抽屉展示） */
.agent-config-card {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
  margin-top: 8px;
}

.config-group {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #e4e7ed;
}

.config-group:last-child {
  border-bottom: none;
}

.config-group-title {
  font-size: 13px;
  color: #909399;
  font-weight: 500;
}

.config-group-value {
  font-size: 14px;
  color: #303133;
}

/* Agent 配置（编辑对话框内） */
.agent-config-in-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 20px;
  background: #fafafa;
  border-radius: 8px;
  margin: 0 0 20px 0;
}

.config-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.config-title {
  font-size: 13px;
  color: #606266;
  width: 90px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.config-help {
  color: #909399;
  font-size: 14px;
  cursor: help;
}

.config-inline {
  display: flex;
  align-items: center;
  gap: 12px;
}

.switch-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.switch-label {
  font-size: 13px;
  color: #606266;
}

.bindings-section {
  margin-top: 8px;
}

.no-bindings {
  text-align: center;
}

.bindings-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.binding-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 13px;
}

.binding-index {
  color: #409eff;
  font-weight: 500;
}

.binding-channel {
  color: #303133;
}

.binding-account {
  color: #606266;
}

.binding-all {
  color: #909399;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: #c0c4cc;
}

.empty-state p {
  margin-top: 16px;
  font-size: 14px;
}

/* Agent 选择器 */
.agent-selector {
  width: 100%;
}

.selected-agents {
  min-height: 40px;
  padding: 6px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}

.selected-agents:hover {
  border-color: #409eff;
}

.selected-agents .placeholder {
  color: #a8abb2;
  font-size: 14px;
}

.agent-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.agent-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.agent-card:hover:not(.disabled) {
  border-color: #409eff;
  background: #f5f7fa;
}

.agent-card.selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.agent-card.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.agent-card-info {
  flex: 1;
}

.agent-card-name {
  font-weight: 500;
  color: #303133;
}

.agent-card-id {
  font-size: 12px;
  color: #909399;
}

.agent-card-model {
  font-size: 11px;
  color: #67c23a;
}

.selected-agents.all-bound {
  border-color: #e6a23c;
  background: #fdf6ec;
}

.placeholder.warning {
  color: #e6a23c;
}

.all-bound-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  color: #e6a23c;
  background: #fdf6ec;
  border-radius: 8px;
  margin-top: 12px;
}
</style>