# OpenClaw Admin UI 开发日志

## 2026-03-30 企业级用户管理和权限系统开发

### 开发内容

#### 1. 后端数据库和认证基础
- 创建 `backend/database.py` - SQLite 数据库管理
  - 用户表 (users): id, username, password_hash, email, display_name, role_id, is_active, last_login, created_at, updated_at
  - 角色表 (roles): id, name, description, permissions (JSON)
  - Refresh Token 表 (refresh_tokens)
  - 操作日志表 (operation_logs)
  - 初始化默认角色: admin, operator, viewer
  - 初始化默认管理员账户: admin / admin123

- 创建 `backend/auth.py` - JWT 认证和密码处理
  - bcrypt 密码哈希
  - JWT Token 生成 (access_token + refresh_token)
  - Token 验证和刷新机制
  - access_token 有效期 30 分钟
  - refresh_token 有效期 7 天

- 更新 `backend/requirements.txt`
  - 新增 PyJWT>=2.0.0
  - 新增 bcrypt>=4.0.0

#### 2. 后端认证 API
- 创建 `backend/decorators.py` - 权限装饰器
  - @require_auth: 需要登录验证
  - @require_permission(resource, action): 需要特定权限
  - has_permission(): 权限检查函数
  - log_operation(): 操作日志记录

- 修改 `backend/app.py` - 新增认证和用户管理 API
  - POST `/api/auth/login` - 登录
  - POST `/api/auth/logout` - 登出
  - GET `/api/auth/me` - 获取当前用户信息
  - POST `/api/auth/refresh` - 刷新 Token
  - POST `/api/auth/change-password` - 修改密码
  - GET `/api/users` - 用户列表
  - POST `/api/users` - 创建用户
  - PUT `/api/users/:id` - 更新用户
  - DELETE `/api/users/:id` - 删除用户
  - GET `/api/roles` - 角色列表
  - PUT `/api/roles/:id` - 更新角色权限
  - GET `/api/logs/operations` - 操作日志

#### 3. 保护现有 API
- 所有现有 API 添加权限检查
- `/api/health` 保持公开
- `/api/auth/*` 保持公开
- Agent、绑定、模型、配置、Gateway API 都添加权限验证

#### 4. 前端登录和状态管理
- 创建 `frontend/src/views/Login.vue` - 登录页面
- 创建 `frontend/src/stores/user.ts` - Pinia 用户状态管理
  - 用户信息存储
  - Token 管理
  - 权限检查方法
  - localStorage 持久化

- 更新 `frontend/src/api/index.ts`
  - 新增认证 API (authApi)
  - 新增用户管理 API (userApi)
  - 新增角色管理 API (roleApi)
  - 新增 Gateway API (gatewayApi)
  - 新增操作日志 API (logApi)
  - 请求拦截器添加 Authorization Header
  - 响应拦截器处理 401 自动刷新 Token

#### 5. 前端路由守卫
- 修改 `frontend/src/router/index.ts`
  - 添加 beforeEach 路由守卫
  - 未登录重定向到 /login
  - 无权限重定向到 /403
  - 添加 meta.permission 权限标识

- 修改 `frontend/src/App.vue`
  - 根据权限显示/隐藏菜单项
  - 显示用户信息和角色
  - 添加登出按钮
  - Gateway 控制按钮权限控制

#### 6. 用户管理页面
- 创建 `frontend/src/views/Users.vue` - 用户管理界面
  - 用户列表表格
  - 创建/编辑用户对话框
  - 权限控制按钮显示
- 创建 `frontend/src/views/Forbidden.vue` - 403 无权限页面

### 权限矩阵

| 功能 | admin | operator | viewer |
|------|-------|----------|--------|
| Agent 管理 (CRUD) | ✓ | ✓ | 只读 |
| 绑定配置 (CRUD) | ✓ | ✓ | 只读 |
| 工具配置 | ✓ | ✓ | 只读 |
| 模型配置 | ✓ | ✓ | 只读 |
| 运行状态 | ✓ | ✓ | ✓ |
| 会话列表 | ✓ | ✓ | ✓ |
| 日志查看 | ✓ | ✓ | ✓ |
| 配置编辑 | ✓ | - | 只读 |
| 安全设置 | ✓ | - | - |
| 用户管理 | ✓ | - | - |
| Gateway 控制 | ✓ | ✓ | - |

### 默认账户
- 用户名: admin
- 密码: admin123
- 角色: admin

### 修复记录

#### 导入路径问题修复
- App.vue 中的 `../stores/user` 改为 `./stores/user`（App.vue 在 src/ 根目录）
- api/index.ts 移除对 useUserStore 的依赖，直接使用 localStorage 避免循环依赖

### 技术栈
- 后端: Flask + SQLite + PyJWT + bcrypt
- 前端: Vue 3 + TypeScript + Element Plus + Pinia

### 数据库位置
- ~/.openclaw/admin.db

### 服务地址
- 后端 API: http://127.0.0.1:5001
- 前端 UI: http://localhost:5000