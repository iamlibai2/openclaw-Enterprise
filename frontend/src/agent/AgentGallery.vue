<template>
  <div class="agent-gallery-page">
    <div class="page-header">
      <div class="header-left">
        <h2>Agent 档案</h2>
        <p class="page-desc">将 Agent 视为"人"而非配置集合</p>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="showBuilder = true">
          <el-icon><Plus /></el-icon>
          创建
        </el-button>
        <el-button @click="showImportDialog = true">
          <el-icon><Upload /></el-icon>
          导入
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="5" animated />
    </div>

    <!-- Agent 卡片网格 -->
    <div v-else class="agent-grid">
      <div
        v-for="agent in agents"
        :key="agent.id"
        class="agent-card"
        @click="goToProfile(agent.id)"
      >
        <div class="card-avatar" :style="getAvatarStyle(agent.id)">
          <span class="avatar-emoji">{{ agent.emoji || '🤖' }}</span>
        </div>
        <div class="card-info">
          <h3 class="card-name">{{ agent.name }}</h3>
          <p class="card-creature">{{ agent.creature || 'AI 助手' }}</p>
          <p class="card-vibe">{{ agent.vibe || '智能助手' }}</p>
        </div>
        <div class="card-stats">
          <div class="stat">
            <span class="stat-icon">🧠</span>
            <span class="stat-value">{{ agent.stats.memoryCount || 0 }}</span>
          </div>
          <div class="stat">
            <span class="stat-icon">⚡</span>
            <span class="stat-value">{{ agent.stats.skillCount || 0 }}</span>
          </div>
          <div class="stat">
            <span class="stat-icon">🔧</span>
            <span class="stat-value">{{ agent.stats.toolCount || 0 }}</span>
          </div>
        </div>
        <div class="card-footer">
          <el-tag v-if="agent.isDefault" type="success" size="small">默认</el-tag>
          <el-button type="primary" text>
            查看档案
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && !agents.length" description="暂无 Agent">
      <el-button type="primary" @click="$router.push('/agents')">前往创建</el-button>
    </el-empty>

    <!-- 导入对话框 -->
    <ImportDialog
      v-model="showImportDialog"
      @imported="onImported"
    />

    <!-- 创建向导 -->
    <AgentBuilder
      v-model="showBuilder"
      @created="onCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Upload, Plus } from '@element-plus/icons-vue'
import type { AgentListItem } from '../agent/types'
import { getAgentList } from '../agent/api'
import ImportDialog from './components/ImportDialog.vue'
import AgentBuilder from './components/AgentBuilder.vue'

const router = useRouter()
const loading = ref(true)
const agents = ref<AgentListItem[]>([])
const showImportDialog = ref(false)
const showBuilder = ref(false)

async function loadAgents() {
  loading.value = true
  try {
    agents.value = await getAgentList()
  } catch (e) {
    console.error('Failed to load agents:', e)
  } finally {
    loading.value = false
  }
}

function goToProfile(agentId: string) {
  router.push(`/agent/${agentId}`)
}

function getAvatarStyle(agentId: string): Record<string, string> {
  const colors = [
    'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)'
  ]
  const index = agentId?.charCodeAt(0) % colors.length || 0
  return { background: colors[index] }
}

onMounted(() => {
  loadAgents()
})

function onImported(agentId: string) {
  loadAgents()
  // 可选：跳转到新导入的 Agent
  router.push(`/agent/${agentId}`)
}

function onCreated(agentId: string) {
  loadAgents()
  router.push(`/agent/${agentId}`)
}
</script>

<style scoped>
.agent-gallery-page {
  margin: -20px;
  padding: 20px;
  min-height: calc(100vh - 56px);
  background: #f5f7fa;
}

.page-header {
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-left {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.header-left h2 {
  font-size: 22px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
  line-height: 1.3;
  text-align: left;
}

.header-left .page-desc {
  font-size: 14px;
  color: #999;
  margin: 0;
  line-height: 1.5;
  text-align: left;
}

.header-right {
  display: flex;
  gap: 8px;
}

.loading-state {
  padding: 40px;
}

/* Agent 卡片网格 */
.agent-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.agent-card {
  background: #fff;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid transparent;
}

.agent-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  border-color: #1890ff;
}

.card-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.avatar-emoji {
  font-size: 28px;
}

.card-info {
  margin-bottom: 16px;
}

.card-name {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 4px 0;
}

.card-creature {
  font-size: 13px;
  color: #666;
  margin: 0 0 2px 0;
}

.card-vibe {
  font-size: 12px;
  color: #999;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-stats {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  border-top: 1px solid #f0f0f0;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 16px;
}

.stat {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-icon {
  font-size: 14px;
}

.stat-value {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 响应式 */
@media (max-width: 1200px) {
  .agent-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1000px) {
  .agent-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .agent-grid {
    grid-template-columns: 1fr;
  }
}
</style>