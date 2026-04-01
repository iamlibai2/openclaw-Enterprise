# DES-075 - OpenClaw 全流程配置能力详细设计

## 基本信息

| 项目 | 内容 |
|------|------|
| 设计编号 | DES-075 |
| 关联需求 | REQ-075 |
| 设计日期 | 2026-04-01 16:50 |
| 设计人 | 助手 |
| 当前状态 | 📝 设计中 |
| 目标版本 | v1.2.0 |

---

## 一、功能设计

### 1.1 功能模块总览

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenClaw 全流程配置                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  模型管理    │  │  渠道向导    │  │  配置预览           │  │
│  │  Model CRUD │  │  Channel    │  │  Config Preview    │  │
│  │             │  │  Wizard     │  │                    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              API Key 加密存储                         │   │
│  │              Secure Storage                          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 模型管理模块

#### 1.2.1 功能清单

| 功能 | 描述 | API | 前端页面 |
|------|------|-----|----------|
| 模型列表 | 获取所有模型配置 | `GET /api/models` | Models.vue |
| 模型添加 | 新增模型配置 | `POST /api/models` | Models.vue |
| 模型编辑 | 修改模型配置 | `PUT /api/models/<id>` | Models.vue |
| 模型删除 | 删除模型 | `DELETE /api/models/<id>` | Models.vue |
| 模型测试 | 测试 API 连通性 | `POST /api/models/<id>/test` | Models.vue |

#### 1.2.2 模型提供商模板

```json
{
  "providers": {
    "bailian": {
      "name": "阿里云百炼",
      "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "models": ["qwen-turbo", "qwen-plus", "qwen-max"],
      "auth_type": "api_key"
    },
    "deepseek": {
      "name": "DeepSeek",
      "api_base": "https://api.deepseek.com/v1",
      "models": ["deepseek-chat", "deepseek-coder"],
      "auth_type": "api_key"
    },
    "zhipu": {
      "name": "智谱",
      "api_base": "https://open.bigmodel.cn/api/paas/v4",
      "models": ["glm-4", "glm-4-flash"],
      "auth_type": "api_key"
    },
    "kimi": {
      "name": "Kimi (Moonshot)",
      "api_base": "https://api.moonshot.cn/v1",
      "models": ["moonshot-v1-8k", "moonshot-v1-32k"],
      "auth_type": "api_key"
    },
    "minimax": {
      "name": "MiniMax",
      "api_base": "https://api.minimax.chat/v1",
      "models": ["abab6.5-chat", "abab5.5-chat"],
      "auth_type": "api_key"
    }
  }
}
```

#### 1.2.3 模型配置结构

```typescript
interface ModelConfig {
  id: string;                  // 模型标识
  name: string;                // 显示名称
  provider: string;            // 提供商：bailian|deepseek|zhipu|kimi|minimax
  model_type: string;          // 模型类型：chat|embedding
  api_key: string;             // API Key（加密存储）
  api_base?: string;           // API 地址（可选，使用默认）
  model_name: string;          // 模型名称
  parameters?: {               // 模型参数
    temperature?: number;
    max_tokens?: number;
    top_p?: number;
  };
  enabled: boolean;            // 是否启用
  created_at: string;
  updated_at: string;
}
```

### 1.3 渠道配置向导模块

#### 1.3.1 飞书配置向导

**配置步骤**：

```
Step 1: 创建飞书应用
├── 引导用户访问飞书开放平台
├── 创建企业自建应用
└── 获取 App ID 和 App Secret

Step 2: 配置应用权限
├── 开启机器人能力
├── 配置消息卡片权限
└── 配置事件订阅权限

Step 3: 配置事件订阅
├── 输入事件订阅地址
├── 配置消息接收事件
└── 验证订阅有效性

Step 4: 完成配置
├── 输入 App ID 和 App Secret
├── 测试连接
└── 保存配置
```

**飞书配置结构**：

