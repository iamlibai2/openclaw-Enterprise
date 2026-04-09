<template>
  <el-config-provider :locale="zhCn">
    <!-- 未登录时只显示 router-view（登录页面） -->
    <template v-if="!userStore.isLoggedIn">
      <router-view />
    </template>

    <!-- 已登录时显示完整布局 -->
    <template v-else>
      <div class="app-container">
        <el-container>
          <!-- 侧边栏 -->
          <el-aside width="210px">
            <div class="sidebar-header">
              <img :src="logoImg" class="logo" alt="OpenClaw" />
              <span class="title">OpenClaw</span>
            </div>

            <!-- 导航菜单 -->
            <el-scrollbar class="menu-scrollbar">
              <el-menu
                :default-active="activeMenu"
                :default-openeds="['organization', 'workflow', 'agent-management', 'experience', 'knowledge', 'security-menu', 'monitor', 'openclaw', 'settings']"
                router
                class="sidebar-menu"
              >
                <!-- 首页仪表盘 -->
                <el-menu-item index="/dashboard">
                  <el-icon><Odometer /></el-icon>
                  <span>工作台</span>
                </el-menu-item>

                <!-- 消息（Discord 风格） -->
                <el-menu-item index="/messages" v-if="hasPermission('sessions', 'read')">
                  <el-icon><ChatDotRound /></el-icon>
                  <span>消息</span>
                </el-menu-item>

                <!-- 飞书聊天 -->
                <el-menu-item index="/feishu-chat" v-if="hasPermission('sessions', 'read')">
                  <el-icon><ChatLineRound /></el-icon>
                  <span>飞书聊天</span>
                </el-menu-item>

                <!-- Agent 对话 -->
                <el-menu-item index="/chat" v-if="hasPermission('sessions', 'read')">
                  <el-icon><ChatDotRound /></el-icon>
                  <span>对话</span>
                </el-menu-item>

                <!-- Agent 群聊 -->
                <el-menu-item index="/group-chat" v-if="hasPermission('sessions', 'read')">
                  <el-icon><UserFilled /></el-icon>
                  <span>群聊讨论</span>
                </el-menu-item>

                <!-- Agent 朋友圈 -->
                <el-menu-item index="/moments">
                  <el-icon><ChatLineSquare /></el-icon>
                  <span>朋友圈</span>
                </el-menu-item>

                <!-- 组织管理 -->
                <el-sub-menu index="organization">
                  <template #title>
                    <el-icon><UserFilled /></el-icon>
                    <span>组织管理</span>
                  </template>
                  <el-menu-item index="/employees" v-if="hasPermission('agents', 'read')">
                    <el-icon><Avatar /></el-icon>
                    <span>员工卡片</span>
                  </el-menu-item>
                  <el-menu-item index="/departments" v-if="hasPermission('employees', 'read')">
                    <el-icon><OfficeBuilding /></el-icon>
                    <span>部门管理</span>
                  </el-menu-item>
                </el-sub-menu>

                <!-- 工作管理 -->
                <el-sub-menu index="workflow">
                  <template #title>
                    <el-icon><Document /></el-icon>
                    <span>工作管理</span>
                  </template>
                  <el-menu-item index="/tasks">
                    <el-icon><Document /></el-icon>
                    <span>任务列表</span>
                  </el-menu-item>
                  <el-menu-item index="/scheduled-tasks" v-if="hasPermission('tasks', 'read')">
                    <el-icon><Clock /></el-icon>
                    <span>定时任务</span>
                  </el-menu-item>
                  <el-menu-item index="/image-generator">
                    <el-icon><Picture /></el-icon>
                    <span>图片生成</span>
                  </el-menu-item>
                </el-sub-menu>

                <!-- 经验管理 -->
                <el-sub-menu index="experience">
                  <template #title>
                    <el-icon><Lightning /></el-icon>
                    <span>经验管理</span>
                  </template>
                  <el-menu-item index="/memories" v-if="hasPermission('memories', 'read')">
                    <el-icon><Memo /></el-icon>
                    <span>记忆管理</span>
                  </el-menu-item>
                </el-sub-menu>

                <!-- Agent 管理 -->
                <el-sub-menu index="agent-management">
                  <template #title>
                    <el-icon><User /></el-icon>
                    <span>Agent 管理</span>
                  </template>
                  <el-menu-item index="/agent-gallery" v-if="hasPermission('agents', 'read')">
                    <el-icon><User /></el-icon>
                    <span>Agent 档案</span>
                  </el-menu-item>
                  <el-menu-item index="/agents" v-if="hasPermission('agents', 'read')">
                    <el-icon><Setting /></el-icon>
                    <span>Agent 配置</span>
                  </el-menu-item>
                  <el-menu-item index="/souls" v-if="hasPermission('agents', 'read')">
                    <el-icon><MagicStick /></el-icon>
                    <span>灵魂管理</span>
                  </el-menu-item>
                  <el-menu-item index="/soul-inject" v-if="hasPermission('config', 'write')">
                    <el-icon><Promotion /></el-icon>
                    <span>灵魂注入</span>
                  </el-menu-item>
                  <el-menu-item index="/skills-list" v-if="hasPermission('skills', 'read')">
                    <el-icon><Lightning /></el-icon>
                    <span>技能配置</span>
                  </el-menu-item>
                  <el-menu-item index="/tools" v-if="hasPermission('tools', 'read')">
                    <el-icon><Tools /></el-icon>
                    <span>工具配置</span>
                  </el-menu-item>
                  <el-menu-item index="/bindings" v-if="hasPermission('bindings', 'read')">
                    <el-icon><Link /></el-icon>
                    <span>渠道绑定</span>
                  </el-menu-item>
                  <el-menu-item index="/templates" v-if="hasPermission('config', 'read')">
                    <el-icon><Collection /></el-icon>
                    <span>Agent 模板</span>
                  </el-menu-item>
                </el-sub-menu>

                <!-- 知识管理 -->
                <el-sub-menu index="knowledge">
                  <template #title>
                    <el-icon><Reading /></el-icon>
                    <span>知识管理</span>
                  </template>
                  <el-menu-item index="/knowledge-base">
                    <el-icon><Collection /></el-icon>
                    <span>知识库</span>
                  </el-menu-item>
                </el-sub-menu>

                <!-- 安全管理 -->
                <el-sub-menu index="security-menu">
                  <template #title>
                    <el-icon><Lock /></el-icon>
                    <span>安全管理</span>
                  </template>
                  <el-menu-item index="/security" v-if="hasPermission('security', 'read')">
                    <el-icon><Lock /></el-icon>
                    <span>安全设置</span>
                  </el-menu-item>
                </el-sub-menu>

                <!-- 监控与状态 -->
                <el-sub-menu index="monitor">
                  <template #title>
                    <el-icon><Monitor /></el-icon>
                    <span>监控与状态</span>
                  </template>
                  <el-menu-item index="/status" v-if="hasPermission('status', 'read')">
                    <el-icon><CircleCheck /></el-icon>
                    <span>运行状态</span>
                  </el-menu-item>
                  <el-menu-item index="/sessions" v-if="hasPermission('sessions', 'read')">
                    <el-icon><ChatDotRound /></el-icon>
                    <span>会话列表</span>
                  </el-menu-item>
                  <el-menu-item index="/openclaw-logs" v-if="hasPermission('logs', 'read')">
                    <el-icon><Tickets /></el-icon>
                    <span>OpenClaw 日志</span>
                  </el-menu-item>
                  <el-menu-item index="/admin-logs" v-if="hasPermission('logs', 'read')">
                    <el-icon><Notebook /></el-icon>
                    <span>Admin 日志</span>
                  </el-menu-item>
                  <el-menu-item index="/operation-logs" v-if="hasPermission('logs', 'read')">
                    <el-icon><Document /></el-icon>
                    <span>操作日志</span>
                  </el-menu-item>
                </el-sub-menu>

                <!-- OpenClaw 管理 -->
                <el-sub-menu index="openclaw">
                  <template #title>
                    <el-icon><Box /></el-icon>
                    <span>OpenClaw 管理</span>
                  </template>
                  <el-menu-item index="/models" v-if="hasPermission('models', 'read')">
                    <el-icon><Cpu /></el-icon>
                    <span>OpenClaw用模型配置</span>
                  </el-menu-item>
                  <el-menu-item index="/channels" v-if="hasPermission('config', 'read')">
                    <el-icon><ChatLineSquare /></el-icon>
                    <span>Channel 管理</span>
                  </el-menu-item>
                  <el-menu-item index="/config" v-if="hasPermission('config', 'read')">
                    <el-icon><EditPen /></el-icon>
                    <span>配置编辑</span>
                  </el-menu-item>
                </el-sub-menu>

                <!-- 系统设置 -->
                <el-sub-menu index="settings">
                  <template #title>
                    <el-icon><Setting /></el-icon>
                    <span>系统设置</span>
                  </template>
                  <el-menu-item index="/gateways">
                    <el-icon><Connection /></el-icon>
                    <span>Gateway 管理</span>
                  </el-menu-item>
                  <el-menu-item index="/model-providers">
                    <el-icon><Cpu /></el-icon>
                    <span>系统用模型配置</span>
                  </el-menu-item>
                  <el-menu-item index="/users" v-if="hasPermission('users', 'read')">
                    <el-icon><Avatar /></el-icon>
                    <span>用户管理</span>
                  </el-menu-item>
                </el-sub-menu>

                <!-- 帮助 -->
                <el-menu-item index="/docs">
                  <el-icon><Reading /></el-icon>
                  <span>帮助文档</span>
                </el-menu-item>
              </el-menu>
            </el-scrollbar>
          </el-aside>

          <!-- 右侧主区域 -->
          <el-container>
            <!-- 顶部 Header -->
            <el-header class="app-header">
              <div class="header-left">
                <!-- 可放面包屑或其他信息 -->
                <span class="page-title">{{ pageTitle }}</span>
              </div>
              <div class="header-right">
                <!-- Gateway 状态 -->
                <div class="gateway-info" @click="toggleGatewayPanel">
                  <span class="status-dot" :class="gatewayStatus"></span>
                  <span class="gateway-label">{{ gatewayName || 'Gateway' }}</span>
                  <span class="gateway-status-text">{{ gatewayStatus === 'online' ? '在线' : gatewayStatus === 'error' ? '离线' : '未知' }}</span>
                  <el-icon class="gateway-arrow"><ArrowDown /></el-icon>

                  <!-- 控制面板 -->
                  <div class="gateway-panel" v-show="showGatewayPanel" @click.stop>
                    <div class="panel-item" @click="goToGateways">
                      <el-icon><Connection /></el-icon>
                      <span>Gateway 管理</span>
                    </div>
                    <div class="panel-item" @click="refreshStatus">
                      <el-icon :class="{ 'is-loading': refreshing }"><Refresh /></el-icon>
                      <span>刷新状态</span>
                    </div>
                  </div>
                </div>

                <!-- 通知中心（仅管理员可见） -->
                <div class="notification-center" v-if="isAdmin" @click="toggleNotifications" v-click-outside="closeNotifications">
                  <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
                    <el-icon :size="20"><Bell /></el-icon>
                  </el-badge>

                  <!-- 通知下拉面板 -->
                  <div class="notification-panel" v-show="showNotifications" @click.stop>
                    <div class="panel-header">
                      <span>任务通知</span>
                      <el-button type="primary" link size="small" @click="markAllRead" v-if="unreadCount > 0">
                        全部已读
                      </el-button>
                    </div>
                    <div class="panel-body" v-loading="notificationsLoading">
                      <div
                        class="notification-item"
                        v-for="item in notifications"
                        :key="item.id"
                        :class="{ unread: !item.is_read }"
                        @click="viewNotification(item)"
                      >
                        <div class="notif-icon">
                          <el-icon :class="item.status"><component :is="getStatusIcon(item.status)" /></el-icon>
                        </div>
                        <div class="notif-content">
                          <div class="notif-title">{{ item.task_name }}</div>
                          <div class="notif-desc">
                            <span :class="['status-text', item.status]">{{ getStatusLabel(item.status) }}</span>
                            <span class="notif-time">{{ formatNotifTime(item.created_at) }}</span>
                          </div>
                        </div>
                      </div>
                      <div class="empty-notif" v-if="!notificationsLoading && notifications.length === 0">
                        <el-icon :size="32"><Bell /></el-icon>
                        <p>暂无通知</p>
                      </div>
                    </div>
                    <div class="panel-footer">
                      <el-button type="primary" link @click="goToScheduledTasks">查看全部任务</el-button>
                    </div>
                  </div>
                </div>

                <!-- 其他信息占位 -->
                <div class="header-divider"></div>

                <!-- 用户信息 -->
                <el-dropdown trigger="click" @command="handleUserCommand">
                  <div class="user-dropdown">
                    <div class="user-avatar">
                      {{ userStore.user?.display_name?.charAt(0) || 'U' }}
                    </div>
                    <div class="user-text">
                      <span class="user-name">{{ userStore.user?.display_name }}</span>
                      <el-tag size="small" effect="plain">{{ roleLabel }}</el-tag>
                    </div>
                    <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
                  </div>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="password">
                        <el-icon><Key /></el-icon>
                        <span>修改密码</span>
                      </el-dropdown-item>
                      <el-dropdown-item command="logout" divided>
                        <el-icon><SwitchButton /></el-icon>
                        <span>退出登录</span>
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </el-header>

            <!-- 主内容区 -->
            <el-main>
              <router-view />
            </el-main>
          </el-container>
        </el-container>
      </div>

      <!-- 修改密码对话框 -->
      <el-dialog v-model="passwordDialog" title="修改密码" width="400px">
        <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-width="80px">
          <el-form-item label="旧密码" prop="old_password">
            <el-input v-model="passwordForm.old_password" type="password" show-password />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="passwordForm.new_password" type="password" show-password />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirm_password">
            <el-input v-model="passwordForm.confirm_password" type="password" show-password />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="passwordDialog = false">取消</el-button>
          <el-button type="primary" @click="handleChangePassword" :loading="passwordLoading">确定</el-button>
        </template>
      </el-dialog>
    </template>
  </el-config-provider>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification, type FormInstance, type FormRules } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import {
  Box,
  User,
  Link,
  Tools,
  Cpu,
  Monitor,
  CircleCheck,
  ChatDotRound,
  Document,
  Setting,
  EditPen,
  Lock,
  Avatar,
  Reading,
  ArrowDown,
  RefreshRight,
  Refresh,
  Key,
  SwitchButton,
  UserFilled,
  Odometer,
  MagicStick,
  Collection,
  Promotion,
  Lightning,
  OfficeBuilding,
  Connection,
  ChatLineSquare,
  Picture,
  Memo,
  Clock,
  Bell,
  SuccessFilled,
  CircleCloseFilled,
  Loading,
  Tickets,
  Notebook
} from '@element-plus/icons-vue'
import { useUserStore } from './stores/user'
import { gatewayApi, authApi, scheduledTaskApi, type TaskExecution } from './api'
import { getSSEClient, SSEEventTypes } from './utils/sse-client'
import logoImg from './assets/images/logo.png'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
const gatewayStatus = ref<'online' | 'error' | 'unknown'>('unknown')
const gatewayName = ref('')
const refreshing = ref(false)
const showGatewayPanel = ref(false)

