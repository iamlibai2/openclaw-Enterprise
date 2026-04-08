# Bug 管理记录

本文档记录开发过程中遇到的 Bug 及其解决方案。

---

## BUG-001: 登录页疯狂刷新无法登录

**发现日期**: 2026-03-30

**严重程度**: P0（阻塞功能）

**现象**:
- 访问登录页后页面疯狂刷新
- 无法正常登录系统
- 浏览器控制台无报错

**根本原因**:

前端路由守卫和 API 拦截器配合问题，导致死循环：

```
1. localStorage 中存在过期的 token（上次登录残留）

2. 访问 /login 登录页
   ↓
3. 路由守卫 loadFromStorage() 加载旧数据
   ↓
4. isLoggedIn = true（只检查 localStorage 有数据）
   ↓
5. 路由守卫检测"已登录用户访问登录页"，重定向到首页 /
   ↓
6. 首页调用 API，token 过期返回 401
   ↓
7. API 拦截器跳转到 /login
   ↓
8. 回到步骤 2 → 无限循环 ♻️
```

**问题代码**:

```typescript
// router/index.ts - 错误逻辑
if (to.path === '/login' && userStore.isLoggedIn) {
  return next('/')  // 认为已登录，重定向首页
}
```

```typescript
// api/index.ts - 缺少路径检查
if (error.response?.status === 401) {
  window.location.href = '/login'  // 不管当前在哪都跳转
}
```

**解决方案**:

1. **路由守卫**：访问登录页时先清除旧认证数据

```typescript
// router/index.ts
if (to.meta.requiresAuth === false) {
  if (to.path === '/login') {
    userStore.clear()  // 清除旧数据
    return next()      // 直接放行
  }
  return next()
}
```

2. **API 拦截器**：已在登录页时不再跳转

```typescript
// api/index.ts
// 如果已经在登录页，不要跳转
if (window.location.pathname === '/login') {
  return Promise.reject(error)
}
```

**修复文件**:
- `frontend/src/router/index.ts`
- `frontend/src/api/index.ts`

**经验教训**:

1. `isLoggedIn` 只检查 localStorage 有数据，不验证 token 有效性
2. 前端无法在路由守卫中同步验证 token（需调用后端）
3. 登录页应作为"干净入口"，进入时清除所有旧状态
4. API 拦截器跳转前需检查当前路径，避免循环

**预防措施**:

- 登录页永远是干净的起点，不做"已登录检测"
- 所有重定向逻辑都要考虑当前路径
- Token 过期处理要区分场景

---

## BUG-002: 会话列表未显示 .jsonl.reset 文件

**发现日期**: 2026-03-31

**严重程度**: P2（功能不完整）

**现象**:
- 会话列表只显示 `.jsonl` 结尾的文件
- `.jsonl.reset.xxx` 格式的会话文件未显示
- 历史对话记录缺失

**根本原因**:

Python `glob("*.jsonl")` 只匹配以 `.jsonl` 结尾的文件：

```python
# 错误代码
for jsonl_file in sessions_dir.glob("*.jsonl"):
    # .jsonl.reset.2026-03-27T03-58-50.055Z 不匹配 *.jsonl
```

文件名格式：
- 普通会话：`{session_id}.jsonl`
- 重置会话：`{session_id}.jsonl.reset.{timestamp}`

**解决方案**:

改用 `iterdir()` 并检查文件名是否包含 `.jsonl`：

```python
# 修复代码
for jsonl_file in sessions_dir.iterdir():
    if '.jsonl' not in jsonl_file.name:
        continue
    if jsonl_file.name == "sessions.json":
        continue
    # 处理文件...
```

**修复文件**:
- `backend/app.py` - `get_agent_sessions()` 函数
- `backend/app.py` - `get_session_messages()` 函数

**经验教训**:

1. `glob()` 模式匹配有局限性，复杂文件名需用其他方式
2. 文件扫描逻辑要考虑所有可能的命名格式

---

## BUG-003: 会话用户消息显示大量无关元数据

**发现日期**: 2026-03-31