```typescript
interface FeishuConfig {
  app_id: string;              // 应用 ID
  app_secret: string;          // 应用密钥（加密）
  event_url?: string;          // 事件订阅地址
  bot_name?: string;           // 机器人名称
  enabled: boolean;
}
```

#### 1.3.2 钉钉配置向导

**配置步骤**：

```
Step 1: 创建钉钉应用
├── 引导用户访问钉钉开放平台
├── 创建企业内部应用
└── 获取 AppKey 和 AppSecret

Step 2: 配置机器人能力
├── 开启机器人功能
├── 配置消息推送模式
└── 添加机器人到组织

Step 3: 配置回调地址
├── 输入消息回调地址
├── 配置回调签名验证
└── 测试回调接收

Step 4: 完成配置
├── 输入 AppKey 和 AppSecret
├── 测试连接
└── 保存配置
```

**钉钉配置结构**：

```typescript
interface DingtalkConfig {
  app_key: string;             // 应用 Key
  app_secret: string;          // 应用密钥（加密）
  callback_url?: string;       // 回调地址
  agent_id?: string;           // Agent ID
  enabled: boolean;
}
```

### 1.4 API Key 加密存储模块

#### 1.4.1 加密方案

**方案选择**：AES-256-GCM

**密钥管理**：
- 加密密钥存储在环境变量 `OPENCLAW_ENCRYPT_KEY`
- 首次启动自动生成密钥并写入 `.env` 文件
- 密钥丢失将无法解密已存储的敏感信息

#### 1.4.2 加密流程

```
存储流程：
原始值 → AES-256-GCM 加密 → Base64 编码 → 存入数据库

读取流程：
数据库值 → Base64 解码 → AES-256-GCM 解密 → 返回原始值
```

#### 1.4.3 脱敏显示

```typescript
// 显示规则
function maskApiKey(key: string): string {
  if (key.length <= 8) return '****';
  return key.substring(0, 4) + '****' + key.substring(key.length - 4);
}

// 示例
"sk-abc123xyz789" → "sk-a****789"
```

### 1.5 配置预览模块

#### 1.5.1 JSON 预览

- 实时生成 `openclaw.json` 预览
- 显示当前配置的完整结构
- 支持复制和下载

#### 1.5.2 配置检查

检查项：
- [ ] 是否配置了模型
- [ ] 是否配置了 Agent
- [ ] 是否配置了渠道
- [ ] 是否配置了绑定规则
- [ ] API Key 是否填写完整

---

## 二、数据模型设计

### 2.1 数据库表设计

#### 2.1.1 models 表