// 通知中心
const showNotifications = ref(false)
const notificationsLoading = ref(false)
const notifications = ref<TaskExecution[]>([])
const unreadCount = ref(0)
let notificationTimer: ReturnType<typeof setInterval> | null = null
const NOTIFICATION_INTERVAL = 60000 // 1分钟轮询

const isAdmin = computed(() => userStore.user?.role === 'admin')

// Gateway 状态轮询
let statusTimer: ReturnType<typeof setInterval> | null = null
const STATUS_CHECK_INTERVAL = 60000 // 60秒检查一次

// SSE 连接
const sseConnected = ref(false)

const roleLabel = computed(() => {
  const roles: Record<string, string> = {
    admin: '管理员',
    operator: '运维',
    viewer: '访客'
  }
  return roles[userStore.user?.role || ''] || userStore.user?.role
})

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    '/dashboard': '团队工作台',
    '/messages': '消息',
    '/feishu-chat': '飞书聊天',
    '/chat': 'Agent 对话',
    '/group-chat': '群聊讨论',
    '/employees': '员工卡片',
    '/departments': '部门管理',
    '/agent-gallery': 'Agent 档案',
    '/agents': 'Agent 配置',
    '/souls': '灵魂管理',
    '/soul-inject': '灵魂注入',
    '/skills-list': '技能配置',
    '/templates': 'Agent 模板',
    '/bindings': '渠道绑定',
    '/tools': '工具配置',
    '/models': 'OpenClaw用模型配置',
    '/memories': '记忆管理',
    '/knowledge-base': '知识库',
    '/tasks': '任务列表',
    '/scheduled-tasks': '定时任务',
    '/image-generator': '图片生成',
    '/status': '运行状态',
    '/sessions': '会话列表',
    '/openclaw-logs': 'OpenClaw 日志',
    '/admin-logs': 'Admin 日志',
    '/operation-logs': '操作日志',
    '/config': '配置编辑',
    '/gateways': 'Gateway 管理',
    '/security': '安全设置',
    '/users': '用户管理',
    '/model-providers': '系统用模型配置',
    '/docs': '帮助文档'
  }

  // 动态路由匹配
  if (route.path.startsWith('/agent/')) {
    return 'Agent 档案'
  }

  return titles[route.path] || ''
})

