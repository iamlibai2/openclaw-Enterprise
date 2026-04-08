"""
Agent Profile API

将 Agent 视为"人"而非配置集合
提供 Agent 档案的读取和更新接口

注意：Admin UI 和 OpenClaw 可能部署在不同服务器
所有操作通过 Gateway API 实现，不直接访问文件系统
"""

import os
import json
import re
import copy
import zipfile
import io
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file
from functools import wraps
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from gateway_sync import sync_call, get_sync_client

bp = Blueprint('agent_profile', __name__, url_prefix='/api/agents')


# ============================================================
# 数据类定义
# ============================================================

@dataclass
class CloneOptions:
    """克隆选项"""
    name: str
    id: str
    clone_soul: bool = True
    clone_identity: bool = True
    clone_memory: bool = False
    clone_user: bool = True
    clone_skills: bool = True
    clone_tools: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> 'CloneOptions':
        return cls(
            name=data.get('name', ''),
            id=data.get('id', ''),
            clone_soul=data.get('cloneSoul', True),
            clone_identity=data.get('cloneIdentity', True),
            clone_memory=data.get('cloneMemory', False),
            clone_user=data.get('cloneUser', True),
            clone_skills=data.get('cloneSkills', True),
            clone_tools=data.get('cloneTools', True)
        )

    def validate(self) -> tuple[bool, str]:
        """验证选项"""
        if not self.name or not self.name.strip():
            return False, "名称不能为空"
        if not self.id or not self.id.strip():
            return False, "ID 不能为空"
        if not re.match(r'^[a-zA-Z0-9_-]+$', self.id):
            return False, "ID 只能包含字母、数字、下划线和横线"
        return True, ""


@dataclass
class AgentConfig:
    """Agent 配置"""
    id: str
    name: str
    model: Dict = field(default_factory=dict)
    skills: List[str] = field(default_factory=list)
    tools: Dict = field(default_factory=dict)
    subagents: Dict = field(default_factory=dict)
    workspace: Optional[str] = None
    is_default: bool = False

    def to_dict(self) -> dict:
        result = {
            'id': self.id,
            'name': self.name,
        }
        if self.model:
            result['model'] = self.model
        if self.skills:
            result['skills'] = self.skills
        if self.tools:
            result['tools'] = self.tools
        if self.subagents:
            result['subagents'] = self.subagents
        if self.workspace:
            result['workspace'] = self.workspace
        if self.is_default:
            result['default'] = True
        return result


# ============================================================
# Gateway API 封装
# ============================================================

class AgentGatewayClient:
    """
    Agent Gateway 客户端

    封装所有 Agent 相关的 Gateway API 调用
    """

    def __init__(self):
        self._config_cache: Optional[Dict] = None
        self._config_hash: Optional[str] = None

    # ------------------- 配置操作 -------------------

    def get_config(self, use_cache: bool = True) -> Dict:
        """获取完整配置"""
        if use_cache and self._config_cache is not None:
            return self._config_cache

        result = sync_call("config.get")
        self._config_cache = result.get("config", {})
        self._config_hash = result.get("hash")
        return self._config_cache

    def get_config_hash(self) -> Optional[str]:
        """获取配置 hash"""
        if self._config_hash is None:
            self.get_config()
        return self._config_hash

    def apply_config(self, config: Dict) -> bool:
        """应用配置变更"""
        import json5
        raw = json5.dumps(config)
        base_hash = self.get_config_hash()

        if not base_hash:
            raise ValueError("无法获取配置 hash")

        sync_call("config.apply", {
            "raw": raw,
            "baseHash": base_hash
        })

        # 清除缓存
        self._config_cache = None
        self._config_hash = None
        return True

    # ------------------- Agent 配置 -------------------

    def get_agents_list(self) -> List[Dict]:
        """获取 Agent 列表"""
        config = self.get_config()
        return config.get("agents", {}).get("list", [])

    def get_agent_config(self, agent_id: str) -> Optional[Dict]:
        """获取单个 Agent 配置"""
        agents = self.get_agents_list()
        for agent in agents:
            if agent.get("id") == agent_id:
                return agent
        return None

    def agent_exists(self, agent_id: str) -> bool:
        """检查 Agent 是否存在"""
        return self.get_agent_config(agent_id) is not None

    def add_agent(self, agent_config: AgentConfig) -> bool:
        """添加新 Agent"""
        config = self.get_config()

        if "agents" not in config:
            config["agents"] = {}
        if "list" not in config["agents"]:
            config["agents"]["list"] = []

        config["agents"]["list"].append(agent_config.to_dict())
        return self.apply_config(config)

    # ------------------- 文件操作 -------------------

    def get_agent_file(self, agent_id: str, filename: str) -> Optional[str]:
        """获取 Agent 文件内容"""
        try:
            result = sync_call("agents.files.get", {
                "agentId": agent_id,
                "name": filename
            })
            file_info = result.get("file", {})
            return file_info.get("content", "")
        except Exception:
            return None

    def set_agent_file(self, agent_id: str, filename: str, content: str) -> bool:
        """设置 Agent 文件内容"""
        try:
            sync_call("agents.files.set", {
                "agentId": agent_id,
                "name": filename,
                "content": content
            })
            return True
        except Exception:
            return False

    def list_agent_files(self, agent_id: str) -> List[Dict]:
        """列出 Agent 文件"""
        try:
            result = sync_call("agents.files.list", {
                "agentId": agent_id
            })
            return result.get("files", [])
        except Exception:
            return []

    # ------------------- Skills 操作 -------------------

    def get_available_skills(self) -> List[str]:
        """获取可用的 Skills 列表"""
        try:
            result = sync_call("skills.status")
            entries = result.get("entries", {})
            # 返回已安装且启用的 skills
            return [
                key for key, value in entries.items()
                if isinstance(value, dict) and value.get("enabled", False)
            ]
        except Exception:
            return []

    def filter_valid_skills(self, skills: List[str]) -> List[str]:
        """过滤出有效的 skills"""
        available = set(self.get_available_skills())
        return [s for s in skills if s in available]