```sql
CREATE TABLE models (
  id TEXT PRIMARY KEY,           -- 模型标识
  name TEXT NOT NULL,            -- 显示名称
  provider TEXT NOT NULL,        -- 提供商
  model_type TEXT DEFAULT 'chat',-- 模型类型
  api_key_encrypted TEXT,        -- 加密后的 API Key
  api_base TEXT,                 -- API 地址
  model_name TEXT NOT NULL,      -- 模型名称
  parameters TEXT,               -- JSON 格式的参数
  enabled INTEGER DEFAULT 1,     -- 是否启用
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

#### 2.1.2 channel_configs 表

```sql
CREATE TABLE channel_configs (
  id TEXT PRIMARY KEY,           -- 配置标识
  channel_type TEXT NOT NULL,    -- 渠道类型：feishu|dingtalk
  config_encrypted TEXT,         -- 加密后的配置 JSON
  enabled INTEGER DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

### 2.2 配置同步机制

**同步策略**：通过 Gateway WebSocket API 实时同步

```
┌─────────────┐     WebSocket      ┌─────────────┐
│  Admin UI   │ ────────────────── │   Gateway   │
│  Database   │                    │  openclaw.  │
│             │ ────────────────── │    json     │
└─────────────┘    config.patch    └─────────────┘
```

**同步时机**：
- 模型配置变更 → 调用 `config.patch` 更新
- 渠道配置变更 → 调用 `config.patch` 更新
- 定时同步 → 每 5 分钟检查一致性

---

## 三、API 设计

### 3.1 模型管理 API

#### 获取模型列表

```
GET /api/models

Response:
{
  "success": true,
  "data": [
    {
      "id": "model-001",
      "name": "Qwen Turbo",
      "provider": "bailian",
      "model_name": "qwen-turbo",
      "api_key_masked": "sk-a****789",
      "enabled": true
    }
  ]
}
```

#### 创建模型

```
POST /api/models

Request:
{
  "name": "Qwen Turbo",
  "provider": "bailian",
  "model_name": "qwen-turbo",
  "api_key": "sk-abc123xyz789",
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 2000
  }
}

Response:
{
  "success": true,
  "data": {
    "id": "model-001",
    "name": "Qwen Turbo",
    ...
  }
}
```

#### 更新模型

```
PUT /api/models/<id>

Request:
{
  "name": "Qwen Turbo v2",
  "api_key": "sk-newkey123",
  "enabled": true
}
```

#### 删除模型

```
DELETE /api/models/<id>

Response:
{
  "success": true
}
```

#### 测试模型连接

```
POST /api/models/<id>/test

Response:
{
  "success": true,
  "data": {
    "connected": true,
    "response_time": 150,  // ms
    "error": null
  }
}
```

### 3.2 渠道配置 API

#### 获取渠道配置

```
GET /api/channels/<type>/config

Response:
{
  "success": true,
  "data": {
    "app_id_masked": "cli_a****xyz",
    "enabled": true
  }
}
```

#### 保存渠道配置

```
POST /api/channels/<type>/config

Request (飞书):
{
  "app_id": "cli_a12345xyz",
  "app_secret": "secret123",
  "event_url": "https://example.com/webhook"
}

Response:
{
  "success": true,
  "data": {
    "message": "配置已保存并同步到 Gateway"
  }
}
```

### 3.3 配置预览 API

#### 获取配置预览

```
GET /api/config/preview

Response:
{
  "success": true,
  "data": {
    "json": "{\n  \"models\": [...],\n  \"channels\": [...]\n}",
    "check_result": {
      "has_models": true,
      "has_agents": true,
      "has_channels": true,
      "has_bindings": false,
      "complete": false,
      "missing": ["绑定规则"]
    }
  }
}
```

---

## 四、技术方案

### 4.1 加密模块实现

**文件**: `backend/crypto_utils.py`

```python
"""
加密工具模块
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

class CryptoUtils:
    def __init__(self):
        key = os.environ.get('OPENCLAW_ENCRYPT_KEY')
        if not key:
            # 首次启动生成密钥
            key = AESGCM.generate_key(bit_length=256).hex()
            self._save_key_to_env(key)
        self.aesgcm = AESGCM(bytes.fromhex(key))

    def encrypt(self, plaintext: str) -> str:
        """加密并返回 Base64 编码"""
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(nonce + ciphertext).decode()

    def decrypt(self, encrypted: str) -> str:
        """解密 Base64 编码的数据"""
        data = base64.b64decode(encrypted)
        nonce = data[:12]
        ciphertext = data[12:]
        return self.aesgcm.decrypt(nonce, ciphertext, None).decode()

    def _save_key_to_env(self, key: str):
        """保存密钥到 .env 文件"""
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        with open(env_path, 'a') as f:
            f.write(f'\nOPENCLAW_ENCRYPT_KEY={key}\n')
```

### 4.2 模型管理实现

**文件**: `backend/model_manager.py`

```python
"""
模型管理模块
"""
import uuid
from datetime import datetime
from crypto_utils import CryptoUtils

class ModelManager:
    def __init__(self, db, crypto: CryptoUtils):
        self.db = db
        self.crypto = crypto

    def create_model(self, data: dict) -> dict:
        """创建模型配置"""
        model_id = f"model-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()

        # 加密 API Key
        encrypted_key = self.crypto.encrypt(data['api_key'])

        self.db.execute(
            '''INSERT INTO models
               (id, name, provider, model_name, api_key_encrypted, parameters, enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (model_id, data['name'], data['provider'], data['model_name'],
             encrypted_key, json.dumps(data.get('parameters', {})),
             1, now, now)
        )

        # 同步到 Gateway
        self._sync_to_gateway()

        return self.get_model(model_id)

    def get_model(self, model_id: str) -> dict:
        """获取模型配置"""
        row = self.db.execute(
            'SELECT * FROM models WHERE id = ?', (model_id,)
        ).fetchone()

        if row:
            return {
                'id': row['id'],
                'name': row['name'],
                'provider': row['provider'],
                'model_name': row['model_name'],
                'api_key_masked': self._mask_key(row['api_key_encrypted']),
                'enabled': row['enabled']
            }
        return None

    def _mask_key(self, encrypted_key: str) -> str:
        """脱敏显示"""
        decrypted = self.crypto.decrypt(encrypted_key)
        if len(decrypted) <= 8:
            return '****'
        return decrypted[:4] + '****' + decrypted[-4:]
```

### 4.3 前端组件设计

#### Models.vue 页面结构

```vue
<template>
  <div class="models-page">
    <!-- 提供商选择 -->
    <ProviderSelect @select="onProviderSelect" />

    <!-- 模型列表 -->
    <ModelTable
      :models="models"
      @edit="onEdit"
      @delete="onDelete"
      @test="onTest"
    />

    <!-- 模型编辑对话框 -->
    <ModelDialog
      v-model="showDialog"
      :model="currentModel"
      :provider="currentProvider"
      @save="onSave"
    />
  </div>
</template>
```

#### ChannelWizard.vue 向导组件

```vue
<template>
  <div class="channel-wizard">
    <el-steps :active="currentStep" :steps="steps" />

    <!-- Step 1: 创建应用 -->
    <StepCreateApp v-if="currentStep === 0" />

    <!-- Step 2: 配置权限 -->
    <StepConfigPermission v-if="currentStep === 1" />

    <!-- Step 3: 配置回调 -->
    <StepConfigCallback v-if="currentStep === 2" />

    <!-- Step 4: 完成配置 -->
    <StepCompleteConfig v-if="currentStep === 3" />
  </div>
</template>
```

---

## 五、界面设计

### 5.1 模型管理页面

```
┌─────────────────────────────────────────────────────────────┐
│  模型管理                                    [+ 添加模型]    │
├─────────────────────────────────────────────────────────────┤
│  提供商筛选：[全部] [百炼] [DeepSeek] [智谱] [Kimi] [MiniMax] │
├─────────────────────────────────────────────────────────────┤
│  ┌─────┬──────────┬────────┬──────────┬────────┬─────────┐  │
│  │ ID  │ 名称      │ 提供商  │ 模型      │ 状态   │ 操作    │  │
│  ├─────┼──────────┼────────┼──────────┼────────┼─────────┤  │
│  │ m01 │ Qwen Turbo│ 百炼   │ qwen-turbo│ 启用   │ 编辑 测试│  │
│  │ m02 │ DeepSeek  │ DeepSeek│ deepseek │ 启用   │ 编辑 测试│  │
│  │ m03 │ GLM-4     │ 智谱   │ glm-4    │ 禁用   │ 编辑 测试│  │
│  └─────┴──────────┴────────┴──────────┴────────┴─────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 模型添加对话框

```
┌─────────────────────────────────────────────────────────────┐
│  添加模型                                                    │
├─────────────────────────────────────────────────────────────┤
│  提供商：     [▼ 阿里云百炼    ]                              │
│              提示：自动填充 API 地址                           │
│                                                             │
│  模型名称：   [▼ qwen-turbo    ]                              │
│              提示：选择提供商后自动列出可用模型                 │
│                                                             │
│  显示名称：   [Qwen Turbo    ]                                │
│                                                             │
│  API Key：    [sk-************]  [👁 显示]                   │
│              提示：从提供商平台获取                            │
│                                                             │
│  参数配置（可选）：                                           │
│  Temperature: [0.7        ]                                  │
│  Max Tokens:  [2000       ]                                  │
│                                                             │
│                                    [取消]  [保存并测试]       │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 飞书配置向导

```
┌─────────────────────────────────────────────────────────────┐
│  飞书应用配置向导                                            │
├─────────────────────────────────────────────────────────────┤
│  ┌───┐  Step 1: 创建飞书应用                                 │
│  │ 1 ├─────────────────────────────────────────────────────│
│  └───┤                                                      │
│      │  1. 访问飞书开放平台                                   │
│      │     [打开飞书开放平台 ↗]                               │
│      │                                                      │
│      │  2. 创建企业自建应用                                   │
│      │     应用类型：企业自建应用                              │
│      │     应用名称：[输入应用名称]                            │
│      │                                                      │
│      │  3. 获取凭证                                          │
│      │     App ID:     [cli_a********    ]                   │
│      │     App Secret: [**************    ]                  │
│      │                                                      │
│      │                                    [下一步]           │
│  ┌───┐  Step 2: 配置应用权限                                 │
│  │ 2 ├─────────────────────────────────────────────────────│
│  └───┤  ...                                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、实现计划

### 6.1 任务分解

| 任务编号 | 任务名称 | 工时预估 | 优先级 |
|----------|----------|----------|--------|
| T054 | 加密模块实现 | 2h | P0 |
| T055 | 模型管理后端 API | 4h | P0 |
| T056 | 模型管理前端页面 | 4h | P0 |
| T057 | 模型提供商模板 | 2h | P1 |
| T058 | 模型测试功能 | 2h | P1 |
| T059 | 飞书配置向导 | 4h | P0 |
| T060 | 钉钉配置向导 | 4h | P0 |
| T061 | 配置预览功能 | 2h | P1 |
| T062 | 配置检查功能 | 2h | P1 |
| T063 | Gateway 同步机制 | 3h | P0 |
| T064 | 整体测试 | 3h | P0 |

**总工时预估**：32h

### 6.2 开发顺序

```
Week 1:
  Day 1-2: T054 加密模块 + T055 模型后端 API
  Day 3-4: T056 模型前端页面 + T057 提供商模板

Week 2:
  Day 1-2: T059 飞书向导 + T060 钉钉向导
  Day 3: T063 Gateway 同步
  Day 4: T061 配置预览 + T062 配置检查

Week 3:
  Day 1-2: T058 模型测试 + T064 整体测试
  Day 3: Bug 修复 + 文档完善
```

---

## 七、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 加密密钥丢失 | 无法解密敏感信息 | 密钥备份，提示用户保存 |
| Gateway 连接失败 | 配置无法同步 | 本地缓存，定时重试 |
| API Key 泄露 | 安全风险 | 加密存储，脱敏显示，审计日志 |
| 提供商 API 变更 | 测试失败 | 模板可更新，错误提示 |

---

## 八、验收标准

- [ ] 模型管理：可添加/编辑/删除模型
- [ ] 模型加密：API Key 加密存储
- [ ] 模型脱敏：界面显示脱敏，支持查看明文
- [ ] 模型测试：可测试 API 连通性
- [ ] 提供商模板：支持 5 个提供商模板
- [ ] 飞书向导：完整引导 4 步配置
- [ ] 钉钉向导：完整引导 4 步配置
- [ ] 配置预览：可预览生成的 JSON
- [ ] 配置检查：可检查配置完整性
- [ ] Gateway 同步：配置变更自动同步

---

## 变更记录

| 日期 | 变更内容 | 变更人 |
|------|----------|--------|
| 2026-04-01 16:50 | 初始版本 | 助手 |