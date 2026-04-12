<template>
  <div class="agent-profile-page">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="10" animated />
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <el-empty :description="error">
        <el-button @click="loadProfile">重试</el-button>
      </el-empty>
    </div>

    <!-- Agent 档案 -->
    <div v-else-if="profile" class="profile-container">
      <!-- 顶部操作栏 -->
      <div class="profile-header">
        <div class="header-left">
          <el-button text @click="$router.back()">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
        </div>
        <div class="header-right">
          <el-button @click="showExportDialog = true">
            <el-icon><Download /></el-icon>
            导出
          </el-button>
          <el-button @click="showCloneDialog = true">
            <el-icon><CopyDocument /></el-icon>
            克隆
          </el-button>
        </div>
      </div>

      <!-- 基本信息卡 -->
      <div class="profile-card main-card">
        <div class="avatar-section">
          <div class="avatar" :style="avatarStyle">
            <span class="avatar-emoji">{{ profile.identity.emoji || '🤖' }}</span>
          </div>
          <div class="basic-info">
            <h1 class="agent-name">{{ profile.name }}</h1>
            <p class="agent-creature">{{ profile.identity.creature || 'AI 助手' }}</p>
            <p class="agent-vibe">{{ profile.identity.vibe || '智能助手' }}</p>
            <div class="agent-tags">
              <el-tag v-if="profile.isDefault" type="success" size="small">默认</el-tag>
              <el-tag size="small">{{ profile.model.primary }}</el-tag>
            </div>
          </div>
        </div>
        <div class="action-buttons">
          <el-button type="primary" @click="openIdentityEditor">
            <el-icon><Edit /></el-icon>
            编辑身份
          </el-button>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-icon">🧠</div>
          <div class="stat-info">
            <span class="stat-value">{{ profile.stats.memoryCount || 0 }}</span>
            <span class="stat-label">记忆条数</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">⚡</div>
          <div class="stat-info">
            <span class="stat-value">{{ profile.skills.length }}</span>
            <span class="stat-label">技能</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">🔧</div>
          <div class="stat-info">
            <span class="stat-value">{{ profile.tools.toolCount }}</span>
            <span class="stat-label">工具</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">💬</div>
          <div class="stat-info">
            <span class="stat-value">{{ profile.stats.conversationCount || 0 }}</span>
            <span class="stat-label">对话</span>
          </div>
        </div>
      </div>

      <!-- 灵魂卡片 -->
      <div class="profile-card">
        <div class="card-header">
          <div class="card-title">
            <span class="card-icon">💫</span>
            灵魂
          </div>
          <el-button text type="primary" @click="openSoulEditor">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
        </div>
        <div class="card-content">
          <div class="soul-preview">
            <p class="soul-vibe">{{ profile.soul.vibe || '暂无灵魂描述' }}</p>
            <div v-if="profile.soul.coreTruths?.length" class="soul-traits">
              <span class="trait-label">核心特质：</span>
              <el-tag v-for="(trait, i) in profile.soul.coreTruths.slice(0, 3)" :key="i" size="small" class="trait-tag">
                {{ trait.slice(0, 20) }}{{ trait.length > 20 ? '...' : '' }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- 服务对象卡片 -->
      <div class="profile-card">
        <div class="card-header">
          <div class="card-title">
            <span class="card-icon">👤</span>
            服务对象
          </div>
          <el-button text type="primary" @click="openUserEditor">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
        </div>
        <div class="card-content">
          <div class="user-info">
            <div class="info-row">
              <span class="info-label">称呼</span>
              <span class="info-value">{{ profile.user.name || '未设置' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">时区</span>
              <span class="info-value">{{ profile.user.timezone || '未设置' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">备注</span>
              <span class="info-value">{{ profile.user.notes || '暂无备注' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 记忆卡片 -->
      <div class="profile-card">
        <div class="card-header">
          <div class="card-title">
            <span class="card-icon">🧠</span>
            记忆
          </div>
          <el-button text type="primary" @click="openMemoryManager">
            <el-icon><View /></el-icon>
            管理
          </el-button>
        </div>
        <div class="card-content">
          <div class="memory-stats">
            <div class="memory-item">
              <span class="memory-label">长期记忆</span>
              <span class="memory-size">{{ formatSize(profile.memory.longTermMemorySize) }}</span>
            </div>
            <div class="memory-item">
              <span class="memory-label">日期记忆</span>
              <span class="memory-size">{{ profile.memory.dailyMemories?.length || 0 }} 天</span>
            </div>
            <div class="memory-item">
              <span class="memory-label">最后更新</span>
              <span class="memory-size">{{ formatDate(profile.memory.lastUpdated) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 技能卡片 -->
      <div class="profile-card">
        <div class="card-header">
          <div class="card-title">
            <span class="card-icon">⚡</span>
            技能
          </div>
          <el-button text type="primary" @click="openSkillsConfig">
            <el-icon><Setting /></el-icon>
            配置
          </el-button>
        </div>
        <div class="card-content">
          <div v-if="profile.skills.length" class="skills-list">
            <el-tag v-for="skill in profile.skills" :key="skill" class="skill-tag">
              {{ skill }}
            </el-tag>
          </div>
          <el-empty v-else description="暂无技能" :image-size="60" />
        </div>
      </div>

      <!-- 能力配置卡片 -->
      <div class="profile-card">
        <div class="card-header">
          <div class="card-title">
            <span class="card-icon">🎯</span>
            能力配置
          </div>
          <el-button text type="primary" @click="showCapabilityEditor = true">
            <el-icon><Setting /></el-icon>
            配置
          </el-button>
        </div>
        <div class="card-content">
          <div class="capability-preview">
            <div v-if="capability?.capabilities?.length" class="capabilities-row">
              <span class="preview-label">能力标签：</span>
              <el-tag v-for="cap in capability.capabilities.slice(0, 4)" :key="cap" size="small" class="cap-tag">
                {{ cap }}
              </el-tag>
              <el-tag v-if="capability.capabilities.length > 4" size="small" type="info">
                +{{ capability.capabilities.length - 4 }}
              </el-tag>
            </div>
            <div v-if="capability?.skills?.length" class="skills-row">
              <span class="preview-label">可执行 Skills：</span>
              <el-tag v-for="skill in capability.skills.slice(0, 3)" :key="skill" size="small" type="success" class="skill-cap-tag">
                {{ skill }}
              </el-tag>
              <el-tag v-if="capability.skills.length > 3" size="small" type="info">
                +{{ capability.skills.length - 3 }}
              </el-tag>
            </div>
            <div class="status-row">
              <span class="preview-label">状态：</span>
              <el-tag :type="capability?.status === 'idle' ? 'success' : 'warning'" size="small">
                {{ capability?.status === 'idle' ? '空闲' : '繁忙' }}
              </el-tag>
              <span class="status-detail">成功率 {{ ((capability?.successRate || 0.95) * 100).toFixed(0) }}%</span>
            </div>
            <el-empty v-if="!capability?.capabilities?.length && !capability?.skills?.length" description="未配置能力" :image-size="40" />
          </div>
        </div>
      </div>

      <!-- 工具卡片 -->
      <div class="profile-card">
        <div class="card-header">
          <div class="card-title">
            <span class="card-icon">🔧</span>
            工具箱
          </div>
          <el-button text type="primary" @click="openToolsConfig">
            <el-icon><Setting /></el-icon>
            配置
          </el-button>
        </div>
        <div class="card-content">
          <div class="tools-info">
            <div class="info-row">
              <span class="info-label">配置文件</span>
              <span class="info-value">{{ profile.tools.profile || 'default' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">可用工具</span>
              <span class="info-value">{{ profile.tools.toolCount }} 个</span>
            </div>
            <div v-if="profile.tools.alsoAllow?.length" class="extra-tools">
              <span class="info-label">额外权限：</span>
              <el-tag v-for="tool in profile.tools.alsoAllow.slice(0, 5)" :key="tool" size="small" class="tool-tag">
                {{ tool }}
              </el-tag>
              <el-tag v-if="profile.tools.alsoAllow.length > 5" size="small" type="info">
                +{{ profile.tools.alsoAllow.length - 5 }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- 协作伙伴卡片 -->
      <div class="profile-card">
        <div class="card-header">
          <div class="card-title">
            <span class="card-icon">🤝</span>
            协作伙伴
          </div>
        </div>
        <div class="card-content">
          <div v-if="profile.subagents.allowAgents?.length" class="subagents-info">
            <template v-if="profile.subagents.allowAgents.includes('*')">
              <el-tag type="success">可调用所有 Agent</el-tag>
            </template>
            <template v-else>
              <el-tag v-for="agent in profile.subagents.allowAgents" :key="agent" class="agent-tag">
                {{ agent }}
              </el-tag>
            </template>
          </div>
          <el-empty v-else description="暂无协作权限" :image-size="60" />
        </div>
      </div>

      <!-- 模型卡片 -->
      <div class="profile-card">
        <div class="card-header">
          <div class="card-title">
            <span class="card-icon">🧠</span>
            大脑模型
          </div>
        </div>
        <div class="card-content">
          <div class="model-info">
            <div class="info-row">
              <span class="info-label">主模型</span>
              <span class="info-value model-name">{{ profile.model.primary }}</span>
            </div>
            <div v-if="profile.model.fallback" class="info-row">
              <span class="info-label">备用模型</span>
              <span class="info-value">{{ profile.model.fallback }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 个人资料卡片（拟人化属性） -->
      <div class="profile-card">
        <div class="card-header">
          <div class="card-title">
            <span class="card-icon">👤</span>
            个人资料
          </div>
          <el-button text type="primary" @click="showExtendedEditor = true">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
        </div>
        <div class="card-content">
          <div class="extended-info">
            <div class="info-row">
              <span class="info-label">性别</span>
              <span class="info-value">{{ profile.extended?.gender || '未设置' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">生日</span>
              <span class="info-value">{{ profile.extended?.birthday || '未设置' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">年龄</span>
              <span class="info-value">{{ profile.extended?.age_display || '未设置' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">性格</span>
              <span class="info-value">{{ profile.extended?.personality || '未设置' }}</span>
            </div>
            <div v-if="profile.extended?.hobbies?.length" class="info-row">
              <span class="info-label">爱好</span>
              <div class="hobby-tags">
                <el-tag v-for="hobby in profile.extended.hobbies" :key="hobby" size="small" class="hobby-tag">
                  {{ hobby }}
                </el-tag>
              </div>
            </div>
            <div class="info-row">
              <span class="info-label">说话风格</span>
              <span class="info-value">{{ profile.extended?.voice_style || '未设置' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 身份编辑器 -->
    <IdentityEditor
      v-model:visible="showIdentityEditor"
      :identity="profile?.identity"
      :agent-id="agentId"
      @saved="onIdentitySaved"
    />

    <!-- 灵魂编辑器 -->
    <SoulEditor
      v-model:visible="showSoulEditor"
      :soul="profile?.soul"
      :agent-id="agentId"
      @saved="onSoulSaved"
    />

    <!-- 主人信息编辑器 -->
    <UserEditor
      v-model:visible="showUserEditor"
      :user="profile?.user"
      :agent-id="agentId"
      @saved="onUserSaved"
    />

    <!-- 记忆管理器 -->
    <MemoryManager
      v-model:visible="showMemoryManager"
      :memory="profile?.memory"
      :agent-id="agentId"
      @saved="onMemorySaved"
    />

    <!-- 克隆对话框 -->
    <CloneDialog
      v-model:visible="showCloneDialog"
      :agent="profile"
      @cloned="onCloned"
    />

    <!-- 导出对话框 -->
    <ExportDialog
      v-model:visible="showExportDialog"
      :agent="profile"
    />

    <!-- 工具配置编辑器 -->
    <ToolsEditor
      v-model="showToolsEditor"
      :agent-id="agentId"
      @saved="onToolsSaved"
    />

    <!-- 扩展档案编辑器 -->
    <ExtendedEditor
      v-model="showExtendedEditor"
      :agent-id="agentId"
      :profile="profile?.extended"
      @saved="onExtendedSaved"
    />

    <!-- 能力配置编辑器 -->
    <CapabilityEditor
      v-model="showCapabilityEditor"
      :agent-id="agentId"
      @saved="onCapabilitySaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Edit, Download, CopyDocument, View, Setting } from '@element-plus/icons-vue'
import type { AgentProfile } from './types'
import { getAgentProfile, getExtendedProfile, getAgentCapability } from './api'

// 子组件
import IdentityEditor from './components/IdentityEditor.vue'
import SoulEditor from './components/SoulEditor.vue'
import UserEditor from './components/UserEditor.vue'
import MemoryManager from './components/MemoryManager.vue'
import CloneDialog from './components/CloneDialog.vue'
import ExtendedEditor from './components/ExtendedEditor.vue'
import ExportDialog from './components/ExportDialog.vue'
import ToolsEditor from './components/ToolsEditor.vue'
import CapabilityEditor from './components/CapabilityEditor.vue'

const route = useRoute()
const router = useRouter()

// 状态
const loading = ref(true)
const error = ref('')
const profile = ref<AgentProfile | null>(null)
const capability = ref<any>(null)

// 对话框状态
const showIdentityEditor = ref(false)
const showSoulEditor = ref(false)
const showUserEditor = ref(false)
const showMemoryManager = ref(false)
const showCloneDialog = ref(false)
const showExportDialog = ref(false)
const showToolsEditor = ref(false)
const showExtendedEditor = ref(false)
const showCapabilityEditor = ref(false)

// 当前 Agent ID
const agentId = computed(() => route.params.id as string || route.query.id as string)

// 头像样式
const avatarStyle = computed(() => {
  const colors = [
    'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)'
  ]
  const index = agentId.value?.charCodeAt(0) % colors.length || 0
  return { background: colors[index] }
})

// 加载档案
async function loadProfile() {
  if (!agentId.value) {
    error.value = '未指定 Agent'
    loading.value = false
    return
  }

  loading.value = true
  error.value = ''

  try {
    const data = await getAgentProfile(agentId.value)
    if (data) {
      profile.value = data

      // 加载扩展档案
      const extended = await getExtendedProfile(agentId.value)
      if (extended) {
        profile.value.extended = extended
      }

      // 加载能力配置
      const cap = await getAgentCapability(agentId.value)
      capability.value = cap
    } else {
      error.value = 'Agent 不存在'
    }
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

// 编辑器操作
function openIdentityEditor() {
  showIdentityEditor.value = true
}

function openSoulEditor() {
  showSoulEditor.value = true
}

function openUserEditor() {
  showUserEditor.value = true
}

function openMemoryManager() {
  showMemoryManager.value = true
}

function openSkillsConfig() {
  // 跳转到 Skills 配置页面
  router.push('/skills-list')
}

function openToolsConfig() {
  showToolsEditor.value = true
}

// 保存回调
function onIdentitySaved() {
  loadProfile()
}

function onSoulSaved() {
  loadProfile()
}

function onUserSaved() {
  loadProfile()
}

function onMemorySaved() {
  loadProfile()
}

function onToolsSaved() {
  loadProfile()
}

function onExtendedSaved() {
  loadProfile()
}

function onCapabilitySaved() {
  loadProfile()
}

function onCloned(newId: string) {
  showCloneDialog.value = false
  ElMessage.success('克隆成功')
  // 可以跳转到新 Agent
}

// 格式化函数
function formatSize(bytes: number): string {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '未知'
  try {
    return new Date(dateStr).toLocaleDateString('zh-CN')
  } catch {
    return dateStr
  }
}

// 监听路由变化
watch(agentId, () => {
  loadProfile()
})

onMounted(() => {
  loadProfile()
})
</script>

<style scoped>
.agent-profile-page {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
}

.loading-state,
.error-state {
  padding: 40px;
}

/* 顶部操作栏 */
.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-right {
  display: flex;
  gap: 10px;
}

/* 主卡片 */
.profile-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.main-card {
  background: linear-gradient(135deg, #f5f7fa 0%, #fff 100%);
}

/* 头像区域 */
.avatar-section {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 16px;
}

.avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.avatar-emoji {
  font-size: 36px;
}

.basic-info {
  flex: 1;
}

.agent-name {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 4px 0;
}

.agent-creature {
  font-size: 14px;
  color: #666;
  margin: 0 0 4px 0;
}

.agent-vibe {
  font-size: 13px;
  color: #999;
  margin: 0 0 8px 0;
}

.agent-tags {
  display: flex;
  gap: 8px;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

/* 统计卡片 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.stat-icon {
  font-size: 24px;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
}

.stat-label {
  font-size: 12px;
  color: #999;
}

/* 卡片头部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-icon {
  font-size: 18px;
}

/* 灵魂预览 */
.soul-preview {
  color: #666;
}

.soul-vibe {
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 12px 0;
}

.soul-traits {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.trait-label {
  font-size: 13px;
  color: #999;
}

.trait-tag {
  background: #f5f5f5;
  border: none;
  color: #666;
}

/* 用户信息 */
.user-info,
.tools-info,
.model-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-row {
  display: flex;
  align-items: center;
}

.info-label {
  width: 80px;
  font-size: 13px;
  color: #999;
}

.info-value {
  font-size: 14px;
  color: #333;
}

.model-name {
  font-family: monospace;
  background: #f5f5f5;
  padding: 2px 8px;
  border-radius: 4px;
}

.extra-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.tool-tag {
  font-size: 11px;
}

/* 记忆统计 */
.memory-stats {
  display: flex;
  gap: 24px;
}

.memory-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.memory-label {
  font-size: 12px;
  color: #999;
}

.memory-size {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

/* 技能列表 */
.skills-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.skill-tag {
  background: #e6f7ff;
  border-color: #91d5ff;
  color: #1890ff;
}

/* 协作伙伴 */
.subagents-info {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.agent-tag {
  background: #f6ffed;
  border-color: #b7eb8f;
  color: #52c41a;
}

/* 能力配置预览 */
.capability-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.capabilities-row,
.skills-row,
.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.preview-label {
  font-size: 13px;
  color: #999;
}

.cap-tag {
  background: #f0f5ff;
  border-color: #adc6ff;
  color: #2f54eb;
}

.skill-cap-tag {
  background: #f6ffed;
  border-color: #b7eb8f;
  color: #52c41a;
}

.status-detail {
  font-size: 12px;
  color: #666;
  margin-left: 8px;
}

/* 响应式 */
@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .avatar-section {
    flex-direction: column;
    text-align: center;
  }

  .avatar {
    width: 100px;
    height: 100px;
  }

  .agent-tags {
    justify-content: center;
  }
}
</style>