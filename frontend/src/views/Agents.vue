<template>
  <div class="agents-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>Agent 管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog" :disabled="isRestarting">
          <el-icon><Plus /></el-icon>
          新建 Agent
        </el-button>
      </div>
    </div>

    <!-- Agent 列表 -->
    <el-card class="table-card" v-loading="loading || isRestarting" element-loading-text="Gateway 正在重启，请稍候...">
      <el-table :data="paginatedAgents" stripe>
        <el-table-column prop="id" label="ID" width="120" />
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column label="模型" width="200">
          <template #default="{ row }">
            <el-tag size="small">{{ row.modelName || row.model?.primary || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.default ? 'warning' : 'success'" size="small">
              {{ row.default ? '默认' : '活跃' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="workspace" label="工作空间" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showEditDialog(row)" :disabled="row.default || isRestarting">
              编辑
            </el-button>
            <el-button size="small" type="danger" @click="deleteAgent(row)" :disabled="row.default || isRestarting">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="agents.length"
          layout="total, sizes, prev, pager, next, jumper"
          background
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑 Agent' : '新建 Agent'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="Agent ID" v-if="!isEdit">
          <div class="id-preview">
            <span class="id-label">自动生成：</span>
            <span class="id-value">{{ generatedId || '(根据名称生成)' }}</span>
          </div>
          <div class="form-tip">ID 由名称自动生成，如名称 "MyAgent" → ID "myagent"</div>
        </el-form-item>
        <el-form-item label="Agent ID" v-if="isEdit">
          <el-input v-model="formData.id" disabled />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="formData.name" placeholder="例如：我的助手" :disabled="isRestarting" />
        </el-form-item>
        <el-form-item label="模型" prop="model">
          <el-select v-model="formData.modelId" placeholder="选择模型（可选）" style="width: 100%" clearable :disabled="isRestarting">
            <el-option
              v-for="model in models"
              :key="model.id"
              :label="model.name"
              :value="model.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="工作空间" prop="workspace" v-if="!isEdit">
          <el-input v-model="formData.workspace" :placeholder="`默认：~/.openclaw/workspace-${generatedId || 'id'}`" :disabled="isRestarting" />
        </el-form-item>
        <el-form-item label="工作空间" v-if="isEdit">
          <el-input v-model="formData.workspace" disabled />
        </el-form-item>
      </el-form>
      <template #footer>
        <!-- 编辑模式：单按钮"保存" -->
        <template v-if="isEdit">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitEdit" :loading="submitting">
            保存
          </el-button>
        </template>
        <!-- 创建模式：单按钮"创建"，会自动重启 -->
        <template v-else>
          <el-button @click="dialogVisible = false" :disabled="isRestarting">取消</el-button>
          <el-button type="primary" @click="submitCreate" :loading="submitting">
            创建
          </el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { agentApi, modelApi, type AgentConfig, type Model } from '../api'
import { createFormRules, sanitizeData } from '../utils/rules'

// 数据
const agents = ref<AgentConfig[]>([])
const models = ref<Model[]>([])
const loading = ref(false)
const submitting = ref(false)
const isRestarting = ref(false)  // Gateway 是否正在重启
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInstance>()

// 分页
const currentPage = ref(1)
const pageSize = ref(10)
const paginatedAgents = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return agents.value.slice(start, end)
})

// 表单数据
const formData = ref({
  id: '',
  name: '',
  modelId: '',
  workspace: ''
})

// 校验规则
const rules = createFormRules({
  id: 'agentId',
  name: 'displayName'
})

// 自动生成 ID（根据 name）
const generatedId = computed(() => {
  if (!formData.value.name) return ''
  // 模拟 Gateway 的 ID 生成逻辑：小写 + 移除特殊字符
  return formData.value.name
    .toLowerCase()
    .replace(/[^a-z0-9_]/g, '')
    .replace(/^[0-9]+/, '') // 不能以数字开头
})

// 加载数据
async function loadAgents() {
  loading.value = true
  try {
    const res = await agentApi.list()
    if (res.data.success) {
      agents.value = res.data.data
    }
  } catch (e: any) {
    ElMessage.error('加载失败：' + e.message)
  } finally {
    loading.value = false
  }
}

async function loadModels() {
  try {
    const res = await modelApi.list()
    if (res.data.success) {
      models.value = res.data.data
    }
  } catch (e) {
    console.error('加载模型失败', e)
  }
}

// 对话框
function showCreateDialog() {
  isEdit.value = false
  formData.value = {
    id: '',
    name: '',
    modelId: '',
    workspace: ''
  }
  dialogVisible.value = true
}

function showEditDialog(agent: AgentConfig) {
  isEdit.value = true
  formData.value = {
    id: agent.id,
    name: agent.name,
    modelId: agent.model?.primary || '',
    workspace: agent.workspace || ''
  }
  dialogVisible.value = true
}

// 提交表单 - 编辑（不重启）
async function submitEdit() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    const cleanData = sanitizeData({
      id: formData.value.id,
      name: formData.value.name,
      modelId: formData.value.modelId,
      workspace: formData.value.workspace
    })

    const updateData: any = {
      name: cleanData.name
    }
    if (cleanData.modelId) {
      updateData.model = cleanData.modelId  // agents.update 需要字符串
    }
    if (cleanData.workspace) {
      updateData.workspace = cleanData.workspace
    }

    const res = await agentApi.update(cleanData.id, updateData)
    if (res.data.success) {
      ElMessage.success('保存成功')
      dialogVisible.value = false
      loadAgents()
    } else {
      ElMessage.error(res.data.error || '保存失败')
    }
  } catch (e: any) {
    ElMessage.error('操作失败：' + e.message)
  } finally {
    submitting.value = false
  }
}

