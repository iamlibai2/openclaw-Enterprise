"""
渠道配置管理模块

管理飞书、钉钉等渠道的配置，包括：
- 配置加密存储
- 配置向导数据
- 配置验证
"""
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from database import db
from crypto_utils import get_crypto


# 渠道类型
CHANNEL_TYPES = {
    'feishu': {
        'name': '飞书',
        'description': '飞书企业自建应用',
        'config_fields': ['app_id', 'app_secret', 'event_url', 'bot_name'],
        'required_fields': ['app_id', 'app_secret']
    },
    'dingtalk': {
        'name': '钉钉',
        'description': '钉钉企业内部应用',
        'config_fields': ['app_key', 'app_secret', 'callback_url', 'agent_id'],
        'required_fields': ['app_key', 'app_secret']
    }
}


class ChannelManager:
    """渠道配置管理器"""

    def __init__(self):
        self.crypto = get_crypto()

    def get_channel_types(self) -> List[Dict]:
        """获取所有渠道类型"""
        types = []
        for type_id, type_info in CHANNEL_TYPES.items():
            types.append({
                'id': type_id,
                'name': type_info['name'],
                'description': type_info['description'],
                'config_fields': type_info['config_fields'],
                'required_fields': type_info['required_fields']
            })
        return types

    def list_configs(self) -> List[Dict]:
        """获取所有渠道配置"""
        rows = db.fetch_all(
            'SELECT * FROM channel_configs ORDER BY created_at DESC'
        )

        configs = []
        for row in rows:
            config = self._row_to_config(row, include_secrets=False)
            configs.append(config)

        return configs

    def get_config(self, channel_type: str) -> Optional[Dict]:
        """获取指定渠道的配置"""
        row = db.fetch_one(
            'SELECT * FROM channel_configs WHERE channel_type = ?', (channel_type,)
        )

        if row:
            return self._row_to_config(row, include_secrets=False)
        return None

    def save_config(self, channel_type: str, config_data: Dict) -> Dict:
        """保存渠道配置"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 检查是否已存在配置
        existing = self.get_config(channel_type)

        # 加密敏感字段
        type_info = CHANNEL_TYPES.get(channel_type, {})
        sensitive_fields = ['app_secret', 'app_key']  # 这些字段需要加密

        encrypted_config = {}
        for key, value in config_data.items():
            if key in sensitive_fields and value:
                encrypted_config[key] = self.crypto.encrypt(value)
            else:
                encrypted_config[key] = value

        config_json = json.dumps(encrypted_config)

        if existing:
            # 更新
            db.update(
                'channel_configs',
                {
                    'config_encrypted': config_json,
                    'enabled': config_data.get('enabled', True),
                    'updated_at': now
                },
                'channel_type = ?',
                (channel_type,)
            )
        else:
            # 创建
            config_id = f"channel-{uuid.uuid4().hex[:8]}"
            db.execute(
                '''INSERT INTO channel_configs
                   (id, channel_type, config_encrypted, enabled, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (config_id, channel_type, config_json,
                 config_data.get('enabled', True), now, now)
            )

        return self.get_config(channel_type)

    def delete_config(self, channel_type: str) -> bool:
        """删除渠道配置"""
        existing = self.get_config(channel_type)
        if not existing:
            return False

        db.delete('channel_configs', 'channel_type = ?', (channel_type,))
        return True

    def validate_config(self, channel_type: str, config_data: Dict) -> Dict:
        """验证配置完整性"""
        type_info = CHANNEL_TYPES.get(channel_type)
        if not type_info:
            return {'valid': False, 'errors': ['未知的渠道类型']}

        errors = []
        warnings = []

        # 检查必填字段
        for field in type_info['required_fields']:
            if not config_data.get(field):
                field_name = self._get_field_display_name(field)
                errors.append(f'{field_name} 为必填项')

        # 渠道特定验证
        if channel_type == 'feishu':
            if config_data.get('app_id') and not config_data['app_id'].startswith('cli_'):
                warnings.append('飞书 App ID 通常以 "cli_" 开头')

        elif channel_type == 'dingtalk':
            if config_data.get('app_key') and len(config_data['app_key']) < 10:
                warnings.append('钉钉 AppKey 长度可能不正确')

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def _row_to_config(self, row: Dict, include_secrets: bool = False) -> Dict:
        """将数据库行转换为配置字典"""
        config_json = row['config_encrypted'] or '{}'
        config_data = json.loads(config_json)

        result = {
            'id': row['id'],
            'channel_type': row['channel_type'],
            'enabled': bool(row['enabled']),
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }

        # 处理配置字段
        type_info = CHANNEL_TYPES.get(row['channel_type'], {})
        sensitive_fields = ['app_secret', 'app_key']

        for key, value in config_data.items():
            if key in sensitive_fields and value:
                if include_secrets:
                    # 解密
                    result[key] = self.crypto.decrypt(value)
                else:
                    # 脱敏
                    result[key + '_masked'] = self.crypto.mask_key(value)
            else:
                result[key] = value

        # 添加渠道类型信息
        result['channel_name'] = type_info.get('name', row['channel_type'])

        return result

    def _get_field_display_name(self, field: str) -> str:
        """获取字段的显示名称"""
        names = {
            'app_id': 'App ID',
            'app_secret': 'App Secret',
            'app_key': 'AppKey',
            'callback_url': '回调地址',
            'event_url': '事件订阅地址',
            'bot_name': '机器人名称',
            'agent_id': 'Agent ID'
        }
        return names.get(field, field)


# 全局实例
channel_manager = ChannelManager()