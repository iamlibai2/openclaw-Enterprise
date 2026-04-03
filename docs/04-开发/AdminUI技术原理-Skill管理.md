# OpenClaw Admin UI 技术原理 - Skill 管理

## 概述

本文档记录 Admin UI 中 Skill 管理功能的技术实现原理，包括 Skill 的启用/禁用机制、配置管理和 Agent 加载流程。

## Skill 禁用原理

### 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Skill 禁用流程                                │
└─────────────────────────────────────────────────────────────────────┘

Admin UI 前端                Admin UI 后端              OpenClaw Gateway
     │                            │                           │
     │  1. 点击开关                │                           │
     │ ─────────────────────────>  │                           │
     │                            │                           │
     │                            │  2. config.patch          │
     │                            │ ────────────────────────> │
     │                            │                           │
     │                            │  3. 更新 openclaw.json    │
     │                            │    skills.entries.{slug}  │
     │                            │    .enabled = false       │
     │                            │                           │
     │                            │                           │  4. 重载配置
     │                            │                           │  跳过 disabled skill
     │                            │                           │
     │  5. 返回成功               │                           │
     │ <─────────────────────────  │                           │
```

### 1. 前端调用

用户在 Skills 页面点击开关，前端调用 `skillApi.toggle` 方法：

```typescript
// frontend/src/views/Skills.vue
async function toggleSkill(skill: Skill) {
  const res = await skillApi.toggle(skill.slug, skill.enabled)
  if (res.data.success) {
    ElMessage.success(skill.enabled ? '已启用' : '已禁用')
  }
}

// frontend/src/api/index.ts
export const skillApi = {
  toggle(skillSlug: string, enabled: boolean) {
    return api.post<BaseResponse>(`/skills/${skillSlug}/toggle`, { enabled })
  }
}
```

### 2. 后端 API

后端接收请求，通过 WebSocket 调用 Gateway 的 `config.patch` 方法：

```python
# backend/app.py
@app.route('/api/skills/<skill_slug>/toggle', methods=['POST'])
@require_permission('skills', 'write')
def toggle_skill(skill_slug):
    """启用/禁用 Skill"""
    data = request.get_json()
    enabled = data.get('enabled', True)

    # 使用 config.patch 方法，只修改 skills 配置部分
    import json5
    patch_raw = json5.dumps({
        'skills': {
            'entries': {
                skill_slug: {'enabled': enabled}
            }
        }
    })

    # 获取当前配置 hash
    result = sync_call('config.get')
    hash = result.get('hash')

    # 使用 patch 方法更新配置
    sync_call('config.patch', {'raw': patch_raw, 'baseHash': hash})

    log_operation_direct('toggle_skill', 'skill', skill_slug,
        json.dumps({'enabled': enabled}))
    return jsonify({
        'success': True,
        'message': f'Skill {skill_slug} 已{"启用" if enabled else "禁用"}'
    })
```

### 3. 配置存储

修改后的配置保存在 `~/.openclaw/openclaw.json`：

```json
{
  "skills": {
    "entries": {
      "pua": {
        "enabled": false      // 禁用状态
      },
      "powerpoint-pptx": {
        "enabled": true       // 启用状态
      },
      "automate-excel": {
        // 无 enabled 字段，默认启用
      },
      "baidu-search": {
        "enabled": true
      }
    }
  }
}
```

### 4. Gateway 处理逻辑

Gateway 在启动或重载配置时的处理流程：

```
1. 读取 openclaw.json 中的 skills.entries 配置
2. 扫描 skills 目录下的所有 skill
3. 对于每个 skill：
   - 检查 skills.entries.{slug}.enabled
   - 如果 enabled = false，跳过加载
   - 如果 enabled = true 或未配置，正常加载
4. 将已加载的 skill 注册到 Agent 的工具列表
```

### 5. 与 Agent 的关系

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Agent 加载 Skill                            │
└─────────────────────────────────────────────────────────────────────┘

Agent Runner 启动
       │
       ▼
读取 skills 配置 (skills.entries)
       │
       ▼
遍历 skills 目录
       │
       ├─► skill-a: enabled = true  ──► 加载 ──► 注册为工具
       │
       ├─► skill-b: enabled = false ──► 跳过（不注册）
       │
       └─► skill-c: 无配置 ──► 默认启用 ──► 加载 ──► 注册为工具
```

## 技术要点总结

| 层级 | 说明 |
|------|------|
| **配置层** | `skills.entries.{slug}.enabled` 控制启用状态 |
| **默认值** | 未配置时默认为 `true`（启用） |
| **持久化** | 配置写入 `openclaw.json`，重启后保持 |
| **生效方式** | 通过 `config.patch` API 触发 Gateway 重载 |
| **权限控制** | 需要 `skills.write` 权限 |

## 配置字段说明

### skills.entries 配置结构

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `enabled` | boolean | 否 | true | 是否启用该 Skill |

### 配置示例

```json
{
  "skills": {
    "install": {
      "nodeManager": "npm"
    },
    "entries": {
      "feishu-im-read": {
        "enabled": true    // 显式启用
      },
      "pua": {
        "enabled": false   // 显式禁用
      },
      "excel-xlsx": {
        // 无配置，默认启用
      }
    }
  }
}
```

## 相关 API

### GET /api/skills

获取所有 Skill 列表，包含启用状态：

```python
def get_skill_enabled(slug: str) -> bool:
    """获取 Skill 启用状态"""
    skills_config = config.get('skills', {}).get('entries', {})
    return skills_config.get(slug, {}).get('enabled', True)
```

### POST /api/skills/{slug}/toggle

启用/禁用 Skill：

**请求参数**：
```json
{
  "enabled": false
}
```

**返回**：
```json
{
  "success": true,
  "message": "Skill pua 已禁用"
}
```

## 权限控制

| 操作 | 所需权限 |
|------|----------|
| 查看 Skill 列表 | `skills.read` |
| 启用/禁用 Skill | `skills.write` |
| 编辑 Skill | `skills.write` |
| 删除 Skill | `skills.delete` |

## 注意事项

1. **配置合并**：使用 `config.patch` 而非直接覆盖，保证其他配置不受影响
2. **立即生效**：配置更新后 Gateway 会自动重载，无需手动重启
3. **状态读取**：每次获取 Skill 列表时都会读取最新配置，保证状态一致性
4. **默认启用**：新安装的 Skill 默认启用，需要显式配置 `enabled: false` 才会禁用

## 版本历史

### v1.0.0 (2026-03-31)

- 初始实现 Skill 启用/禁用功能
- 通过 config.patch 更新配置
- 前端开关组件集成