// 密码修改
const passwordDialog = ref(false)
const passwordLoading = ref(false)
const passwordFormRef = ref<FormInstance>()
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})
const passwordRules: FormRules = {
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: (_, v, callback) => v === passwordForm.new_password ? callback() : callback(new Error('两次密码不一致')), trigger: 'blur' }
  ]
}

const hasPermission = (resource: string, action: string) => {
  return userStore.hasPermission(resource, action)
}

const toggleGatewayPanel = () => {
  showGatewayPanel.value = !showGatewayPanel.value
}

const checkGatewayStatus = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch('/api/gateways/current', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await response.json()
    if (data.success && data.data) {
      gatewayStatus.value = data.data.status === 'online' ? 'online' : 'error'
      gatewayName.value = data.data.name || ''
    } else {
      gatewayStatus.value = 'unknown'
      gatewayName.value = ''
    }
  } catch {
    gatewayStatus.value = 'unknown'
    gatewayName.value = ''
  }
}

const goToGateways = () => {
  showGatewayPanel.value = false
  router.push('/gateways')
}

const refreshStatus = async () => {
  refreshing.value = true
  await checkGatewayStatus()
  refreshing.value = false
  showGatewayPanel.value = false
}

const handleUserCommand = (command: string) => {
  if (command === 'password') {
    passwordDialog.value = true
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
  } else if (command === 'logout') {
    handleLogout()
  }
}

