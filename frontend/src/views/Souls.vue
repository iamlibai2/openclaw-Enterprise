<template>
  <div class="souls-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>灵魂管理</h1>
      <p class="page-desc">管理每个 Agent 的灵魂配置文件，支持手动编辑或选择预置模板</p>
    </div>

    <!-- Agent 列表 -->
    <div class="agents-section">
      <div class="section-title">选择 Agent</div>
      <div class="agent-tabs">
        <div
          class="agent-tab"
          v-for="agent in agents"
          :key="agent.id"
          :class="{ active: currentAgent?.id === agent.id }"
          @click="selectAgent(agent)"
        >
          <div class="tab-avatar" :style="{ background: getAvatarColor(agents.indexOf(agent)) }">
            {{ agent.name?.charAt(0) || agent.id.charAt(0) }}
          </div>
          <div class="tab-info">
            <span class="tab-name">{{ agent.name }}</span>
            <span class="tab-id">@{{ agent.id }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 配置文件区域 -->
    <div class="config-section" v-if="currentAgent">
      <div class="config-header">
        <h3>{{ currentAgent.name }} 的灵魂配置</h3>
        <span class="file-count">{{ configFiles.length }} 个文件</span>
      </div>

      <div class="config-container" v-loading="loadingFiles">
        <!-- 文件列表 -->
        <div class="file-list">
          <div
            class="file-item"
            v-for="file in configFiles"
            :key="file.id"
            :class="{ active: currentFile?.id === file.id }"
            @click="selectFile(file)"
          >
            <div class="file-icon">{{ getFileIcon(file.fileType) }}</div>
            <div class="file-info">
              <div class="file-name">{{ file.fileName }}</div>
              <div class="file-desc">{{ getFileDesc(file.fileType) }}</div>
            </div>
            <div class="file-meta">
              <span class="file-size">{{ formatSize(file.size) }}</span>
            </div>
          </div>
        </div>

        <!-- 编辑区域 -->
        <div class="editor-area">
          <template v-if="currentFile">
            <div class="editor-header">
              <div class="editor-title-row">
                <span class="editor-title">{{ currentFile.fileName }}</span>
                <el-button size="small" text @click="showTemplatePanel = !showTemplatePanel">
                  <el-icon><Collection /></el-icon>
                  {{ showTemplatePanel ? '隐藏模板' : '选择模板' }}
                </el-button>
              </div>
              <div class="editor-actions">
                <el-button size="small" @click="saveFile" :loading="saving" :disabled="!hasChanges" type="primary">
                  <el-icon><Check /></el-icon>
                  保存
                </el-button>
              </div>
            </div>

            <!-- 模板选择面板 -->
            <div class="template-panel" v-if="showTemplatePanel">
              <div class="panel-header">
                <span>预置模板</span>
                <span class="template-hint">点击模板可直接替换当前内容</span>
              </div>
              <div class="template-list" v-loading="loadingTemplates">
                <div
                  class="template-item"
                  v-for="template in templates"
                  :key="template.id"
                  @click="applyTemplate(template)"
                >
                  <div class="template-info">
                    <span class="template-name">{{ template.name }}</span>
                    <span class="template-desc">{{ template.description }}</span>
                  </div>
                  <el-button size="small" text type="primary">应用</el-button>
                </div>
                <div class="empty-templates" v-if="templates.length === 0 && !loadingTemplates">
                  暂无该类型的预置模板
                </div>
              </div>
            </div>

            <textarea
              v-model="fileContent"
              class="code-editor"
              placeholder="文件内容"
            ></textarea>
          </template>
          <template v-else>
            <div class="empty-editor">
              <el-icon :size="48"><Document /></el-icon>
              <p>选择一个配置文件开始编辑</p>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div class="empty-state" v-else>
      <el-icon :size="64"><MagicStick /></el-icon>
      <p>选择一个 Agent 查看其灵魂配置</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Check, MagicStick, Collection } from '@element-plus/icons-vue'
import { agentApi, configFileApi, type AgentConfig } from '../api'

interface ConfigFile {
  id: string
  agentId: string
  agentName: string
  fileName: string
  fileType: string
  path: string
  size: number
  modifiedAt: string
}

interface Template {
  id: string
  name: string
  description: string
  content: string
}

const agents = ref<AgentConfig[]>([])
const currentAgent = ref<AgentConfig | null>(null)
const configFiles = ref<ConfigFile[]>([])
const currentFile = ref<ConfigFile | null>(null)
const fileContent = ref('')
const originalContent = ref('')
const loadingFiles = ref(false)
const saving = ref(false)

// 模板相关
const showTemplatePanel = ref(false)
const templates = ref<Template[]>([])
const loadingTemplates = ref(false)

const hasChanges = computed(() => fileContent.value !== originalContent.value)

const avatarColors = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
]

const fileTypeConfig: Record<string, { icon: string; desc: string }> = {
  'SOUL': { icon: '💫', desc: '灵魂 - 性格与行为准则' },
  'IDENTITY': { icon: '🎭', desc: '身份 - 名称与角色设定' },
  'AGENTS': { icon: '🏠', desc: '工作空间 - 启动流程与记忆' },
  'TOOLS': { icon: '🔧', desc: '工具 - 工具使用说明' },
  'USER': { icon: '👤', desc: '用户 - 服务对象信息' },
  'HEARTBEAT': { icon: '💓', desc: '心跳 - 定时任务配置' }
}

function getAvatarColor(index: number): string {
  return avatarColors[index % avatarColors.length]
}

function getFileIcon(fileType: string): string {
  return fileTypeConfig[fileType]?.icon || '📄'
}

