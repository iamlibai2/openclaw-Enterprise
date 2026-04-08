"""
模型管理模块

直接读写 Gateway 的 openclaw.json 配置，不使用数据库。
"""
from typing import Dict, List, Optional, Any
from gateway_sync import sync_call
from crypto_utils import get_crypto


# 模型提供商模板
PROVIDER_TEMPLATES = {
    'bailian': {
        'name': '阿里云百炼',
        'baseUrl': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'api': 'openai-completions',
        'models': ['qwen-turbo', 'qwen-plus', 'qwen-max', 'qwen-max-longcontext'],
        'description': '阿里云百炼大模型平台，支持 Qwen 系列模型'
    },
    'deepseek': {
        'name': 'DeepSeek',
        'baseUrl': 'https://api.deepseek.com/v1',
        'api': 'openai-completions',
        'models': ['deepseek-chat', 'deepseek-coder'],
        'description': 'DeepSeek 深度求索，擅长代码生成'
    },
    'zhipu': {
        'name': '智谱',
        'baseUrl': 'https://open.bigmodel.cn/api/paas/v4',
        'api': 'openai-completions',
        'models': ['glm-4', 'glm-4-flash', 'glm-4-long'],
        'description': '智谱 AI，支持 GLM 系列模型'
    },
    'kimi': {
        'name': 'Kimi (Moonshot)',
        'baseUrl': 'https://api.moonshot.cn/v1',
        'api': 'openai-completions',
        'models': ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'],
        'description': 'Moonshot Kimi，长文本处理能力强'
    },
    'minimax': {
        'name': 'MiniMax',
        'baseUrl': 'https://api.minimax.chat/v1',
        'api': 'openai-completions',
        'models': ['abab6.5-chat', 'abab5.5-chat', 'abab5.5s-chat'],
        'description': 'MiniMax 大模型'
    }
}


