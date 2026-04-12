import { createRouter, createWebHistory } from 'vue-router'
import { Login, Register, StaffHome } from '../user'
import { useUserStore } from '../user/stores'
import Agents from '../views/Agents.vue'
import { ChatPage, DiscordChat, FeishuChat } from '../chat'
import { GroupChatPage } from '../group-chat'
import { SmartChat } from '../smart-chat'
import { AgentProfilePage, AgentGalleryPage } from '../agent'
import { TasksPage } from '../tasks'
import { WorkflowPage } from '../workflow'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Root',
    redirect: (to) => {
      const userStore = useUserStore()
      userStore.loadFromStorage()
      if (userStore.user?.role === 'staff') {
        return '/staff-home'
      }
      return '/dashboard'
    }
  },
  // 首页仪表盘
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'operator'] }
  },
  // 员工首页（staff 角色专用）
  {
    path: '/staff-home',
    name: 'StaffHome',
    component: StaffHome,
    meta: { requiresAuth: true, roles: ['staff'] }
  },
  // 消息（Discord 风格）
  {
    path: '/messages',
    name: 'Messages',
    component: DiscordChat,
    meta: { requiresAuth: true, permission: 'sessions:read' }
  },
  // 飞书聊天
  {
    path: '/feishu-chat',
    name: 'FeishuChat',
    component: FeishuChat,
    meta: { requiresAuth: true, permission: 'sessions:read' }
  },
  // Agent 对话（原版）
  {
    path: '/chat',
    name: 'Chat',
    component: ChatPage,
    meta: { requiresAuth: true, permission: 'sessions:read' }
  },
  // 智能聊天
  {
    path: '/smart-chat',
    name: 'SmartChat',
    component: SmartChat,
    meta: { requiresAuth: true, permission: 'sessions:read' }
  },
  // Agent 群聊
  {
    path: '/group-chat',
    name: 'GroupChat',
    component: GroupChatPage,
    meta: { requiresAuth: true, permission: 'sessions:read' }
  },
  // 员工管理（一级菜单）
  {
    path: '/employees',
    name: 'Employees',
    component: () => import('../views/Employees.vue'),
    meta: { requiresAuth: true, permission: 'agents:read' }
  },
  {
    path: '/departments',
    name: 'Departments',
    component: () => import('../views/Departments.vue'),
    meta: { requiresAuth: true, permission: 'employees:read' }
  },
  // 系统管理
  {
    path: '/agents',
    name: 'Agents',
    component: Agents,
    meta: { requiresAuth: true, permission: 'agents:read' }
  },
  {
    path: '/souls',
    name: 'Souls',
    component: () => import('../views/Souls.vue'),
    meta: { requiresAuth: true, permission: 'agents:read' }
  },
  {
    path: '/soul-inject',
    name: 'SoulInject',
    component: () => import('../views/SoulInject.vue'),
    meta: { requiresAuth: true, permission: 'config:write' }
  },
  {
    path: '/templates',
    name: 'Templates',
    component: () => import('../views/Templates.vue'),
    meta: { requiresAuth: true, permission: 'config:read' }
  },
  {
    path: '/skills-list',
    name: 'Skills',
    component: () => import('../views/Skills.vue'),
    meta: { requiresAuth: true, permission: 'skills:read' }
  },
  {
    path: '/bindings',
    name: 'Bindings',
    component: () => import('../views/Bindings.vue'),
    meta: { requiresAuth: true, permission: 'bindings:read' }
  },
  {
    path: '/tools',
    name: 'Tools',
    component: () => import('../views/Tools.vue'),
    meta: { requiresAuth: true, permission: 'tools:read' }
  },
  {
    path: '/models',
    name: 'Models',
    component: () => import('../views/Models.vue'),
    meta: { requiresAuth: true, permission: 'models:read' }
  },
  // 知识管理
  {
    path: '/knowledge-base',
    name: 'KnowledgeBase',
    component: () => import('../views/KnowledgeBase.vue'),
    meta: { requiresAuth: true }
  },
  // 记忆管理
  {
    path: '/memories',
    name: 'Memories',
    component: () => import('../views/Memories.vue'),
    meta: { requiresAuth: true, permission: 'memories:read' }
  },
  // Agent Profile
  {
    path: '/agent-gallery',
    name: 'AgentGallery',
    component: AgentGalleryPage,
    meta: { requiresAuth: true, permission: 'agents:read' }
  },
  {
    path: '/agent/:id',
    name: 'AgentProfile',
    component: AgentProfilePage,
    meta: { requiresAuth: true, permission: 'agents:read' }
  },
  // Agent 朋友圈
  {
    path: '/moments',
    name: 'Moments',
    component: () => import('../views/Moments.vue'),
    meta: { requiresAuth: true }
  },
  // 工作流编排
  {
    path: '/workflows',
    name: 'Workflows',
    component: WorkflowPage,
    meta: { requiresAuth: true }
  },
  // 工作管理
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('../views/Tasks.vue'),
    meta: { requiresAuth: true }
  },
  // 定时任务
  {
    path: '/scheduled-tasks',
    name: 'ScheduledTasks',
    component: TasksPage,
    meta: { requiresAuth: true, permission: 'tasks:read' }
  },
  // 监控与状态
  {
    path: '/status',
    name: 'Status',
    component: () => import('../views/Status.vue'),
    meta: { requiresAuth: true, permission: 'status:read' }
  },
  {
    path: '/sessions',
    name: 'Sessions',
    component: () => import('../views/Sessions.vue'),
    meta: { requiresAuth: true, permission: 'sessions:read' }
  },
  // OpenClaw 运行日志
  {
    path: '/openclaw-logs',
    name: 'OpenclawLogs',
    component: () => import('../views/OpenclawLogs.vue'),
    meta: { requiresAuth: true, permission: 'logs:read' }
  },
  // Admin UI 运行日志
  {
    path: '/admin-logs',
    name: 'AdminLogs',
    component: () => import('../views/AdminLogs.vue'),
    meta: { requiresAuth: true, permission: 'logs:read' }
  },
  // 操作日志
  {
    path: '/operation-logs',
    name: 'OperationLogs',
    component: () => import('../views/OperationLogs.vue'),
    meta: { requiresAuth: true, permission: 'logs:read' }
  },
  // 系统设置
  {
    path: '/config',
    name: 'Config',
    component: () => import('../views/Config.vue'),
    meta: { requiresAuth: true, permission: 'config:read' }
  },
  {
    path: '/gateways',
    name: 'Gateways',
    component: () => import('../views/Gateways.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/channels',
    name: 'Channels',
    component: () => import('../views/Channels.vue'),
    meta: { requiresAuth: true, permission: 'config:read' }
  },
  {
    path: '/security',
    name: 'Security',
    component: () => import('../views/Security.vue'),
    meta: { requiresAuth: true, permission: 'security:read' }
  },
  {
    path: '/users',
    name: 'Users',
    component: () => import('../views/Users.vue'),
    meta: { requiresAuth: true, permission: 'users:read' }
  },
  // 快捷入口
  {
    path: '/docs',
    name: 'Docs',
    component: () => import('../views/Docs.vue'),
    meta: { requiresAuth: true }
  },
  // AI 工具
  {
    path: '/image-generator',
    name: 'ImageGenerator',
    component: () => import('../views/ImageGenerator.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/model-providers',
    name: 'ModelProviders',
    component: () => import('../views/ModelProviders.vue'),
    meta: { requiresAuth: true }
  },
  // 403 无权限
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('../views/Forbidden.vue'),
    meta: { requiresAuth: false }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()

  // 从 localStorage 加载用户信息
  if (!userStore.user) {
    userStore.loadFromStorage()
  }

  // 不需要认证的路由
  if (to.meta.requiresAuth === false) {
    // 访问登录页时，先清除旧的认证数据
    if (to.path === '/login') {
      userStore.clear()
      return next()
    }
    return next()
  }

  // 需要认证但未登录
  if (!userStore.isLoggedIn) {
    return next('/login')
  }

  // 角色检查
  const userRole = userStore.user?.role
  const allowedRoles = to.meta.roles as string[] | undefined

  if (allowedRoles && userRole && !allowedRoles.includes(userRole)) {
    // staff 用户访问 admin 路由时，重定向到 staff-home
    if (userRole === 'staff') {
      return next('/staff-home')
    }
    // admin/operator 访问 staff 路由时，重定向到 dashboard
    if (userRole === 'admin' || userRole === 'operator') {
      return next('/dashboard')
    }
    return next('/403')
  }

  // 检查权限
  if (to.meta.permission) {
    const [resource, action] = (to.meta.permission as string).split(':')
    if (!userStore.hasPermission(resource, action)) {
      return next('/403')
    }
  }

  next()
})

export default router