**严重程度**: P2（影响体验）

**现象**:
- 用户消息显示大量系统元数据
- 包含 `System:`、`Sender (untrusted metadata):`、JSON 代码块等
- 实际消息被淹没，难以阅读

**原始消息格式**:
```
System: [2026-03-26 16:07:42 GMT+8] Feishu[aqiang] group oc_1b1b033845cef999d61ae57f944592d1 ...

Conversation info (untrusted metadata):
```json
{
  "message_id": "om_x100b537ada0078bcc22620d493317ac",
  "sender_id": "ou_36505bdb19172485ee9f5df1920159fa",
  ...
}
```

Sender (untrusted metadata):
```json
{
  "label": "ou_36505bdb19172485ee9f5df1920159fa",
  ...
}
```

你好
```

**根本原因**:

消息提取函数 `extract_user_message()` 逻辑不完善，未能正确过滤元数据。

**解决方案**:

重写消息提取函数：

```python
def extract_user_message(text: str) -> str:
    lines = text.split('\n')
    result_lines = []
    in_json_block = False

    for line in lines:
        stripped = line.strip()

        # 检测 JSON 代码块
        if stripped == '```json' or stripped == '```':
            in_json_block = not in_json_block
            continue

        # 在 JSON 代码块内，跳过
        if in_json_block:
            continue

        # 跳过元数据标记行
        if stripped.startswith('System:'):
            continue
        if stripped.startswith('Conversation info'):
            continue
        if stripped.startswith('Sender (untrusted'):
            continue

        result_lines.append(line)

    result = '\n'.join(result_lines).strip()

    # 提取时间戳后的实际消息
    import re
    match = re.search(r'\[(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[^\]]+\]\s*(.+)$', result, re.DOTALL)
    if match:
        return match.group(2).strip()

    return result
```

**修复文件**:
- `backend/app.py` - `extract_user_message()` 函数

**经验教训**:

1. 第三方系统消息包含大量元数据，需针对性清洗
2. 正则表达式提取特定模式内容是有效方法
3. 消息格式可能有多种变体，需实际测试验证

---

## Bug 统计

| 状态 | 数量 |
|------|------|
| 已修复 | 4 |
| 处理中 | 0 |
| 待处理 | 0 |

---

## BUG-004: Agent 会话条数统计不准确

**发现日期**: 2026-03-31

**严重程度**: P2（数据展示错误）

**现象**:
- Agent 列表显示的会话条数与实际文件数不符
- 部分历史会话未被统计

**根本原因**:

`get_session_agents()` 函数存在两个问题：

```python
# 错误代码
for jsonl_file in sessions_dir.glob("*.jsonl"):
    # 问题1: .jsonl.reset.xxx 文件不匹配 *.jsonl
    session_count = len([f for f in jsonl_files if ".reset." not in f.name])
    # 问题2: 故意过滤掉了 reset 文件
```

**解决方案**:

改用 `iterdir()` 扫描所有文件，并使用集合去重：

```python
seen_sessions = set()
for jsonl_file in sessions_dir.iterdir():
    if '.jsonl' not in jsonl_file.name:
        continue
    # 提取 session id 并去重
    if ".reset." in jsonl_file.name:
        sid = jsonl_file.name.split(".jsonl.reset.")[0]
    else:
        sid = jsonl_file.name.replace(".jsonl", "")
    if sid not in seen_sessions:
        seen_sessions.add(sid)
        session_count += 1
```

**修复文件**:
- `backend/app.py` - `get_session_agents()` 函数

**经验教训**:

1. `glob()` 模式匹配有局限性，复杂命名格式需用其他方式
2. 统计逻辑要与实际业务需求一致（reset 文件也是有效会话）

---

## BUG-005: Agent 列表模型显示为 "-"

**发现日期**: 2026-04-04

**严重程度**: P2（数据展示错误）

**现象**:
- Agent 配置页列表中模型列显示为 "-"
- 已配置模型的 Agent 也无法显示模型名称

**根本原因**:

