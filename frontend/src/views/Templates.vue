<template>
  <div class="templates-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>模板管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog" v-if="canEdit">
          <el-icon><Plus /></el-icon>
          新增模板
        </el-button>
      </div>
    </div>

    <!-- 类型筛选 -->
    <div class="filter-bar">
      <span class="filter-label">文件类型：</span>
      <el-radio-group v-model="filterType" @change="loadTemplates">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="SOUL">SOUL.md</el-radio-button>
        <el-radio-button label="IDENTITY">IDENTITY.md</el-radio-button>
        <el-radio-button label="AGENTS">AGENTS.md</el-radio-button>
        <el-radio-button label="TOOLS">TOOLS.md</el-radio-button>
        <el-radio-button label="USER">USER.md</el-radio-button>
        <el-radio-button label="HEARTBEAT">HEARTBEAT.md</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 模板列表 -->
    <div class="templates-grid" v-loading="loading">
      <div
        class="template-card"
        v-for="template in templates"
        :key="template.id"
      >
        <div class="card-header">
          <div class="template-icon">{{ getFileIcon(template.fileType) }}</div>
          <el-tag size="small" v-if="template.isBuiltin" type="info">内置</el-tag>
          <el-tag size="small" v-else type="success">自定义</el-tag>
        </div>
        <div class="card-body">
          <h3 class="template-name">{{ template.name }}</h3>
          <p class="template-desc">{{ template.description || '暂无描述' }}</p>
          <div class="template-type">{{ template.fileType }}.md</div>
        </div>
        <div class="card-footer">
          <el-button size="small" @click="viewTemplate(template)">
            <el-icon><View /></el-icon>
            查看
          </el-button>
          <el-button size="small" @click="editTemplate(template)" v-if="canEdit">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
          <el-button
            size="small"
            type="danger"
            @click="deleteTemplate(template)"
            v-if="canEdit && !template.isBuiltin"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div class="empty-state" v-if="!loading && templates.length === 0">
      <el-icon :size="64"><Document /></el-icon>
      <p>暂无模板</p>
    </div>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑模板' : '新增模板'"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="模板ID" prop="id" v-if="!isEdit">
          <el-input v-model="formData.id" placeholder="例如：soul-custom" />
        </el-form-item>
        <el-form-item label="模板名称" prop="name">
          <el-input v-model="formData.name" placeholder="模板显示名称" />
        </el-form-item>
        <el-form-item label="文件类型" prop="fileType">
          <el-select v-model="formData.fileType" placeholder="选择类型" style="width: 100%">
            <el-option label="SOUL.md - 灵魂配置" value="SOUL" />
            <el-option label="IDENTITY.md - 身份配置" value="IDENTITY" />
            <el-option label="AGENTS.md - 工作空间配置" value="AGENTS" />
            <el-option label="TOOLS.md - 工具配置" value="TOOLS" />
            <el-option label="USER.md - 用户配置" value="USER" />
            <el-option label="HEARTBEAT.md - 心跳配置" value="HEARTBEAT" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="formData.description" placeholder="模板用途说明" />
        </el-form-item>
        <el-form-item label="模板内容" prop="content">
          <textarea
            v-model="formData.content"
            class="content-editor"
            placeholder="Markdown 格式的模板内容，可使用 {{name}} 作为 Agent 名称占位符"
          ></textarea>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 查看对话框 -->
    <el-dialog
      v-model="viewDialogVisible"
      :title="viewTemplate_data?.name"
      width="700px"
    >
      <div class="view-content">
        <div class="view-meta">
          <span>类型：{{ viewTemplate_data?.fileType }}.md</span>
          <span v-if="viewTemplate_data?.isBuiltin">（内置模板）</span>
        </div>
        <div class="view-desc" v-if="viewTemplate_data?.description">
          {{ viewTemplate_data?.description }}
        </div>
        <pre class="view-code">{{ viewTemplate_data?.content }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { Plus, View, Edit, Delete, Document } from '@element-plus/icons-vue'
import { configFileApi, type TemplateParams } from '../api'
import { createFormRules, sanitizeData } from '../utils/rules'
import { useUserStore } from '../stores/user'

interface Template {
  id: string
  name: string
  description: string
  fileType: string
  isBuiltin: boolean
}

interface TemplateDetail extends Template {
  content: string
}

const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const templates = ref<Template[]>([])
const filterType = ref('')

const canEdit = computed(() => userStore.hasPermission('config', 'write'))

// 对话框
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const formRef = ref<FormInstance>()
const formData = ref<TemplateParams>({
  id: '',
  name: '',
  description: '',
  fileType: 'SOUL',
  content: ''
})

// 使用统一校验规则
const rules = createFormRules({
  id: 'templateId',
  name: 'templateName',
  fileType: 'templateFileType',
  content: 'templateContent'
})

// 查看对话框
const viewDialogVisible = ref(false)
const viewTemplate_data = ref<TemplateDetail | null>(null)

const fileTypeIcons: Record<string, string> = {
  'SOUL': '💫',
  'IDENTITY': '🎭',
  'AGENTS': '🏠',
  'TOOLS': '🔧',
  'USER': '👤',
  'HEARTBEAT': '💓'
}

function getFileIcon(fileType: string): string {
  return fileTypeIcons[fileType] || '📄'
}

async function loadTemplates() {
  loading.value = true
  try {
    const res = await configFileApi.templates(filterType.value)
    if (res.data.success) {
      templates.value = res.data.data
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
    id: '',
    name: '',
    description: '',
    fileType: filterType.value || 'SOUL',
    content: ''
  }
  dialogVisible.value = true
}

async function viewTemplate(template: Template) {
  try {
    const res = await configFileApi.getTemplate(template.id)
    if (res.data.success) {
      viewTemplate_data.value = res.data.data
      viewDialogVisible.value = true
    }
  } catch (e: any) {
    ElMessage.error('加载模板失败')
  }
}

async function editTemplate(template: Template) {
  try {
    const res = await configFileApi.getTemplate(template.id)
    if (res.data.success) {
      isEdit.value = true
      editingId.value = template.id
      formData.value = {
        id: template.id,
        name: res.data.data.name,
        description: res.data.data.description,
        fileType: res.data.data.fileType,
        content: res.data.data.content
      }
      dialogVisible.value = true
    }
  } catch (e: any) {
    ElMessage.error('加载模板失败')
  }
}

async function submitForm() {
  if (!formRef.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    // 清理输入数据
    const cleanedData = sanitizeData(formData.value)

    if (isEdit.value) {
      const res = await configFileApi.updateTemplate(editingId.value, {
        name: cleanedData.name,
        description: cleanedData.description,
        content: cleanedData.content
      })
      if (res.data.success) {
        ElMessage.success('更新成功')
        dialogVisible.value = false
        loadTemplates()
      } else {
        ElMessage.error(res.data.error)
      }
    } else {
      const res = await configFileApi.createTemplate(cleanedData)
      if (res.data.success) {
        ElMessage.success('创建成功')
        dialogVisible.value = false
        loadTemplates()
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

async function deleteTemplate(template: Template) {
  try {
    await ElMessageBox.confirm(`确定删除模板「${template.name}」？`, '删除确认', { type: 'warning' })
    const res = await configFileApi.deleteTemplate(template.id)
    if (res.data.success) {
      ElMessage.success('删除成功')
      loadTemplates()
    } else {
      ElMessage.error(res.data.error)
    }
  } catch {
    // 用户取消
  }
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.templates-page {
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

/* 筛选栏 */
.filter-bar {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.filter-label {
  font-size: 14px;
  color: #606266;
  margin-right: 12px;
}

/* 模板网格 */
.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.template-card {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  overflow: hidden;
  transition: all 0.3s;
}

.template-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  padding: 16px 16px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.template-icon {
  font-size: 28px;
}

.card-body {
  padding: 0 16px 16px;
}

.template-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.template-desc {
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
  margin-bottom: 12px;
  min-height: 40px;
}

.template-type {
  font-size: 12px;
  color: #409eff;
  font-family: monospace;
}

.card-footer {
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* 内容编辑器 */
.content-editor {
  width: 100%;
  min-height: 300px;
  padding: 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: vertical;
}

.content-editor:focus {
  outline: none;
  border-color: #409eff;
}

/* 查看内容 */
.view-content {
  padding: 0 20px;
}

.view-meta {
  font-size: 14px;
  color: #606266;
  margin-bottom: 12px;
}

.view-desc {
  font-size: 14px;
  color: #909399;
  margin-bottom: 16px;
}

.view-code {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 6px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 400px;
  overflow-y: auto;
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