// 提交表单 - 创建（会自动重启 Gateway）
async function submitCreate() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  // 先弹出确认框
  try {
    await ElMessageBox.confirm(
      '创建 Agent 将会自动重启 Gateway，预计需要 10-30 秒。是否继续？',
      '创建确认',
      {
        type: 'warning',
        confirmButtonText: '确定创建',
        cancelButtonText: '取消'
      }
    )
  } catch {
    return // 用户取消
  }

  submitting.value = true
  isRestarting.value = true  // 开始重启，禁用界面
  const loadingMsg = ElMessage({
    message: '正在创建 Agent 并重启 Gateway，请稍候...',
    type: 'info',
    duration: 0,
    showClose: false
  })

  try {
    const cleanData = sanitizeData({
      name: formData.value.name,
      workspace: formData.value.workspace,
      modelId: formData.value.modelId
    })

    // 创建参数：name + workspace + model（后端会在创建后设置）
    // workspace 默认格式：~/.openclaw/workspace-<agentId>
    const createData: any = {
      name: cleanData.name,
      workspace: cleanData.workspace || `~/.openclaw/workspace-${generatedId.value || cleanData.name.toLowerCase()}`
    }
    if (cleanData.modelId) {
      createData.model = { primary: cleanData.modelId }
    }

    const res = await agentApi.create(createData)
    loadingMsg.close()

    if (res.data.success) {
      ElMessage.success(res.data.message || '创建成功')
      dialogVisible.value = false
      loadAgents()
    } else {
      ElMessage.error(res.data.error || '创建失败')
    }
  } catch (e: any) {
    loadingMsg.close()
    ElMessage.error('创建失败：' + e.message)
  } finally {
    submitting.value = false
    isRestarting.value = false  // 重启完成，恢复界面
  }
}

// 删除 Agent
async function deleteAgent(agent: AgentConfig) {
  try {
    await ElMessageBox.confirm(
      `确定删除 Agent "${agent.name}" 吗？`,
      '删除确认',
      { type: 'warning' }
    )

    const res = await agentApi.delete(agent.id)
    if (res.data.success) {
      ElMessage.success('删除成功')
      loadAgents()
    } else {
      ElMessage.error(res.data.error || '删除失败')
    }
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败：' + e.message)
    }
  }
}

onMounted(() => {
  loadAgents()
  loadModels()
})
</script>

<style scoped>
.agents-page {
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

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.id-preview {
  display: flex;
  align-items: center;
  gap: 8px;
}

.id-label {
  color: #606266;
  font-size: 14px;
}

.id-value {
  font-family: monospace;
  font-size: 14px;
  color: #303133;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
}
</style>