`_get_agents_via_ws()` 函数只合并了 `workspace` 字段，没有合并 `model` 等其他配置字段：

```python
# 错误代码 - 只合并了 workspace
def _get_agents_via_ws():
    result = sync_call('agents.list')
    agents = result.get('agents', [])
    config = _get_config_via_ws()
    agents_config = config.get('agents', {}).get('list', [])

    # 只创建 workspace 映射
    workspace_map = {a.get('id'): a.get('workspace') for a in agents_config}

    # 只合并 workspace
    for agent in agents:
        if agent_id in workspace_map:
            agent['workspace'] = workspace_map[agent_id]
```

Gateway API `agents.list` 返回的数据不完整，完整配置在 `config.get` 返回的 `agents.list` 中。

**解决方案**:

合并所有配置字段：

```python
def _get_agents_via_ws():
    result = sync_call('agents.list')
    agents = result.get('agents', [])
    config = _get_config_via_ws()
    agents_config = config.get('agents', {}).get('list', [])

    config_map = {a.get('id'): a for a in agents_config}

    for agent in agents:
        agent_id = agent.get('id')
        if agent_id in config_map:
            agent_config = config_map[agent_id]
            # 合并所有配置字段
            if 'workspace' in agent_config:
                agent['workspace'] = agent_config['workspace']
            if 'model' in agent_config:
                agent['model'] = agent_config['model']
            if 'skills' in agent_config:
                agent['skills'] = agent_config['skills']
            if 'tools' in agent_config:
                agent['tools'] = agent_config['tools']
            # ... 其他字段

    return agents
```

**修复文件**:
- `backend/app.py` - `_get_agents_via_ws()` 函数

**经验教训**:

1. Gateway API 返回的数据可能不完整，需要与 config 数据合并
2. 数据合并时要考虑所有需要展示的字段

---

## BUG-006: Agent 配置编辑保存报 500 错误

**发现日期**: 2026-04-04

**严重程度**: P1（功能无法使用）

**现象**:
- Agent 配置页点击编辑，修改模型后保存
- 报错："操作失败：Request failed with status code 500"

**根本原因**:

使用了不存在的 Gateway API `agents.update`：

```python
# 错误代码
def update_agent(agent_id):
    data = request.get_json()
    params = {'agentId': agent_id}
    if 'model' in data:
        params['model'] = data['model']

    # agents.update API 不存在
    result = sync_call('agents.update', params)
```

**解决方案**:

改用 `config.apply` 修改配置的方式：

```python
def update_agent(agent_id):
    data = request.get_json()

    # 获取当前配置
    config = _get_config_via_ws()
    agents_list = config.get('agents', {}).get('list', [])

    # 找到并更新指定 Agent
    for agent in agents_list:
        if agent.get('id') == agent_id:
            if 'name' in data:
                agent['name'] = data['name']
            if 'model' in data:
                agent['model'] = data['model']
            break

    # 应用配置
    _save_config_via_ws(config)

    return jsonify({'success': True})
```

**修复文件**:
- `backend/app.py` - `update_agent()` 函数

**经验教训**:

1. 使用 Gateway API 前要确认 API 是否存在
2. 对于配置修改，`config.apply` 是更通用可靠的方式

---

## BUG-007: 模板 model.json 为空导致新 Agent 无模型配置

**发现日期**: 2026-04-04

**严重程度**: P2（功能异常）

**现象**:
- 从模板创建的 Agent 没有模型配置
- Agent 档案页模型显示 "unknown"

**根本原因**:

模板目录下的 `model.json` 文件内容为空对象 `{}`：

```json
// templates/代码助手/model.json
{}
```

**解决方案**:

为所有模板添加正确的模型配置：

```json
// templates/代码助手/model.json
{
  "primary": "bailian/qwen3-coder-next"
}

// templates/行政助理/model.json
{
  "primary": "bailian/glm-5"
}
```

**修复文件**:
- `templates/行政助理/model.json`
- `templates/代码助手/model.json`
- `templates/客服代表/model.json`
- `templates/写作助手/model.json`

