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
                :default-openeds="['organization', 'workflow', 'experience', 'knowledge', 'security-menu', 'monitor', 'openclaw', 'settings']"
                router
                class="sidebar-menu"
              >
                <!-- 首页仪表盘 -->
                <el-menu-item index="/dashboard">
                  <el-icon><Odometer /></el-icon>
                  <span>工作台</span>
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
                  <el-menu-item index="/skills-list" v-if="hasPermission('skills', 'read')">
                    <el-icon><Lightning /></el-icon>
                    <span>Skill 列表</span>
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
                  <el-menu-item index="/logs" v-if="hasPermission('logs', 'read')">
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
                  <el-menu-item index="/agents" v-if="hasPermission('agents', 'read')">
                    <el-icon><User /></el-icon>
                    <span>Agent 管理</span>
                  </el-menu-item>
                  <el-menu-item index="/souls" v-if="hasPermission('agents', 'read')">
                    <el-icon><MagicStick /></el-icon>
                    <span>灵魂管理</span>
                  </el-menu-item>
                  <el-menu-item index="/soul-inject" v-if="hasPermission('config', 'write')">
                    <el-icon><Promotion /></el-icon>
                    <span>灵魂注入</span>
                  </el-menu-item>
                  <el-menu-item index="/templates" v-if="hasPermission('config', 'read')">
                    <el-icon><Collection /></el-icon>
                    <span>模板管理</span>
                  </el-menu-item>
                  <el-menu-item index="/config" v-if="hasPermission('config', 'read')">
                    <el-icon><EditPen /></el-icon>
                    <span>配置编辑</span>
                  </el-menu-item>
                  <el-menu-item index="/bindings" v-if="hasPermission('bindings', 'read')">
                    <el-icon><Link /></el-icon>
                    <span>绑定配置</span>
                  </el-menu-item>
                  <el-menu-item index="/tools" v-if="hasPermission('tools', 'read')">
                    <el-icon><Tools /></el-icon>
                    <span>工具配置</span>
                  </el-menu-item>
                  <el-menu-item index="/models" v-if="hasPermission('models', 'read')">
                    <el-icon><Cpu /></el-icon>
                    <span>模型配置</span>
                  </el-menu-item>
                  <el-menu-item index="/channels" v-if="hasPermission('config', 'read')">
                    <el-icon><ChatLineSquare /></el-icon>
                    <span>Channel 管理</span>
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
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
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
  Picture
} from '@element-plus/icons-vue'
import { useUserStore } from './stores/user'
import { gatewayApi, authApi } from './api'
import logoImg from './assets/images/logo.png'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
const gatewayStatus = ref<'online' | 'error' | 'unknown'>('unknown')
const gatewayName = ref('')
const refreshing = ref(false)
const showGatewayPanel = ref(false)

// Gateway 状态轮询
let statusTimer: ReturnType<typeof setInterval> | null = null
const STATUS_CHECK_INTERVAL = 60000 // 60秒检查一次

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
    '/employees': '员工卡片',
    '/departments': '部门管理',
    '/agents': 'Agent 管理',
    '/souls': '灵魂管理',
    '/soul-inject': '灵魂注入',
    '/templates': '模板管理',
    '/skills-list': 'Skill 列表',
    '/bindings': '绑定配置',
    '/tools': '工具配置',
    '/models': '模型配置',
    '/knowledge-base': '知识库',
    '/tasks': '任务列表',
    '/status': '运行状态',
    '/sessions': '会话列表',
    '/logs': '操作日志',
    '/config': '配置编辑',
    '/gateways': 'Gateway 管理',
    '/security': '安全设置',
    '/users': '用户管理',
    '/docs': '帮助文档'
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

onMounted(() => {
  checkGatewayStatus()
  // 启动状态轮询
  statusTimer = setInterval(checkGatewayStatus, STATUS_CHECK_INTERVAL)
})

onUnmounted(() => {
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
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