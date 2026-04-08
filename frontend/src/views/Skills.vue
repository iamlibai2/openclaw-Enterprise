<template>
  <div class="skills-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>Skill 管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog" v-if="canEdit">
          <el-icon><Plus /></el-icon>
          创建 Skill
        </el-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <!-- Agent 选择面板 -->
      <div class="filter-item">
        <span class="filter-label">员工：</span>
        <el-popover
          placement="bottom"
          :width="320"
          trigger="click"
          v-model:visible="agentPopoverVisible"
        >
          <template #reference>
            <el-button class="agent-select-btn">
              <div class="selected-agent" v-if="selectedAgentInfo">
                <el-avatar :size="24" :src="selectedAgentInfo.avatar" class="agent-avatar">
                  {{ selectedAgentInfo.name.charAt(0) }}
                </el-avatar>
                <span class="agent-name">{{ selectedAgentInfo.name }}</span>
                <span class="agent-count">{{ selectedAgentInfo.skills.length }}</span>
              </div>
              <span v-else class="placeholder">选择员工</span>
              <el-icon class="arrow"><ArrowDown /></el-icon>
            </el-button>
          </template>
          <!-- Agent 面板 -->
          <div class="agent-panel">
            <div class="agent-grid">
              <div
                class="agent-item"
                v-for="agent in agentsData"
                :key="agent.id"
                :class="{ active: selectedAgent === agent.id }"
                @click="selectAgent(agent.id)"
              >
                <el-avatar :size="40" :src="agent.avatar" class="agent-avatar">
                  {{ agent.name.charAt(0) }}
                </el-avatar>
                <div class="agent-info">
                  <span class="agent-name">{{ agent.name }}</span>
                  <span class="agent-id">@{{ agent.id }}</span>
                  <span class="agent-skills">{{ agent.skills.length }} skills</span>
                </div>
              </div>
            </div>
          </div>
        </el-popover>
      </div>
      <!-- 搜索框 -->
      <div class="filter-item">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索 Skill 名称/描述"
          style="width: 200px"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
      <!-- 级别筛选 -->
      <div class="filter-item">
        <span class="filter-label">级别：</span>
        <el-radio-group v-model="filterLevel">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="workspace">Workspace</el-radio-button>
          <el-radio-button label="shared">Shared</el-radio-button>
          <el-radio-button label="bundled">Bundled</el-radio-button>
        </el-radio-group>
      </div>
      <!-- 统计信息 -->
      <div class="filter-stats" v-if="selectedAgent">
        <el-tag type="info">
          {{ displayedSkills.length }} 个 Skill
        </el-tag>
      </div>
    </div>

    <!-- Skill 卡片网格 -->
    <div class="skills-section" v-loading="loading">
      <div class="skills-grid" v-if="displayedSkills.length > 0">
        <div
          class="skill-card"
          v-for="skill in displayedSkills"
          :key="skill.slug + '-' + skill.agentId"
          :class="['card-level-' + skill.level]"
        >
          <div class="card-header">
            <div class="skill-icon">{{ getSkillIcon(skill) }}</div>
            <div class="skill-title">
              <span class="skill-name">{{ skill.name }}</span>
              <el-tag size="small" :type="getLevelType(skill.level)">{{ skill.level }}</el-tag>
            </div>
          </div>
          <div class="card-body">
            <p class="skill-desc">{{ skill.description || '暂无描述' }}</p>
            <div class="skill-meta">
              <span v-if="skill.version" class="version">v{{ skill.version }}</span>
              <el-tag v-if="skill.userInvocable" size="small" type="success">可调用</el-tag>
              <span class="requires-text" v-if="getRequires(skill)">{{ getRequires(skill) }}</span>
            </div>
          </div>
          <div class="card-footer">
            <el-switch
              v-model="skill.enabled"
              @change="toggleSkill(skill)"
              :loading="skill.toggling"
              :disabled="skill.toggling"
              v-if="canToggle"
            />
            <div class="actions">
              <el-button size="small" text @click="viewSkill(skill)">
                <el-icon><View /></el-icon>
              </el-button>
              <el-button size="small" text @click="editSkill(skill)" v-if="canEdit && skill.canEdit">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button size="small" text type="danger" @click="deleteSkill(skill)" v-if="canDelete && skill.canDelete">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div class="empty-state" v-else-if="!loading">
        <el-icon :size="64"><Document /></el-icon>
        <p v-if="!selectedAgent">请选择一个员工查看 Skills</p>
        <p v-else-if="filterLevel">该员工没有 {{ filterLevel }} 级别的 Skill</p>
        <p v-else>该员工暂无 Skill</p>
      </div>
    </div>

    <!-- 查看 Skill 详情对话框 -->
    <el-dialog
      v-model="viewDialogVisible"
      :title="viewingSkill?.name"
      width="800px"
      class="skill-detail-dialog"
    >
      <div class="skill-detail" v-if="viewingSkill">
        <div class="detail-header">
          <div class="meta-row">
            <span class="meta-label">级别：</span>
            <el-tag :type="getLevelType(viewingSkill.level)">{{ viewingSkill.level }}</el-tag>
          </div>
          <div class="meta-row" v-if="viewingSkill.version">
            <span class="meta-label">版本：</span>
            <span>v{{ viewingSkill.version }}</span>
          </div>
          <div class="meta-row" v-if="viewingSkill.agentName">
            <span class="meta-label">所属员工：</span>
            <span>{{ viewingSkill.agentName }}</span>
          </div>
        </div>

        <el-divider content-position="left">SKILL.md 内容</el-divider>
        <div class="skill-content" v-html="renderedContent"></div>

        <el-divider content-position="left" v-if="viewingSkill.metadata?.openclaw?.requires">依赖要求</el-divider>
        <div class="requires-info" v-if="viewingSkill.metadata?.openclaw?.requires">
          <div v-if="viewingSkill.metadata.openclaw.requires.bins?.length">
            <strong>二进制：</strong>
            <el-tag v-for="bin in viewingSkill.metadata.openclaw.requires.bins" :key="bin" size="small" class="req-tag">{{ bin }}</el-tag>
          </div>
          <div v-if="viewingSkill.metadata.openclaw.requires.env?.length">
            <strong>环境变量：</strong>
            <el-tag v-for="env in viewingSkill.metadata.openclaw.requires.env" :key="env" size="small" type="warning" class="req-tag">{{ env }}</el-tag>
          </div>
        </div>

        <el-divider content-position="left" v-if="viewingSkill.files?.length">关联文件</el-divider>
        <div class="files-list" v-if="viewingSkill.files?.length">
          <div class="file-item" v-for="file in viewingSkill.files" :key="file.name">
            <el-icon v-if="file.type === 'directory'"><Folder /></el-icon>
            <el-icon v-else><Document /></el-icon>
            <span>{{ file.name }}</span>
            <span class="file-size" v-if="file.size">{{ formatSize(file.size) }}</span>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 创建/编辑 Skill 对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      :title="isEdit ? '编辑 Skill' : '创建 Skill'"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="名称" prop="name" v-if="!isEdit">
          <el-input v-model="formData.name" placeholder="skill-name (小写字母、数字、横线)" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="formData.description" placeholder="Skill 描述" />
        </el-form-item>
        <el-form-item label="存储位置" prop="location" v-if="!isEdit">
          <el-select v-model="formData.location" placeholder="选择位置" style="width: 100%">
            <el-option label="Shared - 共享目录 (~/.openclaw/skills)" value="shared" />
            <el-option label="Workspace - 指定员工" value="workspace" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属员工" prop="agentId" v-if="!isEdit && formData.location === 'workspace'">
          <el-select v-model="formData.agentId" placeholder="选择员工" style="width: 100%">
            <el-option
              v-for="agent in agentsData"
              :key="agent.id"
              :label="agent.name"
              :value="agent.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <textarea
            v-model="formData.content"
            class="content-editor"
            placeholder="SKILL.md 内容（Markdown 格式）"
          ></textarea>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { Plus, View, Edit, Delete, Document, Folder, Search, ArrowDown } from '@element-plus/icons-vue'
