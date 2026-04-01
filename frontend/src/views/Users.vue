<template>
  <div class="users-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>用户管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog" v-if="canCreate">
          <el-icon><Plus /></el-icon>
          新建用户
        </el-button>
      </div>
    </div>

    <!-- 用户列表 -->
    <el-card class="table-card">
      <el-table :data="users" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="display_name" label="显示名称" width="150" />
        <el-table-column prop="email" label="邮箱" width="180" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role_name === 'admin' ? 'danger' : 'primary'" size="small">
              {{ row.role_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '活跃' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login" label="最后登录" width="180" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showEditDialog(row)" :disabled="row.id === 1 && !userStore.isAdmin">
              编辑
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="deleteUser(row)"
              :disabled="row.id === 1 || row.id === userStore.user?.id"
              v-if="canDelete"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑用户' : '新建用户'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="用户名" prop="username" v-if="!isEdit">
          <el-input v-model="formData.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="!isEdit">
          <el-input v-model="formData.password" type="password" placeholder="至少6位" show-password />
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="formData.display_name" placeholder="用户显示名称" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="formData.email" placeholder="用户邮箱" />
        </el-form-item>
        <el-form-item label="角色" prop="role_id">
          <el-select v-model="formData.role_id" placeholder="选择角色" style="width: 100%">
            <el-option
              v-for="role in roles"
              :key="role.id"
              :label="role.description"
              :value="role.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" v-if="isEdit">
          <el-switch v-model="formData.is_active" />
        </el-form-item>
        <el-form-item label="新密码" v-if="isEdit">
          <el-input v-model="formData.new_password" type="password" placeholder="不修改请留空" show-password />
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
import { userApi, roleApi, type User, type Role } from '../api'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const users = ref<User[]>([])
const roles = ref<Role[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(0)
const formRef = ref<FormInstance>()

const canCreate = computed(() => userStore.hasPermission('users', 'write'))
const canDelete = computed(() => userStore.hasPermission('users', 'delete'))

const formData = ref({
  username: '',
  password: '',
  display_name: '',
  email: '',
  role_id: 3,
  is_active: true,
  new_password: ''
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名3-50位', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  role_id: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
}

async function loadData() {
  loading.value = true
  try {
    const [usersRes, rolesRes] = await Promise.all([
      userApi.list(),
      roleApi.list()
    ])
    if (usersRes.data.success) {
      users.value = usersRes.data.data
    }
    if (rolesRes.data.success) {
      roles.value = rolesRes.data.data
    }
  } catch (e: any) {
    ElMessage.error('加载失败：' + e.message)
  } finally {
    loading.value = false
  }
}

function showCreateDialog() {
  isEdit.value = false
  formData.value = {
    username: '',
    password: '',
    display_name: '',
    email: '',
    role_id: 3,
    is_active: true,
    new_password: ''
  }
  dialogVisible.value = true
}

function showEditDialog(user: User) {
  isEdit.value = true
  editingId.value = user.id
  const roleId = roles.value.find(r => r.name === user.role_name)?.id || 3
  formData.value = {
    username: user.username,
    password: '',
    display_name: user.display_name || '',
    email: user.email || '',
    role_id: roleId,
    is_active: user.is_active,
    new_password: ''
  }
  dialogVisible.value = true
}

async function submitForm() {
  if (!formRef.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    const data: any = {
      display_name: formData.value.display_name,
      email: formData.value.email,
      role_id: formData.value.role_id
    }

    if (isEdit.value) {
      data.is_active = formData.value.is_active
      if (formData.value.new_password) {
        data.password = formData.value.new_password
      }
      const res = await userApi.update(editingId.value, data)
      if (res.data.success) {
        ElMessage.success('更新成功')
        dialogVisible.value = false
        loadData()
      } else {
        ElMessage.error(res.data.error)
      }
    } else {
      data.username = formData.value.username
      data.password = formData.value.password
      const res = await userApi.create(data)
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

async function deleteUser(user: User) {
  try {
    await ElMessageBox.confirm(
      `确定删除用户 "${user.display_name}" (${user.username})？`,
      '删除确认',
      { type: 'warning' }
    )

    const res = await userApi.delete(user.id)
    if (res.data.success) {
      ElMessage.success('删除成功')
      loadData()
    } else {
      ElMessage.error(res.data.error)
    }
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败：' + e.message)
    }
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.users-page {
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
</style>