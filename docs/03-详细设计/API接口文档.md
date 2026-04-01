# API 接口文档

## 基础信息

- **Base URL**: `http://127.0.0.1:5001/api`
- **认证方式**: JWT Bearer Token
- **Content-Type**: `application/json`

---

## 认证 API

### 登录

```
POST /auth/login
```

**请求体**:
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbG...",
    "refresh_token": "eyJhbG...",
    "user": {
      "id": 1,
      "username": "admin",
      "display_name": "系统管理员",
      "role": "admin",
      "permissions": { "agents": ["read", "write", "delete"], ... }
    }
  },
  "message": "登录成功"
}
```

### 刷新 Token

```
POST /auth/refresh
```

**请求体**:
```json
{
  "refresh_token": "eyJhbG..."
}
```

### 获取当前用户

```
GET /auth/me
Authorization: Bearer <access_token>
```

### 修改密码

```
POST /auth/change-password
Authorization: Bearer <access_token>
```

**请求体**:
```json
{
  "old_password": "旧密码",
  "new_password": "新密码"
}
```

### 登出

```
POST /auth/logout
Authorization: Bearer <access_token>
```

---

## 用户管理 API

### 获取用户列表

```
GET /users
Authorization: Bearer <access_token>
权限: users:read
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "username": "admin",
      "email": "admin@openclaw.local",
      "display_name": "系统管理员",
      "is_active": true,
      "last_login": "2026-03-30 10:00:00",
      "created_at": "2026-03-30 12:00:00",
      "role_name": "admin"
    }
  ]
}
```

### 创建用户

```
POST /users
Authorization: Bearer <access_token>
权限: users:write
```

**请求体**:
```json
{
  "username": "newuser",
  "password": "password123",
  "email": "user@example.com",
  "display_name": "新用户",
  "role_id": 3
}
```

### 更新用户

```
PUT /users/:id
Authorization: Bearer <access_token>
权限: users:write
```

### 删除用户

```
DELETE /users/:id
Authorization: Bearer <access_token>
权限: users:delete
```

---

## Agent API

### 获取 Agent 列表

```
GET /agents
Authorization: Bearer <access_token>
权限: agents:read
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": "main",
      "name": "主助手",
      "model": { "primary": "gpt-4" },
      "modelName": "GPT-4",
      "workspace": "/path/to/workspace",
      "default": true
    }
  ],
  "models": [...],
  "permissions": { "can_edit": true, "can_delete": false }
}
```

### 创建 Agent

```
POST /agents
Authorization: Bearer <access_token>
权限: agents:write
```

**请求体**:
```json
{
  "id": "my-agent",
  "name": "我的助手",
  "model": { "primary": "gpt-4" },
  "workspace": "/optional/custom/path"
}
```

### 更新 Agent

```
PUT /agents/:id
Authorization: Bearer <access_token>
权限: agents:write
```

### 删除 Agent

```
DELETE /agents/:id
Authorization: Bearer <access_token>
权限: agents:delete
```

### 应用配置

```
POST /agents/apply
Authorization: Bearer <access_token>
权限: gateway:restart
```

---

## 任务统计 API

### 获取概览数据

```
GET /tasks/overview
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "success": true,
  "data": {
    "todayTotal": 47,
    "todayChange": 18,
    "completionRate": 92,
    "avgDuration": 150,
    "inProgress": 3
  }
}
```

### 获取趋势数据

```
GET /tasks/trend?days=7
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "success": true,
  "data": {
    "labels": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
    "values": [35, 42, 38, 45, 47, 28, 12],
    "total": 247,
    "change": 23
  }
}
```

### 获取员工排行

```
GET /tasks/ranking?days=7&limit=5
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "agentId": "main",
      "agentName": "主助手",
      "taskCount": 47,
      "successRate": 98
    }
  ]
}
```

### 获取任务类型分布

```
GET /tasks/type-distribution?days=7
Authorization: Bearer <access_token>
```

### 获取最近任务

```
GET /tasks/recent?limit=10
Authorization: Bearer <access_token>
```

### Agent 上报任务

```
POST /tasks/report
Authorization: Bearer <access_token>
```

**请求体**:
```json
{
  "agentId": "main",
  "title": "生成《销售周报》PDF",
  "taskType": "report",
  "deliverableType": "pdf",
  "deliverablePath": "/files/reports/销售周报.pdf",
  "durationSeconds": 120,
  "userId": "user_123",
  "sessionId": "session_456"
}
```

**响应**:
```json
{
  "success": true,
  "data": { "taskId": 123 }
}
```

---

## Gateway API

### 获取状态

```
GET /gateway/status
Authorization: Bearer <access_token>
权限: status:read
```

**响应**:
```json
{
  "status": "ok",
  "message": "Gateway 运行中"
}
```

### 重启 Gateway

```
POST /gateway/restart
Authorization: Bearer <access_token>
权限: gateway:restart
```

### 重载配置

```
POST /gateway/reload
Authorization: Bearer <access_token>
权限: gateway:reload
```

---

## 绑定管理 API

### 获取绑定列表

```
GET /bindings
Authorization: Bearer <access_token>
权限: bindings:read
```

### 创建绑定

```
POST /bindings
Authorization: Bearer <access_token>
权限: bindings:write
```

**请求体**:
```json
{
  "agentId": "main",
  "match": {
    "channelId": "wechat",
    "chatId": "group_123"
  }
}
```

---

## 配置 API

### 获取完整配置

```
GET /config
Authorization: Bearer <access_token>
权限: config:read
```

---

## 操作日志 API

### 获取操作日志

```
GET /logs/operations?page=1&limit=50
Authorization: Bearer <access_token>
权限: logs:read
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "action": "login",
      "resource": "user",
      "resource_id": "1",
      "details": null,
      "ip_address": "127.0.0.1",
      "username": "admin",
      "created_at": "2026-03-30 10:00:00"
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 50
}
```

---

## 错误响应

所有错误响应格式：

```json
{
  "success": false,
  "error": "错误信息描述"
}
```

**HTTP 状态码**:
- 400: 请求参数错误
- 401: 未认证或 Token 过期
- 403: 无权限
- 404: 资源不存在
- 500: 服务器内部错误