import { skillApi } from '../api'
import { createFormRules, sanitizeData } from '../utils/rules'
import { useUserStore } from '../stores/user'
import { marked } from 'marked'

interface Skill {
  slug: string
  name: string
  description: string
  level: 'workspace' | 'shared' | 'bundled'
  path: string
  version?: string
  enabled: boolean
  userInvocable: boolean
  metadata?: {
    openclaw?: {
      requires?: {
        bins?: string[]
        env?: string[]
        config?: string[]
      }
    }
    clawdbot?: {
      requires?: {
        bins?: string[]
        env?: string[]
      }
    }
  }
  agentId?: string
  agentName?: string
  canEdit?: boolean
  canDelete?: boolean
  skillMdContent?: string
  files?: { name: string; size?: number; type: string }[]
  toggling?: boolean  // 新增：开关 loading 状态
}

interface AgentSkills {
  id: string
  name: string
  skills: Skill[]
}

const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const agentsData = ref<AgentSkills[]>([])
const selectedAgent = ref('')
const filterLevel = ref('')
const searchKeyword = ref('')
const agentPopoverVisible = ref(false)

const canEdit = computed(() => userStore.hasPermission('skills', 'write'))
const canDelete = computed(() => userStore.hasPermission('skills', 'delete'))
const canToggle = computed(() => userStore.hasPermission('skills', 'write'))

