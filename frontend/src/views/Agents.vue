<template>
  <div class="agents-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>Agent 管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog">
          <el-icon><Plus /></el-icon>
          新建 Agent
        </el-button>
        <el-button type="success" @click="applyConfig" :loading="applying">
          <el-icon><Refresh /></el-icon>
          应用配置
        </el-button>
      </div>
    </div>

    <!-- Agent 列表 -->
    <el-card class="table-card">
      <el-table :data="agents" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="120" />
        <el-table-column prop="name" label="名称" width="150" />
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
            <el-button size="small" @click="showEditDialog(row)" :disabled="row.default">
              编辑
            </el-button>
            <el-button size="small" type="danger" @click="deleteAgent(row)" :disabled="row.default">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑 Agent' : '新建 Agent'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="Agent ID" prop="id" v-if="!isEdit">
          <el-input v-model="formData.id" placeholder="例如：my-agent" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="formData.name" placeholder="例如：我的助手" />
        </el-form-item>
        <el-form-item label="模型" prop="model">
          <el-select v-model="formData.modelId" placeholder="选择模型" style="width: 100%">
            <el-option
              v-for="model in models"
              :key="model.id"
              :label="model.name"
              :value="model.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="工作空间">
          <el-input v-model="formData.workspace" placeholder="默认自动生成" />
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
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { agentApi, modelApi, type AgentConfig, type Model } from '../api'
import { createFormRules, sanitizeData } from '../utils/rules'

// 数据
const agents = ref<AgentConfig[]>([])
const models = ref<Model[]>([])
const loading = ref(false)
const applying = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const formRef = ref<FormInstance>()

// 表单数据
const formData = ref({
  id: '',
  name: '',
  modelId: '',
  workspace: ''
})

// 使用统一校验规则
const rules = createFormRules({
  id: 'agentIdLower',
  name: 'agentName',
  modelId: 'modelSelect'
})

// 加载 Agent 列表
async function loadAgents() {
  loading.value = true
  try {
    const res = await agentApi.list()
    if (res.data.success) {
      agents.value = res.data.data
      models.value = res.data.models || []
    } else {
      ElMessage.error(res.data.error)
    }
  } catch (e: any) {
    ElMessage.error('加载失败：' + e.message)
  } finally {
    loading.value = false
  }
}

// 显示创建对话框
function showCreateDialog() {
  isEdit.value = false
  formData.value = {
    id: '',
    name: '',
    modelId: models.value[0]?.id || 'bailian/qwen3.5-plus',
    workspace: ''
  }
  dialogVisible.value = true
}

// 显示编辑对话框
function showEditDialog(agent: AgentConfig) {
  isEdit.value = true
  editingId.value = agent.id
  formData.value = {
    id: agent.id,
    name: agent.name,
    modelId: agent.model?.primary || '',
    workspace: agent.workspace || ''
  }
  dialogVisible.value = true
}

// 提交表单
async function submitForm() {
  if (!formRef.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    // 清理输入数据
    const cleanedData = sanitizeData({
      id: formData.value.id,
      name: formData.value.name,
      modelId: formData.value.modelId,
      workspace: formData.value.workspace
    })

    const data: any = {
      name: cleanedData.name,
      model: { primary: cleanedData.modelId }
    }

    if (!isEdit.value) {
      data.id = cleanedData.id
      if (cleanedData.workspace) {
        data.workspace = cleanedData.workspace
      }
    } else {
      if (cleanedData.workspace) {
        data.workspace = cleanedData.workspace
      }
    }

    if (isEdit.value) {
      const res = await agentApi.update(editingId.value, data)
      if (res.data.success) {
        ElMessage.success('更新成功')
        dialogVisible.value = false
        loadAgents()
      } else {
        ElMessage.error(res.data.error)
      }
    } else {
      const res = await agentApi.create(data)
      if (res.data.success) {
        ElMessage.success('创建成功')
        dialogVisible.value = false
        loadAgents()
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

// 删除 Agent
async function deleteAgent(agent: AgentConfig) {
  try {
    await ElMessageBox.confirm(
      `确定删除 Agent "${agent.name}" (${agent.id})？`,
      '删除确认',
      { type: 'warning' }
    )

    const res = await agentApi.delete(agent.id)
    if (res.data.success) {
      ElMessage.success('删除成功')
      loadAgents()
    } else {
      ElMessage.error(res.data.error)
    }
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败：' + e.message)
    }
  }
}

// 应用配置
async function applyConfig() {
  applying.value = true
  try {
    const res = await agentApi.apply()
    if (res.data.success) {
      ElMessage.success('配置已应用，Gateway 已重启')
    } else {
      ElMessage.error(res.data.error)
    }
  } catch (e: any) {
    ElMessage.error('应用失败：' + e.message)
  } finally {
    applying.value = false
  }
}

// 初始化
onMounted(() => {
  loadAgents()
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
</style>
