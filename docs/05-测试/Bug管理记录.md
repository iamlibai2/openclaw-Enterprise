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

## 严重程度说明

| 级别 | 含义 | 示例 |
|------|------|------|
| P0 | 阻塞功能，必须立即修复 | 无法登录、系统崩溃 |
| P1 | 严重影响，尽快修复 | 主要功能异常 |
| P2 | 一般影响，按计划修复 | 次要功能异常 |
| P3 | 轻微问题，有时间再修 | UI 样式问题 |