// 当前选中的 Agent 信息
const selectedAgentInfo = computed(() => {
  return agentsData.value.find(a => a.id === selectedAgent.value)
})

// 选择 Agent
function selectAgent(agentId: string) {
  selectedAgent.value = agentId
  agentPopoverVisible.value = false
}

// 当前显示的 Skills（根据选中的 Agent、级别和搜索关键词筛选）
const displayedSkills = computed(() => {
  if (!selectedAgent.value) return []

  const agent = agentsData.value.find(a => a.id === selectedAgent.value)
  if (!agent) return []

  let skills = agent.skills

  // 级别筛选
  if (filterLevel.value) {
    skills = skills.filter(s => s.level === filterLevel.value)
  }

  // 搜索筛选
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    skills = skills.filter(s =>
      s.name.toLowerCase().includes(keyword) ||
      s.description?.toLowerCase().includes(keyword) ||
      s.slug.toLowerCase().includes(keyword)
    )
  }

  return skills
})

// 查看详情
const viewDialogVisible = ref(false)
const viewingSkill = ref<Skill | null>(null)
const renderedContent = computed(() => {
  if (!viewingSkill.value?.skillMdContent) return ''
  return marked(viewingSkill.value.skillMdContent)
})

// 编辑
const editDialogVisible = ref(false)
const isEdit = ref(false)
const editingSlug = ref('')
const formRef = ref<FormInstance>()
const formData = ref({
  name: '',
  description: '',
  content: '',
  location: 'shared',
  agentId: ''
})

// 使用统一校验规则
const rules = createFormRules({
  name: 'skillName',
  location: 'skillLocation',
  content: 'skillContent'
})

function getSkillIcon(skill: Skill): string {
  const icons: Record<string, string> = {
    'pua': '🎭',
    'excel': '📊',
    'excel-xlsx': '📊',
    'powerpoint-pptx': '📽️',
    'ppt': '📽️',
    'ppt-generator': '📽️',
    'pdf': '📄',
    'python': '🐍',
    'search': '🔍',
    'baidu-search': '🔍'
  }
  return icons[skill.slug] || '⚡'
}