# 全局客户端实例
_gateway_client = AgentGatewayClient()


def get_gateway_client() -> AgentGatewayClient:
    """获取 Gateway 客户端"""
    return _gateway_client


# ============================================================
# 认证装饰器
# ============================================================

def auth_required(f):
    """认证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'success': False, 'error': '未授权'}), 401
        return f(*args, **kwargs)
    return decorated


# ============================================================
# 克隆功能实现
# ============================================================

class AgentCloner:
    """
    Agent 克隆器

    负责克隆 Agent 的所有逻辑
    """

    # 默认复制的文件列表
    DEFAULT_FILES = ['SOUL.md', 'IDENTITY.md', 'USER.md', 'MEMORY.md']

    def __init__(self, client: AgentGatewayClient):
        self.client = client

    def clone(self, source_id: str, options: CloneOptions) -> Dict[str, Any]:
        """
        克隆 Agent

        Args:
            source_id: 源 Agent ID
            options: 克隆选项

        Returns:
            包含新 Agent 信息的字典

        Raises:
            ValueError: 参数错误
            RuntimeError: 克隆失败
        """
        # 1. 验证选项
        valid, msg = options.validate()
        if not valid:
            raise ValueError(msg)

        # 2. 检查源 Agent 是否存在
        source_config = self.client.get_agent_config(source_id)
        if not source_config:
            raise ValueError(f"源 Agent '{source_id}' 不存在")

        # 3. 检查目标 ID 是否已存在
        if self.client.agent_exists(options.id):
            raise ValueError(f"Agent ID '{options.id}' 已存在")

        # 4. 构建新 Agent 配置
        new_config = self._build_new_config(source_config, options)

        # 5. 添加 Agent 配置
        self.client.add_agent(new_config)

        # 6. 复制文件
        copied_files = self._copy_files(source_id, options.id, options)

        return {
            'id': options.id,
            'name': options.name,
            'copiedFiles': copied_files
        }

    def _build_new_config(self, source: Dict, options: CloneOptions) -> AgentConfig:
        """构建新 Agent 配置"""
        config = AgentConfig(
            id=options.id,
            name=options.name,
            is_default=False
        )

        # 设置 workspace（使用默认路径格式）
        config.workspace = f"~/.openclaw/workspace-{options.id}"

        # 复制模型配置
        config.model = copy.deepcopy(source.get('model', {}))

        # 复制技能（过滤不存在的）
        if options.clone_skills:
            source_skills = source.get('skills', [])
            config.skills = self.client.filter_valid_skills(source_skills)

        # 复制工具配置
        if options.clone_tools:
            config.tools = copy.deepcopy(source.get('tools', {}))

        # 复制子 Agent 配置
        config.subagents = copy.deepcopy(source.get('subagents', {}))

        return config

    def _copy_files(self, source_id: str, target_id: str,
                    options: CloneOptions) -> List[str]:
        """复制文件"""
        copied = []

        # 确定要复制的文件
        files_to_copy = []
        if options.clone_soul:
            files_to_copy.append('SOUL.md')
        if options.clone_identity:
            files_to_copy.append('IDENTITY.md')
        if options.clone_user:
            files_to_copy.append('USER.md')
        if options.clone_memory:
            files_to_copy.append('MEMORY.md')

        for filename in files_to_copy:
            content = self.client.get_agent_file(source_id, filename)
            if content:
                # 如果是 IDENTITY.md，需要更新名字
                if filename == 'IDENTITY.md':
                    content = self._update_identity_name(content, options.name)

                if self.client.set_agent_file(target_id, filename, content):
                    copied.append(filename)

        return copied

    def _update_identity_name(self, content: str, new_name: str) -> str:
        """更新 IDENTITY.md 中的名字"""
        lines = content.split('\n')
        updated_lines = []

        for line in lines:
            if line.strip().startswith('- **Name:**') or line.strip().startswith('- **名字:**'):
                # 提取前缀
                if '- **Name:**' in line:
                    updated_lines.append(f'- **Name:** {new_name}')
                else:
                    updated_lines.append(f'- **名字:** {new_name}')
            else:
                updated_lines.append(line)

        return '\n'.join(updated_lines)


# ============================================================
# 导出功能实现
# ============================================================

class AgentExporter:
    """
    Agent 导出器

    负责将 Agent 打包为 .openclaw-agent 文件
    """

    def __init__(self, client: AgentGatewayClient):
        self.client = client

    def export(self, agent_id: str, include_memory: bool = False) -> io.BytesIO:
        """
        导出 Agent 为 zip 文件流

        Args:
            agent_id: Agent ID
            include_memory: 是否包含记忆文件

        Returns:
            BytesIO 流，可直接返回给客户端下载

        Raises:
            ValueError: Agent 不存在
        """
        # 1. 获取 Agent 配置
        agent_config = self.client.get_agent_config(agent_id)
        if not agent_config:
            raise ValueError(f"Agent '{agent_id}' 不存在")

        agent_name = agent_config.get('name', agent_id)

        # 2. 构建 manifest
        manifest = self._build_manifest(agent_config, include_memory)

        # 3. 创建 zip 文件
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 写入 manifest
            zf.writestr('manifest.json', json.dumps(manifest, indent=2, ensure_ascii=False))

            # 写入文件
            files_to_export = ['SOUL.md', 'IDENTITY.md', 'USER.md']
            if include_memory:
                files_to_export.append('MEMORY.md')

            for filename in files_to_export:
                content = self.client.get_agent_file(agent_id, filename)
                if content:
                    # 统一使用小写文件名
                    zf.writestr(filename.lower(), content)

            # 写入配置文件
            zf.writestr('skills.json', json.dumps(agent_config.get('skills', []), indent=2))
            zf.writestr('tools.json', json.dumps(agent_config.get('tools', {}), indent=2, ensure_ascii=False))
            zf.writestr('model.json', json.dumps(agent_config.get('model', {}), indent=2, ensure_ascii=False))

        zip_buffer.seek(0)
        return zip_buffer

    def _build_manifest(self, agent_config: Dict, include_memory: bool) -> Dict:
        """构建 manifest 元数据"""
        return {
            'name': agent_config.get('name', agent_config.get('id')),
            'id': agent_config.get('id'),
            'version': '1.0.0',
            'exportedAt': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'description': f"Agent exported from OpenClaw Admin UI",
            'components': {
                'soul': True,
                'identity': True,
                'user': True,
                'skills': bool(agent_config.get('skills')),
                'tools': bool(agent_config.get('tools')),
                'model': bool(agent_config.get('model')),
                'memory': include_memory
            }
        }


# ============================================================
# API 端点
# ============================================================

@bp.route('/list', methods=['GET'])
@auth_required
def list_agents():
    """获取 Agent 列表"""
    client = get_gateway_client()

    try:
        agents = client.get_agents_list()
        result = []

        for agent in agents:
            result.append({
                'id': agent.get('id'),
                'name': agent.get('name', agent.get('id')),
                'isDefault': agent.get('default', False),
                'emoji': '🤖',  # TODO: 从 IDENTITY.md 读取
                'stats': {
                    'memoryCount': 0,
                    'skillCount': len(agent.get('skills', [])),
                    'toolCount': len(agent.get('tools', {}).get('alsoAllow', []))
                }
            })

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<agent_id>/profile', methods=['GET'])
@auth_required
def get_profile(agent_id):
    """获取 Agent 完整档案"""
    client = get_gateway_client()

    try:
        agent_config = client.get_agent_config(agent_id)
        if not agent_config:
            return jsonify({'success': False, 'error': 'Agent 不存在'}), 404

        # 读取文件内容
        soul_content = client.get_agent_file(agent_id, 'SOUL.md') or ''
        identity_content = client.get_agent_file(agent_id, 'IDENTITY.md') or ''
        user_content = client.get_agent_file(agent_id, 'USER.md') or ''

        profile = {
            'id': agent_id,
            'name': agent_config.get('name', agent_id),
            'isDefault': agent_config.get('default', False),
            'workspace': agent_config.get('workspace', ''),
            'soul': {
                'content': soul_content,
                'coreTruths': [],
                'boundaries': [],
                'vibe': ''
            },
            'identity': {
                'content': identity_content,
                'name': '',
                'creature': '',
                'vibe': '',
                'emoji': '',
                'avatar': ''
            },
            'user': {
                'content': user_content,
                'name': '',
                'pronouns': '',
                'timezone': '',
                'notes': '',
                'context': ''
            },
            'memory': {
                'longTermMemory': '',
                'longTermMemorySize': 0,
                'dailyMemories': [],
                'totalSize': 0,
                'lastUpdated': ''
            },
            'skills': agent_config.get('skills', []),
            'tools': {
                'profile': agent_config.get('tools', {}).get('profile', 'default'),
                'alsoAllow': agent_config.get('tools', {}).get('alsoAllow', []),
                'toolCount': len(agent_config.get('tools', {}).get('alsoAllow', []))
            },
            'model': {
                'primary': agent_config.get('model', {}).get('primary', 'unknown'),
                'fallback': agent_config.get('model', {}).get('fallback')
            },
            'subagents': {
                'allowAgents': agent_config.get('subagents', {}).get('allowAgents', []),
                'denyAgents': agent_config.get('subagents', {}).get('denyAgents', [])
            },
            'stats': {
                'memoryCount': 0,
                'memorySize': 0,
                'skillCount': len(agent_config.get('skills', [])),
                'toolCount': len(agent_config.get('tools', {}).get('alsoAllow', [])),
                'lastActiveAt': None,
                'conversationCount': None
            }
        }

        return jsonify({'success': True, 'data': profile})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<agent_id>/clone', methods=['POST'])
@auth_required
def clone_agent(agent_id):
    """
    克隆 Agent

    Body:
    {
        "name": "新Agent名称",
        "id": "新AgentID",
        "cloneSoul": true,
        "cloneIdentity": true,
        "cloneMemory": false,
        "cloneUser": true,
        "cloneSkills": true,
        "cloneTools": true
    }
    """
    client = get_gateway_client()
    data = request.get_json() or {}

    try:
        # 构建克隆选项
        options = CloneOptions.from_dict(data)

        # 执行克隆
        cloner = AgentCloner(client)
        result = cloner.clone(agent_id, options)

        return jsonify({
            'success': True,
            'data': {
                'id': result['id'],
                'name': result['name'],
                'copiedFiles': result['copiedFiles']
            }
        })

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'克隆失败: {str(e)}'}), 500


@bp.route('/<agent_id>/soul', methods=['PUT'])
@auth_required
def update_soul(agent_id):
    """更新灵魂文件"""
    client = get_gateway_client()
    data = request.get_json() or {}

    content = data.get('content', '')
    if not content:
        return jsonify({'success': False, 'error': '内容不能为空'}), 400

    if client.set_agent_file(agent_id, 'SOUL.md', content):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '保存失败'}), 500


@bp.route('/<agent_id>/identity', methods=['PUT'])
@auth_required
def update_identity(agent_id):
    """更新身份文件"""
    client = get_gateway_client()
    data = request.get_json() or {}

    # 读取现有内容
    content = client.get_agent_file(agent_id, 'IDENTITY.md') or ''

    # 更新字段
    if data.get('name'):
        content = re.sub(
            r'- \*\*Name:\*\*.*',
            f'- **Name:** {data["name"]}',
            content
        )
        content = re.sub(
            r'- \*\*名字:\*\*.*',
            f'- **名字:** {data["name"]}',
            content
        )
    if data.get('emoji'):
        content = re.sub(
            r'- \*\*Emoji:\*\*.*',
            f'- **Emoji:** {data["emoji"]}',
            content
        )

    if client.set_agent_file(agent_id, 'IDENTITY.md', content):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '保存失败'}), 500


@bp.route('/<agent_id>/user', methods=['PUT'])
@auth_required
def update_user(agent_id):
    """更新主人信息"""
    client = get_gateway_client()
    data = request.get_json() or {}

    content = client.get_agent_file(agent_id, 'USER.md') or ''

    if data.get('name'):
        content = re.sub(
            r'- \*\*Name:\*\*.*',
            f'- **Name:** {data["name"]}',
            content
        )
        content = re.sub(
            r'- \*\*称呼:\*\*.*',
            f'- **称呼:** {data["name"]}',
            content
        )
    if data.get('timezone'):
        content = re.sub(
            r'- \*\*Timezone:\*\*.*',
            f'- **Timezone:** {data["timezone"]}',
            content
        )
        content = re.sub(
            r'- \*\*时区:\*\*.*',
            f'- **时区:** {data["timezone"]}',
            content
        )

    if client.set_agent_file(agent_id, 'USER.md', content):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '保存失败'}), 500


@bp.route('/<agent_id>/memory', methods=['PUT'])
@auth_required
def update_memory(agent_id):
    """更新长期记忆"""
    client = get_gateway_client()
    data = request.get_json() or {}

    content = data.get('content', '')

    if client.set_agent_file(agent_id, 'MEMORY.md', content):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '保存失败'}), 500


@bp.route('/<agent_id>/export', methods=['POST'])
@auth_required
def export_agent(agent_id):
    """
    导出 Agent

    Body:
    {
        "includeMemory": false  // 是否包含记忆文件
    }

    返回 .openclaw-agent 文件（zip 格式）
    """
    client = get_gateway_client()
    data = request.get_json() or {}
    include_memory = data.get('includeMemory', False)

    try:
        exporter = AgentExporter(client)
        zip_buffer = exporter.export(agent_id, include_memory)

        # 获取 Agent 名称用于文件名
        agent_config = client.get_agent_config(agent_id)
        agent_name = agent_config.get('name', agent_id) if agent_config else agent_id
        date_str = datetime.now().strftime('%Y%m%d')

        filename = f"{agent_name}_{date_str}.openclaw-agent"

        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': f'导出失败: {str(e)}'}), 500


@bp.route('/import', methods=['POST'])
@auth_required
def import_agent():
    """
    导入 Agent

    接收 .openclaw-agent 文件（zip 格式）
    """
    client = get_gateway_client()

    # 检查文件
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未上传文件'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': '文件名为空'}), 400

    # 检查文件扩展名
    if not file.filename.endswith('.openclaw-agent'):
        return jsonify({'success': False, 'error': '文件格式错误，需要 .openclaw-agent 文件'}), 400

    try:
        # 解析 zip 文件
        zip_data = io.BytesIO(file.read())

        with zipfile.ZipFile(zip_data, 'r') as zf:
            # 读取 manifest
            if 'manifest.json' not in zf.namelist():
                return jsonify({'success': False, 'error': '无效的导入文件：缺少 manifest.json'}), 400

            manifest = json.loads(zf.read('manifest.json').decode('utf-8'))

            # 生成 Agent ID（使用 manifest 中的 id 或生成新的）
            agent_id = manifest.get('id', '')
            agent_name = manifest.get('name', '导入的 Agent')

            # 检查 ID 是否已存在，如果存在则生成新 ID
            base_id = agent_id
            counter = 1
            while client.agent_exists(agent_id):
                agent_id = f"{base_id}_{counter}"
                counter += 1

            # 读取配置文件
            skills = []
            tools = {}
            model = {}

            if 'skills.json' in zf.namelist():
                skills = json.loads(zf.read('skills.json').decode('utf-8'))

            if 'tools.json' in zf.namelist():
                tools = json.loads(zf.read('tools.json').decode('utf-8'))

            if 'model.json' in zf.namelist():
                model = json.loads(zf.read('model.json').decode('utf-8'))

            # 过滤有效的 skills
            skills = client.filter_valid_skills(skills)

            # 创建 Agent 配置
            new_config = AgentConfig(
                id=agent_id,
                name=agent_name,
                model=model,
                skills=skills,
                tools=tools,
                is_default=False
            )

            # 设置 workspace
            new_config.workspace = f"~/.openclaw/workspace-{agent_id}"

            # 添加 Agent
            client.add_agent(new_config)

            # 写入文件
            imported_files = []

            file_mapping = {
                'soul.md': 'SOUL.md',
                'identity.md': 'IDENTITY.md',
                'user.md': 'USER.md',
                'memory.md': 'MEMORY.md'
            }

            for zip_name, agent_name in file_mapping.items():
                if zip_name in zf.namelist():
                    content = zf.read(zip_name).decode('utf-8')
                    if client.set_agent_file(agent_id, agent_name, content):
                        imported_files.append(agent_name)

            return jsonify({
                'success': True,
                'data': {
                    'id': agent_id,
                    'name': agent_name,
                    'importedFiles': imported_files
                }
            })

    except zipfile.BadZipFile:
        return jsonify({'success': False, 'error': '无效的 zip 文件'}), 400
    except json.JSONDecodeError:
        return jsonify({'success': False, 'error': 'JSON 解析失败'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'导入失败: {str(e)}'}), 500


# ============================================================
# 模板库 API
# ============================================================

TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'


@bp.route('/templates', methods=['GET'])
@auth_required
def list_templates():
    """获取模板列表"""
    try:
        templates = []

        if TEMPLATES_DIR.exists():
            for template_dir in TEMPLATES_DIR.iterdir():
                if template_dir.is_dir() and template_dir.name != '__pycache__':
                    manifest_path = template_dir / 'manifest.json'
                    if manifest_path.exists():
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            manifest = json.load(f)

                        templates.append({
                            'id': manifest.get('id', template_dir.name),
                            'name': manifest.get('name', template_dir.name),
                            'description': manifest.get('description', ''),
                            'recommendedTools': manifest.get('recommendedTools', []),
                            'recommendedSkills': manifest.get('recommendedSkills', []),
                            'emoji': _get_template_emoji(template_dir)
                        })

        return jsonify({'success': True, 'data': templates})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _get_template_emoji(template_dir: Path) -> str:
    """从 identity.md 读取 emoji"""
    identity_path = template_dir / 'identity.md'
    if identity_path.exists():
        with open(identity_path, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'- \*\*Emoji:\*\*\s*(\S+)', content)
            if match:
                return match.group(1)
    return '🤖'


@bp.route('/templates/<template_id>', methods=['GET'])
@auth_required
def get_template(template_id):
    """获取单个模板详情"""
    try:
        # 查找模板目录
        template_dir = None
        for dir_path in TEMPLATES_DIR.iterdir():
            if dir_path.is_dir():
                manifest_path = dir_path / 'manifest.json'
                if manifest_path.exists():
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    if manifest.get('id') == template_id or dir_path.name == template_id:
                        template_dir = dir_path
                        break

        if not template_dir:
            return jsonify({'success': False, 'error': '模板不存在'}), 404

        # 读取所有文件
        manifest_path = template_dir / 'manifest.json'
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        template_data = {
            'id': manifest.get('id'),
            'name': manifest.get('name'),
            'description': manifest.get('description', ''),
            'files': {}
        }

        # 读取各文件
        for filename in ['soul.md', 'identity.md', 'user.md', 'skills.json', 'tools.json', 'model.json']:
            file_path = template_dir / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    template_data['files'][filename] = f.read()

        return jsonify({'success': True, 'data': template_data})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/create', methods=['POST'])
@auth_required
def create_from_template():
    """
    从模板创建 Agent

    Body:
    {
        "templateId": "admin_assistant",  // 模板 ID
        "name": "我的助理",               // 新 Agent 名称
        "id": "my_assistant",            // 新 Agent ID
        "customize": {                   // 可选的自定义内容
            "soul": "...",
            "identity": "...",
            "user": "..."
        }
    }
    """
    client = get_gateway_client()
    data = request.get_json() or {}

    template_id = data.get('templateId')
    agent_name = data.get('name')
    agent_id = data.get('id')
    customize = data.get('customize', {})

    # 验证参数
    if not template_id:
        return jsonify({'success': False, 'error': '模板 ID 不能为空'}), 400
    if not agent_name or not agent_name.strip():
        return jsonify({'success': False, 'error': '名称不能为空'}), 400
    if not agent_id or not agent_id.strip():
        return jsonify({'success': False, 'error': 'ID 不能为空'}), 400
    if not re.match(r'^[a-zA-Z0-9_-]+$', agent_id):
        return jsonify({'success': False, 'error': 'ID 只能包含字母、数字、下划线和横线'}), 400

    # 检查 ID 是否已存在
    if client.agent_exists(agent_id):
        return jsonify({'success': False, 'error': f"Agent ID '{agent_id}' 已存在"}), 400

    try:
        # 查找模板目录
        template_dir = None
        for dir_path in TEMPLATES_DIR.iterdir():
            if dir_path.is_dir():
                manifest_path = dir_path / 'manifest.json'
                if manifest_path.exists():
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    if manifest.get('id') == template_id or dir_path.name == template_id:
                        template_dir = dir_path
                        break

        if not template_dir:
            return jsonify({'success': False, 'error': '模板不存在'}), 404

        # 读取模板配置
        tools_path = template_dir / 'tools.json'
        model_path = template_dir / 'model.json'

        with open(tools_path, 'r', encoding='utf-8') as f:
            tools_config = json.load(f)

        with open(model_path, 'r', encoding='utf-8') as f:
            model_config = json.load(f)

        # 创建 Agent 配置
        new_config = AgentConfig(
            id=agent_id,
            name=agent_name,
            model=model_config,
            tools=tools_config,
            is_default=False
        )

        # 设置 workspace
        new_config.workspace = f"~/.openclaw/workspace-{agent_id}"

        # 添加 Agent
        client.add_agent(new_config)

        # 写入文件
        created_files = []

        # soul.md
        soul_content = customize.get('soul') or _read_template_file(template_dir, 'soul.md')
        if soul_content and client.set_agent_file(agent_id, 'SOUL.md', soul_content):
            created_files.append('SOUL.md')

        # identity.md - 需要更新名字
        identity_content = customize.get('identity') or _read_template_file(template_dir, 'identity.md')
        if identity_content:
            # 更新 identity 中的名字
            identity_content = re.sub(
                r'- \*Name:\*\s*.*',
                f'- **Name:** {agent_name}',
                identity_content
            )
            identity_content = re.sub(
                r'- \*名字:\*\s*.*',
                f'- **名字:** {agent_name}',
                identity_content
            )
            if client.set_agent_file(agent_id, 'IDENTITY.md', identity_content):
                created_files.append('IDENTITY.md')

        # user.md
        user_content = customize.get('user') or _read_template_file(template_dir, 'user.md')
        if user_content and client.set_agent_file(agent_id, 'USER.md', user_content):
            created_files.append('USER.md')

        return jsonify({
            'success': True,
            'data': {
                'id': agent_id,
                'name': agent_name,
                'createdFiles': created_files,
                'template': template_id
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'创建失败: {str(e)}'}), 500


@bp.route('/<agent_id>/tools', methods=['GET'])
@auth_required
def get_agent_tools(agent_id):
    """获取 Agent 工具权限配置"""
    client = get_gateway_client()

    try:
        agent_config = client.get_agent_config(agent_id)
        if not agent_config:
            return jsonify({'success': False, 'error': 'Agent 不存在'}), 404

        tools_config = agent_config.get('tools', {})

        return jsonify({
            'success': True,
            'data': {
                'profile': tools_config.get('profile', 'default'),
                'alsoAllow': tools_config.get('alsoAllow', [])
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<agent_id>/tools', methods=['PUT'])
@auth_required
def update_agent_tools(agent_id):
    """更新 Agent 工具权限配置"""
    client = get_gateway_client()
    data = request.get_json() or {}

    profile = data.get('profile', 'default')
    also_allow = data.get('alsoAllow', [])

    try:
        # 获取当前配置
        config = client.get_config()
        agents_list = config.get('agents', {}).get('list', [])

        # 找到并更新指定 Agent
        found = False
        for agent in agents_list:
            if agent.get('id') == agent_id:
                agent['tools'] = {
                    'profile': profile,
                    'alsoAllow': also_allow
                }
                found = True
                break

        if not found:
            return jsonify({'success': False, 'error': 'Agent 不存在'}), 404

        # 应用配置
        client.apply_config(config)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/tools-catalog', methods=['GET'])
@auth_required
def get_tools_catalog():
    """获取工具目录"""
    try:
        result = sync_call('tools.catalog')
        return jsonify({
            'success': True,
            'data': {
                'profiles': result.get('profiles', []),
                'groups': result.get('groups', [])
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _read_template_file(template_dir: Path, filename: str) -> Optional[str]:
    """读取模板文件"""
    file_path = template_dir / filename
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None


# ============================================================
# Agent 扩展档案 API（拟人化属性）
# ============================================================

from database import db


@bp.route('/<agent_id>/extended-profile', methods=['GET'])
@auth_required
def get_extended_profile(agent_id):
    """获取 Agent 扩展档案（拟人化属性）"""
    try:
        profile = db.fetch_one(
            "SELECT * FROM agent_profiles WHERE agent_id = ?",
            (agent_id,)
        )

        if not profile:
            # 返回默认空数据
            return jsonify({
                'success': True,
                'data': {
                    'agent_id': agent_id,
                    'gender': None,
                    'birthday': None,
                    'age_display': None,
                    'personality': None,
                    'hobbies': [],
                    'voice_style': None,
                    'custom_fields': {},
                    'total_conversations': 0,
                    'total_tokens': 0,
                    'admin_notes': None,
                    'tags': []
                }
            })

        # 解析 JSON 字段
        result = dict(profile)
        if result.get('hobbies'):
            try:
                result['hobbies'] = json.loads(result['hobbies'])
            except:
                result['hobbies'] = []
        else:
            result['hobbies'] = []

        if result.get('custom_fields'):
            try:
                result['custom_fields'] = json.loads(result['custom_fields'])
            except:
                result['custom_fields'] = {}
        else:
            result['custom_fields'] = {}

        if result.get('tags'):
            try:
                result['tags'] = json.loads(result['tags'])
            except:
                result['tags'] = []
        else:
            result['tags'] = []

        return jsonify({'success': True, 'data': result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<agent_id>/extended-profile', methods=['PUT'])
@auth_required
def update_extended_profile(agent_id):
    """更新 Agent 扩展档案"""
    data = request.get_json() or {}

    try:
        # 检查是否已存在
        existing = db.fetch_one(
            "SELECT agent_id FROM agent_profiles WHERE agent_id = ?",
            (agent_id,)
        )

        # 准备数据
        update_data = {
            'gender': data.get('gender'),
            'birthday': data.get('birthday'),
            'age_display': data.get('age_display'),
            'personality': data.get('personality'),
            'hobbies': json.dumps(data.get('hobbies', []), ensure_ascii=False) if data.get('hobbies') else None,
            'voice_style': data.get('voice_style'),
            'custom_fields': json.dumps(data.get('custom_fields', {}), ensure_ascii=False) if data.get('custom_fields') else None,
            'admin_notes': data.get('admin_notes'),
            'tags': json.dumps(data.get('tags', []), ensure_ascii=False) if data.get('tags') else None,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        if existing:
            # 更新
            db.update(
                'agent_profiles',
                update_data,
                'agent_id = ?',
                (agent_id,)
            )
        else:
            # 插入
            update_data['agent_id'] = agent_id
            update_data['total_conversations'] = 0
            update_data['total_tokens'] = 0
            db.insert('agent_profiles', update_data)

        return jsonify({'success': True, 'message': '保存成功'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<agent_id>/stats', methods=['POST'])
@auth_required
def update_agent_stats(agent_id):
    """更新 Agent 统计数据（内部调用）"""
    data = request.get_json() or {}

    try:
        # 检查是否已存在
        existing = db.fetch_one(
            "SELECT agent_id, total_conversations, total_tokens FROM agent_profiles WHERE agent_id = ?",
            (agent_id,)
        )

        if existing:
            # 累加更新
            new_conversations = existing['total_conversations'] + data.get('conversation_add', 0)
            new_tokens = existing['total_tokens'] + data.get('token_add', 0)

            db.update(
                'agent_profiles',
                {
                    'total_conversations': new_conversations,
                    'total_tokens': new_tokens,
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                'agent_id = ?',
                (agent_id,)
            )
        else:
            # 创建新记录
            db.insert('agent_profiles', {
                'agent_id': agent_id,
                'total_conversations': data.get('conversation_add', 0),
                'total_tokens': data.get('token_add', 0)
            })

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500