"""
模型管理模块

管理 OpenClaw 的模型配置，包括：
- 模型 CRUD 操作
- API Key 加密存储
- 模型提供商模板
- 模型连通性测试
"""
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from database import db
from crypto_utils import CryptoUtils, get_crypto


# 模型提供商模板
PROVIDER_TEMPLATES = {
    'bailian': {
        'name': '阿里云百炼',
        'api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'models': ['qwen-turbo', 'qwen-plus', 'qwen-max', 'qwen-max-longcontext'],
        'auth_type': 'api_key',
        'description': '阿里云百炼大模型平台，支持 Qwen 系列模型'
    },
    'deepseek': {
        'name': 'DeepSeek',
        'api_base': 'https://api.deepseek.com/v1',
        'models': ['deepseek-chat', 'deepseek-coder'],
        'auth_type': 'api_key',
        'description': 'DeepSeek 深度求索，擅长代码生成'
    },
    'zhipu': {
        'name': '智谱',
        'api_base': 'https://open.bigmodel.cn/api/paas/v4',
        'models': ['glm-4', 'glm-4-flash', 'glm-4-long'],
        'auth_type': 'api_key',
        'description': '智谱 AI，支持 GLM 系列模型'
    },
    'kimi': {
        'name': 'Kimi (Moonshot)',
        'api_base': 'https://api.moonshot.cn/v1',
        'models': ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'],
        'auth_type': 'api_key',
        'description': 'Moonshot Kimi，长文本处理能力强'
    },
    'minimax': {
        'name': 'MiniMax',
        'api_base': 'https://api.minimax.chat/v1',
        'models': ['abab6.5-chat', 'abab5.5-chat', 'abab5.5s-chat'],
        'auth_type': 'api_key',
        'description': 'MiniMax 大模型'
    }
}


