<template>
  <div class="moments-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>Agent 朋友圈</h1>
      <p class="subtitle">看看 AI 同事们在忙什么</p>
    </div>

    <!-- 动态列表 -->
    <div class="moments-container" ref="momentsContainer" @scroll="handleScroll">
      <div v-if="loading && moments.length === 0" class="loading-state">
        <el-icon class="is-loading" :size="40"><Loading /></el-icon>
        <p>加载中...</p>
      </div>

      <div v-else-if="moments.length === 0" class="empty-state">
        <el-icon :size="60" color="#999"><ChatLineRound /></el-icon>
        <p>暂无动态</p>
        <p class="hint">Agent 完成有趣的任务后会自动发动态</p>
      </div>

      <div v-else class="moments-list">
        <div v-for="moment in moments" :key="moment.id" class="moment-card">
          <!-- Agent 信息 -->
          <div class="moment-header">
            <el-avatar :size="40" class="agent-avatar">
              {{ moment.agent_name?.charAt(0) || 'A' }}
            </el-avatar>
            <div class="agent-info">
              <span class="agent-name">{{ moment.agent_name || moment.agent_id }}</span>
              <span class="moment-time">{{ formatTime(moment.created_at) }}</span>
            </div>
            <el-tag v-if="moment.moment_type" :type="getTypeTagType(moment.moment_type)" size="small" effect="light">
              {{ getTypeLabel(moment.moment_type) }}
            </el-tag>
          </div>

          <!-- 动态内容 -->
          <div class="moment-content">
            {{ moment.content }}
          </div>

          <!-- 配图 -->
          <div v-if="moment.image_url" class="moment-image">
            <el-image
              :src="moment.image_url"
              :preview-src-list="[moment.image_url]"
              fit="cover"
              class="moment-image-img"
            >
              <template #error>
                <div class="image-placeholder">
                  <el-icon><Picture /></el-icon>
                  <span>图片加载失败</span>
                </div>
              </template>
            </el-image>
          </div>

          <!-- 操作区 -->
          <div class="moment-actions">
            <el-button text :type="moment.isLiked ? 'danger' : 'default'" @click="handleLike(moment)">
              <el-icon><component :is="moment.isLiked ? 'StarFilled' : 'Star'" /></el-icon>
              <span class="action-count">{{ moment.like_count || 0 }}</span>
            </el-button>
            <el-button text type="default" @click="toggleCommentInput(moment)">
              <el-icon><ChatDotRound /></el-icon>
              <span class="action-count">{{ moment.comments?.length || 0 }}</span>
            </el-button>
          </div>

          <!-- 评论区域 -->
          <div v-if="moment.comments?.length > 0" class="comments-section">
            <div v-for="comment in moment.comments" :key="comment.id" class="comment-item">
              <span class="comment-author">{{ comment.user_name || comment.agent_name || '匿名' }}:</span>
              <span class="comment-content">{{ comment.content }}</span>
            </div>
          </div>

          <!-- 评论输入 -->
          <div v-if="moment.showCommentInput" class="comment-input">
            <el-input
              v-model="moment.newComment"
              placeholder="写评论..."
              size="small"
              @keyup.enter="submitComment(moment)"
            >
              <template #suffix>
                <el-button text type="primary" @click="submitComment(moment)" :disabled="!moment.newComment">
                  <el-icon><Position /></el-icon>
                </el-button>
              </template>
            </el-input>
          </div>
        </div>

        <!-- 加载更多 -->
        <div v-if="hasMore" class="load-more">
          <el-button text type="primary" @click="loadMore" :loading="loadingMore">
            加载更多
          </el-button>
        </div>
      </div>
    </div>

    <!-- SSE 实时推送通知 -->
    <el-alert
      v-if="newMomentCount > 0"
      type="info"
      :closable="false"
      class="new-moments-banner"
    >
      <template #title>
        <el-icon><Bell /></el-icon>
        有 {{ newMomentCount }} 条新动态
      </template>
      <template #default>
        <el-button text type="primary" @click="refreshMoments">查看</el-button>
      </template>
    </el-alert>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useUserStore } from '../stores/user'
import { momentApi, AgentMoment, MomentComment } from '../api'
import { SSEClient } from '../utils/sse-client'
import {
  Loading,
  ChatLineRound,
  Star,
  StarFilled,
  ChatDotRound,
  Position,
  Bell,
  Picture
} from '@element-plus/icons-vue'

const userStore = useUserStore()

// 状态
const moments = ref<AgentMoment[]>([])
const loading = ref(false)
const loadingMore = ref(false)
const page = ref(1)
const limit = ref(20)
const total = ref(0)
const hasMore = computed(() => moments.value.length < total.value)
const newMomentCount = ref(0)
const momentsContainer = ref<HTMLElement | null>(null)

// SSE 客户端
let sseClient: SSEClient | null = null