function getLevelType(level: string): '' | 'success' | 'warning' | 'info' | 'danger' {
  const types: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = {
    'workspace': 'success',
    'shared': 'warning',
    'bundled': 'info'
  }
  return types[level] || ''
}

function getRequires(skill: Skill): string {
  const requires = skill.metadata?.openclaw?.requires || skill.metadata?.clawdbot?.requires
  if (!requires) return ''

  const parts: string[] = []
  if (requires.bins?.length) {
    parts.push(`二进制: ${requires.bins.join(', ')}`)
  }
  if (requires.env?.length) {
    parts.push(`环境变量: ${requires.env.join(', ')}`)
  }

  return parts.join(' | ')
}

function formatSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

async function loadSkills() {
  loading.value = true
  try {
    const res = await skillApi.list()
    if (res.data.success) {
      agentsData.value = res.data.data.agents || []
      // 默认选中第一个有 skills 的 Agent
      if (agentsData.value.length > 0 && !selectedAgent.value) {
        const firstWithSkills = agentsData.value.find(a => a.skills.length > 0)
        if (firstWithSkills) {
          selectedAgent.value = firstWithSkills.id
        }
      }
    }
  } catch (e: any) {
    ElMessage.error('加载失败：' + e.message)
  } finally {
    loading.value = false
  }
}

async function viewSkill(skill: Skill) {
  try {
    const res = await skillApi.get(skill.slug)
    if (res.data.success) {
      viewingSkill.value = res.data.data
      viewDialogVisible.value = true
    }
  } catch (e: any) {
    ElMessage.error('加载详情失败')
  }
}

async function toggleSkill(skill: Skill) {
  // 防止重复点击
  if (skill.toggling) return

  const previousState = skill.enabled
  skill.toggling = true

  try {
    const res = await skillApi.toggle(skill.slug, skill.enabled)
    if (res.data.success) {
      ElMessage.success(skill.enabled ? '已启用' : '已禁用')
    } else {
      skill.enabled = !skill.enabled  // 恢复原状态
      const error = res.data.error || '操作失败'
      // 处理速率限制错误
      if (error.includes('rate limit') || error.includes('速率')) {
        ElMessage.warning('操作太频繁，请稍后再试')
      } else {
        ElMessage.error(error)
      }
    }
  } catch (e: any) {
    skill.enabled = !skill.enabled  // 恢复原状态
    const error = e.response?.data?.error || e.message || '未知错误'
    // 处理速率限制错误
    if (error.includes('rate limit') || error.includes('速率')) {
      ElMessage.warning('操作太频繁，请稍后再试')
    } else if (error.includes('Connect call failed')) {
      ElMessage.error('无法连接到 Gateway，请检查服务状态')
    } else {
      ElMessage.error('操作失败：' + error)
    }
  } finally {
    skill.toggling = false
  }
}

function showCreateDialog() {
  isEdit.value = false
  formData.value = {
    name: '',
    description: '',
    content: `# Skill 名称\n\n描述...\n\n## 使用说明\n\n`,
    location: selectedAgent.value ? 'workspace' : 'shared',
    agentId: selectedAgent.value || ''
  }
  editDialogVisible.value = true
}