function getFileDesc(fileType: string): string {
  return fileTypeConfig[fileType]?.desc || '配置文件'
}

function formatSize(size: number): string {
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
  return (size / 1024 / 1024).toFixed(1) + ' MB'
}

async function loadAgents() {
  try {
    const res = await agentApi.list()
    if (res.data.success) {
      agents.value = res.data.data
    }
  } catch (e: any) {
    ElMessage.error('加载 Agent 列表失败')
  }
}

async function selectAgent(agent: AgentConfig) {
  if (hasChanges.value) {
    try {
      await ElMessageBox.confirm('当前文件未保存，是否放弃修改？', '提示', { type: 'warning' })
    } catch {
      return
    }
  }

  currentAgent.value = agent
  currentFile.value = null
  fileContent.value = ''
  originalContent.value = ''
  configFiles.value = []
  showTemplatePanel.value = false

  loadingFiles.value = true
  try {
    const res = await configFileApi.list()
    if (res.data.success) {
      configFiles.value = res.data.data.filter((f: ConfigFile) => f.agentId === agent.id)
    }
  } catch (e: any) {
    ElMessage.error('加载配置文件失败')
  } finally {
    loadingFiles.value = false
  }
}

async function selectFile(file: ConfigFile) {
  if (hasChanges.value) {
    try {
      await ElMessageBox.confirm('当前文件未保存，是否放弃修改？', '提示', { type: 'warning' })
    } catch {
      return
    }
  }

  currentFile.value = file
  fileContent.value = ''
  originalContent.value = ''
  showTemplatePanel.value = false

  try {
    const res = await configFileApi.get(file.id)
    if (res.data.success) {
      fileContent.value = res.data.data.content
      originalContent.value = res.data.data.content
    }
  } catch (e: any) {
    ElMessage.error('加载文件内容失败')
  }
}

async function loadTemplates(fileType: string) {
  loadingTemplates.value = true
  templates.value = []
  try {
    const res = await configFileApi.templates(fileType)
    if (res.data.success) {
      templates.value = res.data.data
    }
  } catch (e: any) {
    ElMessage.error('加载模板失败')
  } finally {
    loadingTemplates.value = false
  }
}

async function applyTemplate(template: Template) {
  try {
    await ElMessageBox.confirm(
      `确定要应用「${template.name}」模板吗？这将替换当前内容。`,
      '应用模板',
      { type: 'warning' }
    )

    // 替换模板中的 {{name}} 为当前 Agent 名称
    let content = template.content
    if (currentAgent.value) {
      content = content.replace(/\{\{name\}\}/g, currentAgent.value.name)
    }

    fileContent.value = content
    ElMessage.success('已应用模板，点击保存生效')
  } catch {
    // 用户取消
  }
}

async function saveFile() {
  if (!currentFile.value || !hasChanges.value) return

  saving.value = true
  try {
    const res = await configFileApi.update(currentFile.value.id, fileContent.value)
    if (res.data.success) {
      ElMessage.success('保存成功')
      originalContent.value = fileContent.value
    } else {
      ElMessage.error(res.data.error)
    }
  } catch (e: any) {
    ElMessage.error('保存失败：' + e.message)
  } finally {
    saving.value = false
  }
}

// 监听文件变化，加载对应模板
watch(currentFile, (file) => {
  if (file) {
    loadTemplates(file.fileType)
  } else {
    templates.value = []
    showTemplatePanel.value = false
  }
})

onMounted(() => {
  loadAgents()
})
</script>

<style scoped>
.souls-page {
  min-height: calc(100vh - 96px);
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.page-desc {
  font-size: 14px;
  color: #909399;
}

/* Agent 选择区 */
.agents-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 12px;
}

.agent-tabs {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.agent-tab {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 180px;
}

.agent-tab:hover {
  border-color: #c0c4cc;
}

.agent-tab.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.tab-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
}

.tab-info {
  display: flex;
  flex-direction: column;
}

.tab-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.tab-id {
  font-size: 12px;
  color: #909399;
}

/* 配置区域 */
.config-section {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.config-header {
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.file-count {
  font-size: 12px;
  color: #909399;
}

.config-container {
  display: flex;
  min-height: 500px;
}

/* 文件列表 */
.file-list {
  width: 280px;
  border-right: 1px solid #ebeef5;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f5f5f5;
  transition: background 0.2s;
}

.file-item:hover {
  background: #f5f7fa;
}

.file-item.active {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.file-icon {
  font-size: 24px;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.file-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.file-meta {
  text-align: right;
}

.file-size {
  font-size: 12px;
  color: #c0c4cc;
}

/* 编辑区域 */
.editor-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.editor-header {
  padding: 12px 20px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.editor-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.editor-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

/* 模板面板 */
.template-panel {
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;
}

.panel-header {
  padding: 12px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 500;
  color: #606266;
}

.template-hint {
  font-size: 12px;
  font-weight: normal;
  color: #909399;
}

.template-list {
  padding: 0 20px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.template-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.template-item:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.template-info {
  display: flex;
  flex-direction: column;
}

.template-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.template-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.empty-templates {
  padding: 20px;
  text-align: center;
  color: #909399;
  font-size: 14px;
}

.code-editor {
  flex: 1;
  padding: 16px 20px;
  border: none;
  outline: none;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 14px;
  line-height: 1.6;
  resize: none;
  background: #fafafa;
}

.code-editor:focus {
  background: #fff;
}

.empty-editor {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
}

.empty-editor p {
  margin-top: 16px;
  font-size: 14px;
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