const handleChangePassword = async () => {
  if (!passwordFormRef.value) return
  await passwordFormRef.value.validate()

  passwordLoading.value = true
  try {
    const res = await authApi.changePassword(passwordForm.old_password, passwordForm.new_password)
    if (res.data.success) {
      ElMessage.success('密码已修改')
      passwordDialog.value = false
    } else {
      ElMessage.error(res.data.error)
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '修改失败')
  } finally {
    passwordLoading.value = false
  }
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' })
    await authApi.logout()
    userStore.clear()
    ElMessage.success('已退出')
    router.push('/login')
  } catch {
    // 用户取消
  }
}

// ==================== 通知中心 ====================

async function loadNotifications() {
  if (!isAdmin.value) return

  try {
    const res = await scheduledTaskApi.getRecentExecutions(10)
    if (res.data.success) {
      notifications.value = res.data.data || []
      unreadCount.value = res.data.unread_count || 0
    }
  } catch (e) {
    console.error('Failed to load notifications:', e)
  }
}

function toggleNotifications() {
  showNotifications.value = !showNotifications.value
  if (showNotifications.value) {
    loadNotifications()
  }
}

function closeNotifications() {
  showNotifications.value = false
}

async function markAllRead() {
  try {
    await scheduledTaskApi.markAllRead()
    unreadCount.value = 0
    notifications.value.forEach(n => n.is_read = true)
  } catch (e) {
    console.error('Failed to mark all read:', e)
  }
}