**经验教训**:

1. 模板文件要包含完整的配置数据
2. 创建测试用例验证模板完整性

---

## BUG-008: AgentProfile.vue 缺少 router 导入

**发现日期**: 2026-04-04

**严重程度**: P3（代码错误）

**现象**:
- 控制台报错 `router is not defined`
- "配置技能"按钮点击无法跳转

**根本原因**:

`openSkillsConfig()` 函数使用了 `router`，但没有导入 `useRouter`：

```typescript
// 错误代码
import { useRoute } from 'vue-router'

const route = useRoute()

function openSkillsConfig() {
  router.push('/skills-list')  // router 未定义
}
```

**解决方案**:

添加 `useRouter` 导入：

```typescript
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
```

**修复文件**:
- `frontend/src/agent/AgentProfile.vue`

---

## BUG-009: Gateway 切换后连接未重置

**发现日期**: 2026-04-04

**严重程度**: P1（功能异常）

**现象**:
- 在 Gateway 管理页面切换 Gateway
- 切换后仍连接到旧的 Gateway
- 后续操作使用的仍是旧连接

**根本原因**:

`gateway_client.py` 中的全局客户端 `_global_client` 在切换时未重置：

```python
# 问题代码
def set_current_gateway(gateway_id: int):
    settings.current_gateway_id = gateway_id
    # 全局客户端仍然保持旧连接
```

**解决方案**:

切换时重置全局客户端：

```python
def set_current_gateway(gateway_id: int):
    settings.current_gateway_id = gateway_id

    # 重置全局客户端
    from gateway_client import _global_client
    if _global_client and _global_client.connected:
        asyncio.run(_global_client.close())

    import gateway_client
    gateway_client._global_client = None
```

**修复文件**:
- `backend/gateway_sync.py`

---

## BUG-010: log_operation_direct 参数类型错误

**发现日期**: 2026-04-04

**严重程度**: P2（功能异常）

**现象**:
- 添加 Gateway 保存报错
- 错误信息：`Error binding parameter 5: type 'dict' is not supported`

**根本原因**:

`log_operation_direct` 的 `details` 参数期望字符串，但传入了字典：

```python
# 错误代码
log_operation_direct('create_gateway', 'gateway', str(gw_id), {'name': name, 'url': url})
```

**解决方案**:

使用 `json.dumps()` 转换：

```python
log_operation_direct('create_gateway', 'gateway', str(gw_id), json.dumps({'name': name, 'url': url}))
```

**修复文件**:
- `backend/app.py` - 修复所有调用处

---

## BUG-011: 用户创建报错 UNIQUE constraint failed

**发现日期**: 2026-04-04

**严重程度**: P2（功能异常）

**现象**:
- 创建用户时报错
- 错误信息：`UNIQUE constraint failed: users.email`
- 即使没有填写邮箱也会报错

**根本原因**:

`email` 字段有 UNIQUE 约束，空字符串也会冲突：

```python
# 问题代码
email = data.get('email', '').strip()  # 空字符串 ''
# INSERT 时 email='' 与其他空字符串冲突
```

**解决方案**:

空字符串转为 NULL，并添加邮箱检查：

```python
email = data.get('email', '').strip() or None  # 空字符串转 None

if email:
    existing = db.fetch_one("SELECT id FROM users WHERE email = ?", (email,))
    if existing:
        return jsonify({'error': '邮箱已被使用'}), 400
```

**修复文件**:
- `backend/app.py` - `create_user()` 函数

---

## Bug 统计

| 状态 | 数量 |
|------|------|
| 已修复 | 11 |
| 处理中 | 0 |
| 待处理 | 0 |

---

## 严重程度说明

| 级别 | 含义 | 示例 |
|------|------|------|
| P0 | 阻塞功能，必须立即修复 | 无法登录、系统崩溃 |
| P1 | 严重影响，尽快修复 | 主要功能异常 |
| P2 | 一般影响，按计划修复 | 次要功能异常 |
| P3 | 轻微问题，有时间再修 | UI 样式问题 |