<template>
  <div class="department-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>部门管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog" v-if="canEdit">
          <el-icon><Plus /></el-icon>
          新增部门
        </el-button>
      </div>
    </div>

    <!-- 部门树 -->
    <div class="department-tree" v-loading="loading">
      <el-tree
        :data="departments"
        :props="{ label: 'name', children: 'children' }"
        node-key="id"
        default-expand-all
        :expand-on-click-node="false"
      >
        <template #default="{ node, data }">
          <div class="tree-node">
            <div class="node-content">
              <el-icon class="dept-icon" v-if="!data.children?.length"><OfficeBuilding /></el-icon>
              <el-icon class="dept-icon folder" v-else><Folder /></el-icon>
              <span class="dept-name">{{ data.name }}</span>
              <el-tag size="small" type="info" v-if="data.leader_name">负责人: {{ data.leader_name }}</el-tag>
            </div>
            <div class="node-actions">
              <el-button size="small" text @click.stop="showEditDialog(data)" v-if="canEdit">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button size="small" text type="danger" @click.stop="deleteDepartment(data)" v-if="canDelete && !data.children?.length">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </template>
      </el-tree>

      <!-- 空状态 -->
      <div class="empty-state" v-if="!loading && departments.length === 0">
        <el-icon :size="64"><OfficeBuilding /></el-icon>
        <p>暂无部门数据</p>
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑部门' : '新增部门'"
      width="450px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="部门名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入部门名称" />
        </el-form-item>
        <el-form-item label="上级部门" prop="parent_id">
          <el-cascader
            v-model="formData.parent_id"
            :options="departmentOptions"
            :props="{ value: 'id', label: 'name', children: 'children', checkStrictly: true, emitPath: false }"
            placeholder="选择上级部门（可选）"
            clearable
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="部门负责人" prop="leader_id">
          <el-select v-model="formData.leader_id" placeholder="选择负责人（可选）" clearable filterable style="width: 100%">
            <el-option
              v-for="emp in employees"
              :key="emp.id"
              :label="emp.name"
              :value="emp.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="formData.sort_order" :min="0" :max="999" />
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
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Edit, Delete, OfficeBuilding, Folder } from '@element-plus/icons-vue'
import { departmentApi, employeeApi, type Department, type Employee } from '../api'
import { useUserStore } from '../stores/user'
import { createFormRules } from '../utils/rules'

const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const departments = ref<Department[]>([])
const employees = ref<Employee[]>([])

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const canEdit = computed(() => userStore.hasPermission('employees', 'write'))
const canDelete = computed(() => userStore.hasPermission('employees', 'delete'))

const formData = ref({
  name: '',
  parent_id: null as number | null,
  leader_id: null as number | null,
  sort_order: 0
})

// 使用统一校验规则
const rules: FormRules = createFormRules({
  name: 'departmentName'
})

// 部门选项（用于上级部门选择，排除自己）
const departmentOptions = computed(() => {
  if (isEdit.value && editingId.value) {
    return filterDeptTree(departments.value, editingId.value)
  }
  return departments.value
})

function filterDeptTree(depts: Department[], excludeId: number): Department[] {
  return depts
    .filter(d => d.id !== excludeId)
    .map(d => ({
      ...d,
      children: d.children ? filterDeptTree(d.children, excludeId) : []
    }))
}

async function loadData() {
  loading.value = true
  try {
    const [deptRes, empRes] = await Promise.all([
      departmentApi.list(),
      employeeApi.list()
    ])

    if (deptRes.data.success) {
      departments.value = deptRes.data.data
    }

    if (empRes.data.success) {
      employees.value = empRes.data.data
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
    parent_id: null,
    leader_id: null,
    sort_order: 0
  }
  dialogVisible.value = true
}

function showEditDialog(dept: Department) {
  isEdit.value = true
  editingId.value = dept.id
  formData.value = {
    name: dept.name,
    parent_id: dept.parent_id,
    leader_id: dept.leader_id,
    sort_order: dept.sort_order || 0
  }
  dialogVisible.value = true
}

async function submitForm() {
  if (!formRef.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    const data: any = {
      name: formData.value.name,
      parent_id: formData.value.parent_id,
      leader_id: formData.value.leader_id,
      sort_order: formData.value.sort_order
    }

    if (isEdit.value) {
      const res = await departmentApi.update(editingId.value!, data)
      if (res.data.success) {
        ElMessage.success('更新成功')
        dialogVisible.value = false
        loadData()
      } else {
        ElMessage.error(res.data.error)
      }
    } else {
      const res = await departmentApi.create(data)
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

async function deleteDepartment(dept: Department) {
  try {
    await ElMessageBox.confirm(`确定删除部门「${dept.name}」？`, '删除确认', { type: 'warning' })
    const res = await departmentApi.delete(dept.id)
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
.department-page {
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

/* 部门树 */
.department-tree {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  padding: 16px;
  min-height: 400px;
}

.tree-node {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-right: 8px;
}

.node-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dept-icon {
  color: #409eff;
  font-size: 16px;
}

.dept-icon.folder {
  color: #e6a23c;
}

.dept-name {
  font-size: 14px;
  color: #303133;
}

.node-actions {
  display: flex;
  gap: 4px;
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

/* 树形组件样式调整 */
:deep(.el-tree-node__content) {
  height: 40px;
}

:deep(.el-tree-node__content:hover) {
  background: #f5f7fa;
}
</style>