async function viewNotification(item: TaskExecution) {
  if (!item.is_read) {
    try {
      await scheduledTaskApi.markRead(item.id)
      item.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch (e) {
      console.error('Failed to mark read:', e)
    }
  }
  showNotifications.value = false
  router.push('/scheduled-tasks')
}

function goToScheduledTasks() {
  showNotifications.value = false
  router.push('/scheduled-tasks')
}

function getStatusIcon(status: string) {
  const icons: Record<string, any> = {
    success: SuccessFilled,
    failed: CircleCloseFilled,
    running: Loading
  }
  return icons[status] || CircleCheck
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: '等待中',
    running: '执行中',
    success: '执行成功',
    failed: '执行失败'
  }
  return labels[status] || status
}

function formatNotifTime(time: string): string {
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return date.toLocaleDateString('zh-CN')
}

// SSE 事件处理
function initSSE() {
  if (!isAdmin.value) return

  const sseClient = getSSEClient()

  // 监听任务结果
  sseClient.on(SSEEventTypes.TASK_RESULT, (data: any) => {
    console.log('[SSE] Task result received:', data)

    // 获取任务名称
    const taskName = data.task_name || `任务 #${data.task_id}`

    // 使用 ElNotification 显示更丰富的通知
    if (data.status === 'completed') {
      ElNotification({
        title: '任务执行完成',
        message: `任务「${taskName}」已成功执行完成`,
        type: 'success',
        duration: 5000,
        position: 'top-right',
        onClick: () => {
          // 点击跳转到定时任务页面
          router.push('/scheduled-tasks')
        }
      })
      // 播放提示音
      playNotificationSound('success')
    } else if (data.status === 'failed') {
      ElNotification({
        title: '任务执行失败',
        message: `任务「${taskName}」执行失败: ${data.error || '未知错误'}`,
        type: 'error',
        duration: 0, // 不自动关闭
        position: 'top-right',
        onClick: () => {
          router.push('/scheduled-tasks')
        }
      })
      // 播放提示音
      playNotificationSound('error')
    } else if (data.status === 'aborted') {
      ElNotification({
        title: '任务已中止',
        message: `任务「${taskName}」已被中止`,
        type: 'warning',
        duration: 5000,
        position: 'top-right'
      })
    }

    // 刷新通知列表
    loadNotifications()
  })

  // 监听任务开始
  sseClient.on(SSEEventTypes.TASK_STARTED, (data: any) => {
    console.log('[SSE] Task started:', data)
    const taskName = data.task_name || `任务 #${data.task_id}`
    ElMessage.info(`任务「${taskName}」开始执行`)
  })

  // 监听连接状态
  sseClient.onStatusChange((connected) => {
    sseConnected.value = connected
    if (connected) {
      console.log('[SSE] Connected to server')
    } else {
      console.log('[SSE] Disconnected from server')
    }
  })

  // 连接
  sseClient.connect()
}

