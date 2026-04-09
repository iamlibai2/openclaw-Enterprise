# Gateway 模型管理 API 调研

## 调研结论

Gateway **没有**独立的模型 CRUD API，模型只能通过配置文件管理。

---

## API 测试结果

| API | 状态 | 说明 |
|-----|------|------|
| `models.list` | ✅ 支持 | 返回模型列表 |
| `models.create` | ❌ 不存在 | `unknown method` |
| `models.update` | ❌ 不存在 | `unknown method` |
| `models.delete` | ❌ 不存在 | `unknown method` |

### models.list 返回示例

```json
{
  "models": [
    {
      "id": "glm-5",
      "name": "glm-5 (Custom Provider)",
      "provider": "bailian",
      "contextWindow": 160000,
      "reasoning": false,
      "input": ["text"]
    }
  ]
}
```

---

## 模型管理方式

### 读取配置

```python
from gateway_sync import sync_call

result = sync_call('config.get')
config = result.get('config', {})
base_hash = result.get('hash')  # 配置版本，修改时需要传递

# 模型配置结构
providers = config.get('models', {}).get('providers', {})
```

### 修改模型

```python
import json5

# 获取当前配置
result = sync_call('config.get')
config = result.get('config', {})
base_hash = result.get('hash')

# 修改配置
provider_id = 'bailian'
if provider_id not in config['models']['providers']:
    config['models']['providers'][provider_id] = {
        'baseUrl': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'apiKey': 'your-api-key',
        'api': 'openai-completions',
        'models': []
    }

# 添加新模型
config['models']['providers'][provider_id]['models'].append({
    'id': 'new-model',
    'name': '新模型',
    'api': 'openai-completions',
    'reasoning': False,
    'input': ['text'],
    'contextWindow': 16000,
    'maxTokens': 4096
})

# 保存配置（自动触发 Gateway 重启）
sync_call('config.apply', {
    'raw': json5.dumps(config),
    'baseHash': base_hash
})
```

### 删除模型

```python
# 从配置中移除模型
models = config['models']['providers'][provider_id]['models']
config['models']['providers'][provider_id]['models'] = [
    m for m in models if m.get('id') != 'model-to-delete'
]

# 保存配置
sync_call('config.apply', {
    'raw': json5.dumps(config),
    'baseHash': base_hash
})
```

---

## 配置结构

```javascript
{
  "models": {
    "mode": "merge",
    "providers": {
      "bailian": {
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "apiKey": "sk-xxx",
        "api": "openai-completions",
        "models": [
          {
            "id": "qwen-turbo",
            "name": "Qwen Turbo",
            "api": "openai-completions",
            "reasoning": false,
            "input": ["text"],
            "contextWindow": 8000,
            "maxTokens": 2000,
            "cost": {
              "input": 0.002,
              "output": 0.006,
              "cacheRead": 0,
              "cacheWrite": 0
            }
          }
        ]
      }
    }
  }
}
```

---

## 后端实现

### model_manager.py

```python
class ModelManager:
    def create_model(self, data: Dict) -> Dict:
        # 1. 获取配置
        result = sync_call('config.get')
        config = result.get('config', {})
        base_hash = result.get('hash')

        # 2. 修改配置
        # ...

        # 3. 保存（触发重启）
        sync_call('config.apply', {
            'raw': json5.dumps(config),
            'baseHash': base_hash
        })

        return model
```

### app.py

```python
@app.route('/api/models', methods=['POST'])
def create_model():
    start_time = time.time()

    # 创建模型
    model = model_manager.create_model(data)

    # 等待 Gateway 重启
    success, elapsed, error = _wait_for_gateway_restart(start_time)

    if success:
        return jsonify({
            'success': True,
            'message': f'创建成功，Gateway 已重启 (耗时 {elapsed} 秒)'
        })
```

---

## 与 Agent API 对比

| 功能 | Agent API | Model API |
|------|-----------|-----------|
| List | `agents.list` | `models.list` |
| Create | `agents.create` ✅ | ❌ 通过 `config.apply` |
| Update | `agents.update` ✅ (热加载) | ❌ 通过 `config.apply` |
| Delete | `agents.delete` ✅ (热加载) | ❌ 通过 `config.apply` |
| 重启 | 创建时重启 | 所有操作都重启 |

---

## 最佳实践

1. **合并操作**：批量修改模型时，一次性修改配置，减少重启次数
2. **等待重启**：前端显示 loading，后端等待重启完成再返回
3. **错误处理**：配置冲突时 Gateway 会返回错误，需要处理 `baseHash` 不匹配的情况

```python
# baseHash 冲突处理
try:
    sync_call('config.apply', {'raw': raw, 'baseHash': hash})
except GatewayError as e:
    if 'hash mismatch' in str(e):
        # 配置已被其他地方修改，重新获取
        result = sync_call('config.get')
        # 重试修改
```