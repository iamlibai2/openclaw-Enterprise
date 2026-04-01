import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'
import Agents from '../views/Agents.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    redirect: '/dashboard'
  },
  // 首页仪表盘
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true }
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
  // 工作管理
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('../views/Tasks.vue'),
    meta: { requiresAuth: true }
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
  {
    path: '/logs',
    name: 'Logs',
    component: () => import('../views/Logs.vue'),
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