// 播放通知声音
function playNotificationSound(type: 'success' | 'error' | 'warning') {
  try {
    // 使用 Web Audio API 生成简单的提示音
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
    const oscillator = audioContext.createOscillator()
    const gainNode = audioContext.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(audioContext.destination)

    // 不同类型使用不同频率
    if (type === 'success') {
      oscillator.frequency.value = 800
      oscillator.type = 'sine'
    } else if (type === 'error') {
      oscillator.frequency.value = 400
      oscillator.type = 'square'
    } else {
      oscillator.frequency.value = 600
      oscillator.type = 'triangle'
    }

    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3)

    oscillator.start(audioContext.currentTime)
    oscillator.stop(audioContext.currentTime + 0.3)
  } catch (e) {
    // 忽略音频播放错误
  }
}

function disconnectSSE() {
  const sseClient = getSSEClient()
  sseClient.disconnect()
}

onMounted(() => {
  // 先从 localStorage 加载用户信息
  userStore.loadFromStorage()

  checkGatewayStatus()
  // 启动状态轮询
  statusTimer = setInterval(checkGatewayStatus, STATUS_CHECK_INTERVAL)

  // 启动通知轮询（仅管理员）
  if (isAdmin.value) {
    loadNotifications()
    notificationTimer = setInterval(loadNotifications, NOTIFICATION_INTERVAL)
  }

  // 启动 SSE 连接（仅管理员）
  initSSE()
})

