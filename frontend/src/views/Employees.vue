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
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 120px">
        <el-option label="在职" value="active" />
        <el-option label="离职" value="inactive" />
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
        :class="{ 'inactive': emp.status === 'inactive' }"
      >
        <div class="card-header">
          <el-avatar :size="56" class="employee-avatar">
            {{ emp.name.charAt(0) }}
          </el-avatar>
          <div class="status-badge" :class="emp.status">
            {{ emp.status === 'active' ? '在职' : '离职' }}
          </div>
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

          <div class="agent-info" v-if="emp.agent_id">
            <el-icon><Monitor /></el-icon>
            <div class="agent-details">
              <span class="agent-name">{{ emp.agent_name }}</span>
              <span class="agent-model" v-if="emp.agent_model">{{ emp.agent_model }}</span>
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
        <el-form-item label="Agent" prop="agent_id">
          <el-select v-model="formData.agent_id" placeholder="绑定 Agent" clearable style="width: 100%">
            <el-option-group label="未绑定">
              <el-option
                v-for="agent in unboundAgents"
                :key="agent.id"
                :label="agent.name"
                :value="agent.id"
              >
                <span>{{ agent.name }}</span>
                <span style="color: #909399; font-size: 12px; margin-left: 8px;">{{ agent.id }}</span>
              </el-option>
            </el-option-group>
            <el-option-group label="已绑定（其他员工）" v-if="boundAgents.length">
              <el-option
                v-for="item in boundAgents"
                :key="item.agent.id"
                :label="`${item.agent.name} (${item.employee.name})`"
                :value="item.agent.id"
                disabled
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status" v-if="isEdit">
          <el-radio-group v-model="formData.status">
            <el-radio label="active">在职</el-radio>
            <el-radio label="inactive">离职</el-radio>
          </el-radio-group>
        </el-form-item>
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
            <template v-if="currentEmployee.agent_id">
              <el-tag type="primary">{{ currentEmployee.agent_name }}</el-tag>
              <span style="margin-left: 8px; color: #909399; font-size: 12px;">{{ currentEmployee.agent_model }}</span>
            </template>
            <span v-else style="color: #909399;">未绑定</span>
          </el-descriptions-item>
        </el-descriptions>

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
import { Plus, Search, Edit, View, Delete, User, OfficeBuilding, Monitor, Warning, Link } from '@element-plus/icons-vue'
import { employeeApi, departmentApi, bindingApi, type Employee, type Department, type UnboundAgent, type BindingConfig } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()

const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const employees = ref<Employee[]>([])
const departments = ref<Department[]>([])
const unboundAgents = ref<UnboundAgent[]>([])

const searchKeyword = ref('')
const filterDepartment = ref<number | null>(null)
const filterStatus = ref('')

const dialogVisible = ref(false)
const detailVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const currentEmployee = ref<Employee | null>(null)
const subordinates = ref<Employee[]>([])
const agentBindings = ref<BindingConfig[]>([])

const canEdit = computed(() => userStore.hasPermission('employees', 'write'))
const canDelete = computed(() => userStore.hasPermission('employees', 'delete'))

const formData = ref({
  name: '',
  email: '',
  phone: '',
  department_id: null as number | null,
  manager_id: null as number | null,
  agent_id: null as string | null,
  status: 'active'
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入员工姓名', trigger: 'blur' }]
}

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

// 已绑定的 Agent（用于显示）
const boundAgents = computed(() => {
  const result: { agent: { id: string; name: string }; employee: Employee }[] = []
  for (const emp of employees.value) {
    if (emp.agent_id && emp.id !== editingId.value) {
      result.push({
        agent: { id: emp.agent_id, name: emp.agent_name || emp.agent_id },
        employee: emp
      })
    }
  }
  return result
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

  if (filterStatus.value) {
    result = result.filter(e => e.status === filterStatus.value)
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
    agent_id: null,
    status: 'active'
  }
  dialogVisible.value = true
}

function showEditDialog(emp: Employee) {
  isEdit.value = true
  editingId.value = emp.id
  formData.value = {
    name: emp.name,
    email: emp.email || '',
    phone: emp.phone || '',
    department_id: emp.department_id,
    manager_id: emp.manager_id,
    agent_id: emp.agent_id,
    status: emp.status
  }
  dialogVisible.value = true
}

async function showDetailDialog(emp: Employee) {
  currentEmployee.value = emp
  detailVisible.value = true
  agentBindings.value = []

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
  if (emp.agent_id) {
    try {
      const res = await bindingApi.list()
      if (res.data.success) {
        agentBindings.value = res.data.data.filter(b => b.agentId === emp.agent_id)
      }
    } catch {
      agentBindings.value = []
    }
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
      agent_id: formData.value.agent_id
    }

    if (isEdit.value) {
      data.status = formData.value.status
      const res = await employeeApi.update(editingId.value!, data)
      if (res.data.success) {
        ElMessage.success('更新成功')
        dialogVisible.value = false
        loadData()
      } else {
        ElMessage.error(res.data.error)
      }
    } else {
      const res = await employeeApi.create(data)
      if (res.data.success) {
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

.employee-card.inactive {
  opacity: 0.6;
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

.status-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
}

.status-badge.active {
  background: #f0f9eb;
  color: #67c23a;
}

.status-badge.inactive {
  background: #f4f4f5;
  color: #909399;
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
</style>