async function editSkill(skill: Skill) {
  try {
    const res = await skillApi.get(skill.slug)
    if (res.data.success) {
      isEdit.value = true
      editingSlug.value = skill.slug
      formData.value = {
        name: skill.name,
        description: skill.description,
        content: res.data.data.skillMdContent || '',
        location: skill.level as 'workspace' | 'shared',
        agentId: skill.agentId || ''
      }
      editDialogVisible.value = true
    }
  } catch (e: any) {
    ElMessage.error('加载 Skill 失败')
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
      const res = await skillApi.update(editingSlug.value, cleanedData.content)
      if (res.data.success) {
        ElMessage.success('更新成功')
        editDialogVisible.value = false
        loadSkills()
      } else {
        ElMessage.error(res.data.error)
      }
    } else {
      const res = await skillApi.create(cleanedData)
      if (res.data.success) {
        ElMessage.success('创建成功')
        editDialogVisible.value = false
        loadSkills()
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

async function deleteSkill(skill: Skill) {
  try {
    await ElMessageBox.confirm(`确定删除 Skill「${skill.name}」？此操作不可恢复。`, '删除确认', { type: 'warning' })
    const res = await skillApi.delete(skill.slug)
    if (res.data.success) {
      ElMessage.success('删除成功')
      loadSkills()
    } else {
      ElMessage.error(res.data.error)
    }
  } catch {
    // 用户取消
  }
}

onMounted(() => {
  loadSkills()
})
</script>

<style scoped>
.skills-page {
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
  gap: 24px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
}

.filter-label {
  font-size: 14px;
  color: #606266;
  margin-right: 12px;
}

.filter-stats {
  margin-left: auto;
}

/* Agent 选择按钮和面板 */
.agent-select-btn {
  min-width: 160px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
}

.agent-select-btn .selected-agent {
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-select-btn .agent-name {
  font-size: 14px;
  color: #303133;
}

.agent-select-btn .agent-count {
  font-size: 12px;
  color: #909399;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 10px;
}

.agent-select-btn .placeholder {
  color: #a0a0a0;
}

.agent-select-btn .arrow {
  margin-left: 8px;
  color: #c0c4cc;
}

.agent-panel {
  padding: 8px;
}

.agent-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.agent-item:hover {
  background: #f5f7fa;
}

.agent-item.active {
  background: #ecf5ff;
  border-color: #409eff;
}

.agent-item .agent-avatar {
  flex-shrink: 0;
}

.agent-item .agent-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-item .agent-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.agent-item .agent-id {
  font-size: 12px;
  color: #909399;
}

.agent-item .agent-skills {
  font-size: 12px;
  color: #67c23a;
}

/* Skill 网格 */
.skills-section {
  min-height: 300px;
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.skill-card {
  background: #fff;
  border-radius: 6px;
  border: 2px solid transparent;
  overflow: hidden;
  transition: all 0.2s;
}

/* 不同级别的卡片边框颜色 */
.skill-card.card-level-workspace {
  border-color: #67c23a;
  background: linear-gradient(to right, #f6ffed 0%, #fff 20%);
}

.skill-card.card-level-shared {
  border-color: #e6a23c;
  background: linear-gradient(to right, #fdf6ec 0%, #fff 20%);
}

.skill-card.card-level-bundled {
  border-color: #909399;
  background: linear-gradient(to right, #f4f4f5 0%, #fff 20%);
}

.skill-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.card-header {
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.skill-icon {
  font-size: 20px;
}

.skill-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.skill-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-body {
  padding: 0 12px 8px;
}

.skill-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
  margin-bottom: 6px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.skill-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.skill-meta .version {
  color: #67c23a;
  font-family: monospace;
}

.skill-meta .requires-text {
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-footer {
  padding: 8px 12px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.actions {
  display: flex;
  gap: 4px;
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

/* 详情对话框 */
.skill-detail {
  max-height: 60vh;
  overflow-y: auto;
}

.detail-header {
  margin-bottom: 16px;
}

.meta-row {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.meta-label {
  color: #909399;
  font-size: 13px;
}

.skill-content {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 6px;
  font-size: 14px;
  line-height: 1.6;
}

.skill-content :deep(h1) {
  font-size: 20px;
  margin-bottom: 12px;
}

.skill-content :deep(h2) {
  font-size: 16px;
  margin-bottom: 10px;
}

.skill-content :deep(code) {
  background: #e8e8e8;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
}

.skill-content :deep(pre) {
  background: #282c34;
  color: #abb2bf;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
}

.skill-content :deep(pre code) {
  background: transparent;
  padding: 0;
}

.requires-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.req-tag {
  margin-right: 4px;
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.file-size {
  margin-left: auto;
  color: #909399;
  font-size: 12px;
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