class ModelManager:
    """模型管理器"""

    def __init__(self):
        self.crypto = get_crypto()

    def get_providers(self) -> List[Dict]:
        """获取所有模型提供商模板"""
        providers = []
        for provider_id, template in PROVIDER_TEMPLATES.items():
            providers.append({
                'id': provider_id,
                'name': template['name'],
                'api_base': template['api_base'],
                'models': template['models'],
                'auth_type': template['auth_type'],
                'description': template['description']
            })
        return providers

    def get_provider_models(self, provider_id: str) -> List[str]:
        """获取指定提供商的模型列表"""
        template = PROVIDER_TEMPLATES.get(provider_id)
        if template:
            return template['models']
        return []

    def list_models(self) -> List[Dict]:
        """获取所有模型配置"""
        rows = db.fetch_all(
            'SELECT * FROM models ORDER BY created_at DESC'
        )

        models = []
        for row in rows:
            model = self._row_to_model(row, include_key=False)
            models.append(model)

        return models

    def get_model(self, model_id: str, include_key: bool = False) -> Optional[Dict]:
        """获取单个模型配置"""
        row = db.fetch_one(
            'SELECT * FROM models WHERE id = ?', (model_id,)
        )

        if row:
            return self._row_to_model(row, include_key=include_key)
        return None

    def create_model(self, data: Dict) -> Dict:
        """创建模型配置"""
        model_id = f"model-{uuid.uuid4().hex[:8]}"
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 加密 API Key
        api_key = data.get('api_key', '')
        encrypted_key = ''
        if api_key:
            encrypted_key = self.crypto.encrypt(api_key)

        # 处理参数
        parameters = data.get('parameters', {})
        parameters_json = json.dumps(parameters) if parameters else '{}'

        # 获取提供商默认 API Base（如果未提供）
        api_base = data.get('api_base', '')
        if not api_base:
            provider = data.get('provider', '')
            template = PROVIDER_TEMPLATES.get(provider)
            if template:
                api_base = template['api_base']

        # 插入数据库
        db.execute(
            '''INSERT INTO models
               (id, name, provider, model_type, api_key_encrypted, api_base,
                model_name, parameters, enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (model_id, data['name'], data['provider'],
             data.get('model_type', 'chat'), encrypted_key, api_base,
             data['model_name'], parameters_json,
             data.get('enabled', True), now, now)
        )

        return self.get_model(model_id)

    def update_model(self, model_id: str, data: Dict) -> Optional[Dict]:
        """更新模型配置"""
        # 检查模型是否存在
        existing = self.get_model(model_id)
        if not existing:
            return None

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 处理 API Key 更新
        api_key = data.get('api_key')
        encrypted_key = existing.get('api_key_encrypted', '')

        if api_key:
            # 用户提供了新的 API Key，加密存储
            encrypted_key = self.crypto.encrypt(api_key)
        elif api_key == '' and 'api_key' in data:
            # 用户清空了 API Key
            encrypted_key = ''

        # 处理参数更新
        parameters = data.get('parameters')
        if parameters:
            # 用户提供了新参数，序列化为 JSON
            parameters_json = json.dumps(parameters)
        else:
            # 使用现有的参数
            existing_params = existing.get('parameters', {})
            if isinstance(existing_params, dict):
                parameters_json = json.dumps(existing_params)
            else:
                parameters_json = existing_params or '{}'

        # 构建 UPDATE 语句
        update_fields = {
            'updated_at': now
        }

        if 'name' in data:
            update_fields['name'] = data['name']
        if 'provider' in data:
            update_fields['provider'] = data['provider']
        if 'model_type' in data:
            update_fields['model_type'] = data['model_type']
        if 'api_base' in data:
            update_fields['api_base'] = data['api_base']
        if 'model_name' in data:
            update_fields['model_name'] = data['model_name']
        if 'enabled' in data:
            update_fields['enabled'] = data['enabled']

        # 特殊处理加密字段和参数
        update_fields['api_key_encrypted'] = encrypted_key
        update_fields['parameters'] = parameters_json

        # 执行更新
        db.update('models', update_fields, 'id = ?', (model_id,))

        return self.get_model(model_id)

    def delete_model(self, model_id: str) -> bool:
        """删除模型配置"""
        existing = self.get_model(model_id)
        if not existing:
            return False

        db.delete('models', 'id = ?', (model_id,))
        return True

    def test_connection(self, model_id: str) -> Dict:
        """测试模型 API 连通性"""
        model = self.get_model(model_id, include_key=True)
        if not model:
            return {'connected': False, 'error': '模型不存在'}

        api_key = model.get('api_key', '')
        if not api_key:
            return {'connected': False, 'error': '未配置 API Key'}

        api_base = model.get('api_base', '')
        if not api_base:
            return {'connected': False, 'error': '未配置 API Base'}

        model_name = model.get('model_name', '')

        # 尝试调用 API
        try:
            import requests
            import time

            start_time = time.time()

            # 发送测试请求
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            # 使用简单的 chat completion 测试
            payload = {
                'model': model_name,
                'messages': [{'role': 'user', 'content': 'Hi'}],
                'max_tokens': 5
            }

            response = requests.post(
                f'{api_base}/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                return {
                    'connected': True,
                    'response_time': elapsed_ms,
                    'model': model_name,
                    'error': None
                }
            elif response.status_code == 401:
                return {
                    'connected': False,
                    'error': 'API Key 无效或已过期',
                    'status_code': 401
                }
            else:
                return {
                    'connected': False,
                    'error': f'API 返回错误: {response.status_code}',
                    'status_code': response.status_code
                }

        except requests.exceptions.Timeout:
            return {'connected': False, 'error': '连接超时（30秒）'}
        except requests.exceptions.ConnectionError:
            return {'connected': False, 'error': '无法连接到 API 服务器'}
        except Exception as e:
            return {'connected': False, 'error': str(e)}

    def _row_to_model(self, row: Dict, include_key: bool = False) -> Dict:
        """将数据库行转换为模型字典"""
        model = {
            'id': row['id'],
            'name': row['name'],
            'provider': row['provider'],
            'model_type': row['model_type'],
            'api_base': row['api_base'],
            'model_name': row['model_name'],
            'parameters': json.loads(row['parameters'] or '{}'),
            'enabled': bool(row['enabled']),
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }

        # 处理 API Key
        encrypted_key = row['api_key_encrypted'] or ''
        model['api_key_encrypted'] = encrypted_key

        if include_key and encrypted_key:
            # 返回解密后的原始值（仅用于测试连接）
            model['api_key'] = self.crypto.decrypt(encrypted_key)

        # 脱敏显示
        model['api_key_masked'] = self.crypto.mask_key(encrypted_key) if encrypted_key else ''

        return model


# 全局实例
model_manager = ModelManager()