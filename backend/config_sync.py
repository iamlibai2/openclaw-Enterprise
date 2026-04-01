"""
Gateway 配置同步模块

将本地数据库中的模型配置和渠道配置同步到 Gateway 的 openclaw.json
"""
import json
from typing import Dict, List, Any, Optional
from database import db
from crypto_utils import get_crypto
from gateway_sync import sync_call


class ConfigSync:
    """配置同步器"""

    def __init__(self):
        self.crypto = get_crypto()

    def sync_models_to_gateway(self) -> Dict:
        """
        将本地模型配置同步到 Gateway

        Returns:
            同步结果
        """
        try:
            # 获取本地模型配置
            rows = db.fetch_all('SELECT * FROM models WHERE enabled = 1')

            if not rows:
                return {'success': True, 'message': '没有启用的模型需要同步'}

            # 构建模型配置
            models_config = {}
            for row in rows:
                model_id = row['id']

                # 解密 API Key
                api_key = ''
                if row['api_key_encrypted']:
                    api_key = self.crypto.decrypt(row['api_key_encrypted'])

                # 解析参数
                parameters = json.loads(row['parameters'] or '{}')

                # 构建模型配置
                models_config[model_id] = {
                    'provider': row['provider'],
                    'model': row['model_name'],
                    'api_key': api_key,
                    'api_base': row['api_base'] or None,
                    **parameters
                }

            # 获取当前 Gateway 配置
            result = sync_call('config.get')
            current_config = result.get('config', {})
            config_hash = result.get('hash', '')

            # 更新模型配置
            current_config['models'] = models_config

            # 同步到 Gateway
            import json5
            raw = json5.dumps(current_config)

            sync_result = sync_call('config.apply', {
                'raw': raw,
                'baseHash': config_hash
            })

            return {
                'success': True,
                'message': f'已同步 {len(models_config)} 个模型配置到 Gateway',
                'models_count': len(models_config)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def sync_channel_to_gateway(self, channel_type: str) -> Dict:
        """
        将指定渠道配置同步到 Gateway

        Args:
            channel_type: 渠道类型 (feishu/dingtalk)

        Returns:
            同步结果
        """
        try:
            # 获取本地渠道配置
            row = db.fetch_one(
                'SELECT * FROM channel_configs WHERE channel_type = ? AND enabled = 1',
                (channel_type,)
            )

            if not row:
                return {'success': True, 'message': f'没有启用的 {channel_type} 配置'}

            # 解析配置
            config_json = row['config_encrypted'] or '{}'
            config_data = json.loads(config_json)

            # 解密敏感字段
            decrypted_config = {}
            for key, value in config_data.items():
                if key in ['app_secret', 'app_key'] and value:
                    decrypted_config[key] = self.crypto.decrypt(value)
                else:
                    decrypted_config[key] = value

            # 获取当前 Gateway 配置
            result = sync_call('config.get')
            current_config = result.get('config', {})
            config_hash = result.get('hash', '')

            # 更新渠道配置
            if 'channels' not in current_config:
                current_config['channels'] = {}

            # 映射渠道类型到 Gateway 的渠道名称
            gateway_channel_name = channel_type
            if channel_type == 'dingtalk':
                gateway_channel_name = 'dingtalk-connector'

            # 构建渠道账号配置
            account_id = 'default'
            account_config = {
                'enabled': True
            }

            if channel_type == 'feishu':
                account_config['appId'] = decrypted_config.get('app_id', '')
                account_config['appSecret'] = decrypted_config.get('app_secret', '')
            elif channel_type == 'dingtalk':
                account_config['clientKey'] = decrypted_config.get('app_key', '')
                account_config['clientSecret'] = decrypted_config.get('app_secret', '')

            # 更新配置
            if gateway_channel_name not in current_config['channels']:
                current_config['channels'][gateway_channel_name] = {
                    'enabled': True,
                    'accounts': {}
                }

            current_config['channels'][gateway_channel_name]['accounts'][account_id] = account_config

            # 同步到 Gateway
            import json5
            raw = json5.dumps(current_config)

            sync_result = sync_call('config.apply', {
                'raw': raw,
                'baseHash': config_hash
            })

            return {
                'success': True,
                'message': f'{channel_type} 配置已同步到 Gateway'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def sync_all_to_gateway(self) -> Dict:
        """
        将所有本地配置同步到 Gateway

        Returns:
            同步结果
        """
        results = {
            'models': None,
            'channels': []
        }

        # 同步模型
        results['models'] = self.sync_models_to_gateway()

        # 同步所有启用的渠道
        channel_rows = db.fetch_all(
            'SELECT channel_type FROM channel_configs WHERE enabled = 1'
        )

        for row in channel_rows:
            channel_type = row['channel_type']
            result = self.sync_channel_to_gateway(channel_type)
            results['channels'].append({
                'channel': channel_type,
                **result
            })

        return results

    def get_sync_status(self) -> Dict:
        """
        获取同步状态

        Returns:
            本地和 Gateway 配置对比
        """
        try:
            # 本地配置统计
            local_models = db.fetch_one(
                'SELECT COUNT(*) as count FROM models WHERE enabled = 1'
            )
            local_channels = db.fetch_all(
                'SELECT channel_type, enabled FROM channel_configs'
            )

            # Gateway 配置统计
            result = sync_call('config.get')
            gateway_config = result.get('config', {})

            gateway_models = len(gateway_config.get('models', {}))
            gateway_channels = len([
                k for k, v in gateway_config.get('channels', {}).items()
                if v.get('enabled', True)
            ])

            return {
                'local': {
                    'models': local_models['count'] if local_models else 0,
                    'channels': len([c for c in local_channels if c['enabled']])
                },
                'gateway': {
                    'models': gateway_models,
                    'channels': gateway_channels
                },
                'in_sync': (
                    (local_models['count'] if local_models else 0) == gateway_models
                )
            }

        except Exception as e:
            return {
                'error': str(e)
            }


# 全局实例
config_sync = ConfigSync()