class ModelManager:
    """模型管理器 - 直接操作 Gateway 配置"""

    def __init__(self):
        self.crypto = get_crypto()

    def get_providers(self) -> List[Dict]:
        """获取所有模型提供商模板"""
        providers = []
        for provider_id, template in PROVIDER_TEMPLATES.items():
            providers.append({
                'id': provider_id,
                'name': template['name'],
                'baseUrl': template['baseUrl'],
                'models': template['models'],
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
        """获取所有模型配置 - 从 Gateway 读取"""
        try:
            result = sync_call('config.get')
            config = result.get('config', {})
            models_config = config.get('models', {})
            providers = models_config.get('providers', {})

            models = []
            for provider_id, provider_config in providers.items():
                if not isinstance(provider_config, dict):
                    continue

                provider_models = provider_config.get('models', [])
                api_key = provider_config.get('apiKey', '')
                base_url = provider_config.get('baseUrl', '')

                # API Key 脱敏显示
                api_key_masked = ''
                if api_key:
                    # 显示前8位和后4位，中间用***代替
                    if len(api_key) > 12:
                        api_key_masked = api_key[:8] + '***' + api_key[-4:]
                    else:
                        api_key_masked = api_key[:4] + '***'

                for model in provider_models:
                    if isinstance(model, dict):
                        model_id = model.get('id', 'unknown')
                        context_window = model.get('contextWindow', 16000)
                        max_tokens = model.get('maxTokens', 4096)
                        models.append({
                            'id': model_id,
                            'name': model.get('name', model_id),
                            'provider': provider_id,
                            'provider_name': PROVIDER_TEMPLATES.get(provider_id, {}).get('name', provider_id),
                            'model_name': model_id,
                            'api_base': base_url,
                            'baseUrl': base_url,  # 兼容字段
                            'api_key_masked': api_key_masked,
                            'has_api_key': bool(api_key),
                            'enabled': True,  # 配置文件中的模型默认启用
                            'contextWindow': context_window,
                            'maxTokens': max_tokens,
                            'parameters': {
                                'contextWindow': context_window,
                                'maxTokens': max_tokens,
                                'context_window': context_window,  # snake_case 兼容
                                'max_tokens': max_tokens,  # snake_case 兼容
                                'temperature': 0.7
                            },
                            'model_type': 'chat'
                        })

            return models
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return []

    def get_model(self, model_id: str) -> Optional[Dict]:
        """获取单个模型配置"""
        models = self.list_models()
        for model in models:
            if model['id'] == model_id:
                return model
        return None

    def create_model(self, data: Dict) -> Dict:
        """创建模型配置 - 写入 Gateway"""
        try:
            result = sync_call('config.get')
            config = result.get('config', {})
            base_hash = result.get('hash')  # 获取配置版本 hash

            if 'models' not in config:
                config['models'] = {'mode': 'merge', 'providers': {}}
            if 'providers' not in config['models']:
                config['models']['providers'] = {}

            # 清理输入，去除首尾空格
            provider_id = data['provider'].strip() if data.get('provider') else ''
            model_name = data['model_name'].strip() if data.get('model_name') else ''
            model_display_name = data.get('name', model_name).strip()
            api_base = data.get('api_base', '').strip()
            api_key = data.get('api_key', '').strip() if data.get('api_key') else ''

            if not provider_id or not model_name:
                raise ValueError("提供商和模型名称不能为空")

            # 确保提供商配置存在
            if provider_id not in config['models']['providers']:
                template = PROVIDER_TEMPLATES.get(provider_id, {})
                config['models']['providers'][provider_id] = {
                    'baseUrl': api_base or template.get('baseUrl', ''),
                    'apiKey': api_key,
                    'api': 'openai-completions',
                    'models': []
                }

            provider_config = config['models']['providers'][provider_id]

            # 如果有新的 API Key，更新
            if api_key:
                provider_config['apiKey'] = api_key

            # 添加模型
            params = data.get('parameters', {})
            # 兼容 camelCase 和 snake_case
            context_window = params.get('contextWindow') or params.get('context_window', 16000)
            max_tokens = params.get('maxTokens') or params.get('max_tokens', 4096)

            new_model = {
                'id': model_name,
                'name': model_display_name,
                'api': 'openai-completions',
                'reasoning': False,
                'input': ['text'],
                'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0},
                'contextWindow': context_window,
                'maxTokens': max_tokens
            }

            # 检查是否已存在
            existing_ids = [m.get('id') for m in provider_config.get('models', [])]
            if model_name not in existing_ids:
                provider_config.setdefault('models', []).append(new_model)

            # 保存配置 - 必须传递 baseHash
            import json5
            sync_call('config.apply', {
                'raw': json5.dumps(config),
                'baseHash': base_hash
            })

            return self.get_model(model_name) or {'id': model_name, 'name': model_display_name}

        except Exception as e:
            raise Exception(f"创建模型失败: {e}")

    def update_model(self, model_id: str, data: Dict) -> Optional[Dict]:
        """更新模型配置"""
        try:
            result = sync_call('config.get')
            config = result.get('config', {})
            base_hash = result.get('hash')  # 获取配置版本 hash
            providers = config.get('models', {}).get('providers', {})

            # 清理输入
            model_id = model_id.strip() if model_id else ''

            for provider_id, provider_config in providers.items():
                if not isinstance(provider_config, dict):
                    continue

                for model in provider_config.get('models', []):
                    if isinstance(model, dict) and model.get('id') == model_id:
                        # 更新模型属性
                        if 'name' in data:
                            model['name'] = data['name'].strip() if data['name'] else model_id
                        if 'parameters' in data:
                            params = data['parameters']
                            # 兼容 camelCase 和 snake_case
                            if 'contextWindow' in params or 'context_window' in params:
                                model['contextWindow'] = params.get('contextWindow') or params.get('context_window')
                            if 'maxTokens' in params or 'max_tokens' in params:
                                model['maxTokens'] = params.get('maxTokens') or params.get('max_tokens')

                        # 更新 API Key（在提供商级别）
                        if data.get('api_key'):
                            provider_config['apiKey'] = data['api_key'].strip()

                        # 保存配置 - 必须传递 baseHash
                        import json5
                        sync_call('config.apply', {
                            'raw': json5.dumps(config),
                            'baseHash': base_hash
                        })

                        return self.get_model(model_id)

            return None

        except Exception as e:
            raise Exception(f"更新模型失败: {e}")

    def delete_model(self, model_id: str) -> bool:
        """删除模型配置"""
        try:
            result = sync_call('config.get')
            config = result.get('config', {})
            base_hash = result.get('hash')  # 获取配置版本 hash
            providers = config.get('models', {}).get('providers', {})

            for provider_id, provider_config in providers.items():
                if not isinstance(provider_config, dict):
                    continue

                models = provider_config.get('models', [])
                original_count = len(models)

                provider_config['models'] = [
                    m for m in models
                    if not (isinstance(m, dict) and m.get('id') == model_id)
                ]

                if len(provider_config['models']) < original_count:
                    # 保存配置 - 必须传递 baseHash
                    import json5
                    sync_call('config.apply', {
                        'raw': json5.dumps(config),
                        'baseHash': base_hash
                    })
                    return True

            return False

        except Exception as e:
            raise Exception(f"删除模型失败: {e}")

    def test_connection(self, model_id: str) -> Dict:
        """测试模型 API 连通性 - 远程部署不支持"""
        # Gateway WebSocket API 不提供模型测试功能
        # 且 config.get 返回的 API Key 是脱敏版本
        # 远程部署时无法测试，需要 Gateway 上游支持
        return {
            'connected': False,
            'error': '远程部署模式不支持模型测试功能，请确保模型配置正确'
        }


# 全局实例
model_manager = ModelManager()