onUnmounted(() => {
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
  if (notificationTimer) {
    clearInterval(notificationTimer)
    notificationTimer = null
  }

  // 断开 SSE
  disconnectSSE()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.app-container {
  height: 100vh;
  background: #fff;
}

.el-container {
  height: 100%;
}

/* 侧边栏 */
.el-aside {
  background: #fff;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid #f0f0f0;
}

.sidebar-header .logo {
  width: 32px;
  height: 32px;
  margin-right: 10px;
}

.sidebar-header .title {
  font-size: 16px;
  font-weight: 600;
  color: #1890ff;
}

.menu-scrollbar {
  flex: 1;
  overflow: hidden;
}

.sidebar-menu {
  border: none;
}

.sidebar-menu .el-sub-menu .el-sub-menu__title {
  height: 48px;
  line-height: 48px;
}

.sidebar-menu .el-menu-item {
  height: 40px;
  line-height: 40px;
  padding-left: 48px !important;
}

.sidebar-menu .el-menu-item.is-active {
  background: #e6f7ff;
  color: #1890ff;
  border-right: 3px solid #1890ff;
}

/* 顶部 Header */
.app-header {
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
}

.page-title {
  font-size: 16px;
  font-weight: 500;
  color: #333;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* Gateway 状态 */
.gateway-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #fafafa;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  transition: background 0.2s;
}

.gateway-info:hover {
  background: #f5f5f5;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.running, .status-dot.online {
  background: #52c41a;
  box-shadow: 0 0 6px rgba(82, 196, 26, 0.6);
}

.status-dot.stopped, .status-dot.error {
  background: #ff4d4f;
}

.status-dot.unknown {
  background: #faad14;
}

.gateway-label {
  font-size: 13px;
  color: #666;
}

.gateway-status-text {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.gateway-arrow {
  font-size: 12px;
  color: #999;
}

.gateway-panel {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: #fff;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 100;
  min-width: 140px;
  overflow: hidden;
}

.panel-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.panel-item:hover {
  background: #f5f5f5;
}

.panel-item span {
  font-size: 13px;
  color: #333;
}

/* 通知中心 */
.notification-center {
  position: relative;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.notification-center:hover {
  background: #f5f5f5;
}

.notification-panel {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  width: 360px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  z-index: 100;
  overflow: hidden;
}

.notification-panel .panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  font-weight: 500;
}

.notification-panel .panel-body {
  max-height: 400px;
  overflow-y: auto;
}

.notification-item {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.notification-item:hover {
  background: #fafafa;
}

.notification-item.unread {
  background: #f0f7ff;
}

.notif-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
}

.notif-icon .success {
  color: #52c41a;
}

.notif-icon .failed {
  color: #ff4d4f;
}

.notif-icon .running {
  color: #1890ff;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.notif-content {
  flex: 1;
  min-width: 0;
}

.notif-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notif-desc {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.notif-desc .status-text.success {
  color: #52c41a;
}

.notif-desc .status-text.failed {
  color: #ff4d4f;
}

.notif-desc .status-text.running {
  color: #1890ff;
}

.notif-time {
  color: #999;
}

.empty-notif {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: #c0c4cc;
}

.empty-notif p {
  margin-top: 8px;
  font-size: 13px;
}

.notification-panel .panel-footer {
  padding: 12px 16px;
  border-top: 1px solid #f0f0f0;
  text-align: center;
}

.header-divider {
  width: 1px;
  height: 24px;
  background: #e8e8e8;
}

/* 用户下拉 */
.user-dropdown {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.user-dropdown:hover {
  background: #f5f5f5;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1890ff, #36cfc9);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 500;
}

.user-text {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-name {
  font-size: 14px;
  color: #333;
}

.dropdown-arrow {
  font-size: 12px;
  color: #999;
}

/* 主内容区 */
.el-main {
  padding: 20px;
  background: #fff;
  overflow-y: auto;
}

/* 下拉菜单图标对齐 */
.el-dropdown-menu__item {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>

<!-- 全局样式：确保 ElMessage 在弹窗遮罩之上 -->
<style>
.el-message {
  z-index: 3000 !important;
}
</style>