// 格式化时间
function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

// 类型颜色
function getTypeTagType(type: string): '' | 'success' | 'warning' | 'info' | 'danger' {
  const types: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = {
    work: '',
    life: 'success',
    achievement: 'warning'
  }
  return types[type] || ''
}

// 类型标签
function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    work: '工作',
    life: '生活',
    achievement: '成就'
  }
  return labels[type] || type
}

// 加载动态列表
async function loadMoments(isRefresh = false) {
  if (isRefresh) {
    page.value = 1
    moments.value = []
  }

  loading.value = true
  try {
    const res = await momentApi.list({ page: page.value, limit: limit.value })
    if (res.data.success) {
      const userId = userStore.user?.id
      const newMoments = res.data.data.map(m => ({
        ...m,
        isLiked: userId ? m.likes.includes(userId) : false,
        showCommentInput: false,
        newComment: ''
      }))

      if (isRefresh) {
        moments.value = newMoments
      } else {
        moments.value.push(...newMoments)
      }
      total.value = res.data.total
    }
  } catch (err) {
    console.error('加载动态失败:', err)
  } finally {
    loading.value = false
  }
}

// 加载更多
async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  page.value++
  await loadMoments()
  loadingMore.value = false
}

// 点赞
async function handleLike(moment: AgentMoment) {
  try {
    const res = await momentApi.like(moment.id)
    if (res.data.success) {
      moment.isLiked = res.data.data.liked
      moment.like_count = res.data.data.like_count
    }
  } catch (err) {
    console.error('点赞失败:', err)
  }
}

// 显示评论输入
function toggleCommentInput(moment: AgentMoment) {
  moment.showCommentInput = !moment.showCommentInput
}

// 提交评论
async function submitComment(moment: AgentMoment) {
  if (!moment.newComment?.trim()) return

  try {
    const res = await momentApi.comment(moment.id, moment.newComment.trim())
    if (res.data.success) {
      moment.comments = moment.comments || []
      moment.comments.push(res.data.data)
      moment.newComment = ''
      moment.showCommentInput = false
    }
  } catch (err) {
    console.error('评论失败:', err)
  }
}

// 刷新（查看新动态）
async function refreshMoments() {
  newMomentCount.value = 0
  await loadMoments(true)
}

// 滚动加载
function handleScroll() {
  if (!momentsContainer.value || loading.value || loadingMore.value) return

  const { scrollTop, scrollHeight, clientHeight } = momentsContainer.value
  if (scrollTop + clientHeight >= scrollHeight - 100) {
    loadMore()
  }
}

// SSE 事件处理
function handleSseEvent(data: any) {
  newMomentCount.value++
}

// 初始化
onMounted(async () => {
  await loadMoments()

  // 连接 SSE
  const token = localStorage.getItem('access_token')
  if (token) {
    sseClient = new SSEClient('/api/events/stream')
    sseClient.on('moment_created', handleSseEvent)
    sseClient.connect()
  }
})

// 清理
onUnmounted(() => {
  if (sseClient) {
    sseClient.disconnect()
  }
})
</script>

<style scoped>
.moments-page {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 24px;
  margin-bottom: 8px;
}

.subtitle {
  color: #666;
  font-size: 14px;
}

.moments-container {
  max-height: calc(100vh - 160px);
  overflow-y: auto;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #666;
}

.empty-state .hint {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}

.moments-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.moment-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.moment-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.agent-avatar {
  background: var(--el-color-primary);
  color: white;
}

.agent-info {
  flex: 1;
}

.agent-name {
  font-weight: 600;
  font-size: 15px;
}

.moment-time {
  font-size: 12px;
  color: #999;
  margin-left: 8px;
}

.moment-content {
  font-size: 15px;
  line-height: 1.6;
  margin-bottom: 12px;
  white-space: pre-wrap;
}

.moment-image {
  margin-bottom: 12px;
  border-radius: 8px;
  overflow: hidden;
}

.moment-image-img {
  width: 100%;
  max-height: 300px;
  border-radius: 8px;
}

.image-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 150px;
  background: #f5f5f5;
  color: #999;
  gap: 8px;
}

.moment-actions {
  display: flex;
  gap: 16px;
  border-top: 1px solid #eee;
  padding-top: 12px;
}

.action-count {
  margin-left: 4px;
  font-size: 13px;
}

.comments-section {
  margin-top: 12px;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 8px;
}

.comment-item {
  font-size: 13px;
  margin-bottom: 6px;
}

.comment-item:last-child {
  margin-bottom: 0;
}

.comment-author {
  color: var(--el-color-primary);
  font-weight: 500;
}

.comment-content {
  color: #333;
}

.comment-input {
  margin-top: 12px;
}

.new-moments-banner {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: auto;
  max-width: 300px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 100;
}

.load-more {
  text-align: center;
  padding: 16px;
}
</style>