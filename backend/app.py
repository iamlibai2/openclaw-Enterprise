"""
OpenClaw Admin Backend - Flask API
企业级用户管理和权限系统
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from config_manager import ConfigManager
from database import db
from auth import (
    verify_password, hash_password, generate_tokens,
    verify_access_token, refresh_access_token
)
from decorators import (
    get_current_user, require_auth, require_permission,
    has_permission, log_operation, log_operation_direct, log_exceptions
)
from gateway_sync import get_sync_client, sync_call, GatewayError
from settings import settings
from logger import setup_logging, get_logger, log_error
from model_manager import model_manager, PROVIDER_TEMPLATES
from channel_manager import channel_manager, CHANNEL_TYPES
from config_sync import config_sync
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
import re
import yaml
import json5

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 初始化日志系统
setup_logging(app)
logger = get_logger('app')

# 配置管理器（保留用于某些本地模板操作）
# config_manager = ConfigManager()


def _get_agents_via_ws():
    """通过 WebSocket 获取 Agent 列表（合并配置中的 workspace 信息）"""
    # 从 agents.list 获取基本信息
    result = sync_call('agents.list')
    agents = result.get('agents', [])

    # 从 config.get 获取 workspace 信息
    config = _get_config_via_ws()
    agents_config = config.get('agents', {}).get('list', [])

    # 创建 workspace 映射
    workspace_map = {a.get('id'): a.get('workspace') for a in agents_config}

    # 合并 workspace 信息
    for agent in agents:
        agent_id = agent.get('id')
        if agent_id in workspace_map:
            agent['workspace'] = workspace_map[agent_id]

    return agents


def _get_agent_via_ws(agent_id):
    """通过 WebSocket 获取单个 Agent"""
    agents = _get_agents_via_ws()
    return next((a for a in agents if a.get('id') == agent_id), None)


# 配置 hash 缓存（用于乐观锁）
_config_hash = None


def _get_config_via_ws():
    """通过 WebSocket 获取配置"""
    global _config_hash
    result = sync_call('config.get')
    _config_hash = result.get('hash')
    return result.get('config', {})


def _save_config_via_ws(config: dict):
    """通过 WebSocket 保存配置"""
    global _config_hash
    raw = json5.dumps(config)
    sync_call('config.apply', {
        'raw': raw,
        'baseHash': _config_hash or ''
    })
    # 保存成功后更新 hash
    result = sync_call('config.get')
    _config_hash = result.get('hash')


def _patch_config(patch: dict, max_retries: int = 3) -> dict:
    """
    部分更新配置（带重试机制）

    Args:
        patch: 要更新的配置片段，如 {'skills': {'entries': {'xxx': {'enabled': False}}}}
        max_retries: 最大重试次数

    Returns:
        更新结果

    Example:
        result = _patch_config({
            'skills': {
                'entries': {
                    'my-skill': {'enabled': False}
                }
            }
        })
    """
    import time

    patch_raw = json5.dumps(patch)
    last_error = None

    for attempt in range(max_retries):
        try:
            result = sync_call('config.get')
            hash = result.get('hash')
            result = sync_call('config.patch', {'raw': patch_raw, 'baseHash': hash})
            return result
        except GatewayError as e:
            last_error = e
            error_str = str(e).lower()
            # 检测配置冲突错误，需要重试
            if any(x in error_str for x in ['hash', 'conflict', 'changed', 'stale']):
                logger.warning(f"Config patch conflict, retrying ({attempt + 1}/{max_retries}): {e}")
                time.sleep(0.1 * (attempt + 1))
                continue
            raise
        except Exception as e:
            last_error = e
            logger.error(f"Config patch error: {e}")
            raise

    raise Exception(f"配置更新失败，重试耗尽: {last_error}")


# ==================== 认证 API ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查（公开）"""
    return jsonify({'status': 'ok', 'message': 'OpenClaw Admin Backend is running'})


@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            return jsonify({'success': False, 'error': '请输入用户名和密码'}), 400

        # 查询用户
        user = db.fetch_one(
            "SELECT u.id, u.username, u.password_hash, u.display_name, u.is_active, "
            "r.id as role_id, r.name as role_name, r.permissions "
            "FROM users u JOIN roles r ON u.role_id = r.id "
            "WHERE u.username = ?",
            (username,)
        )

        if not user:
            return jsonify({'success': False, 'error': '用户名或密码错误'}), 401

        if not user['is_active']:
            return jsonify({'success': False, 'error': '账户已被禁用'}), 401

        if not verify_password(password, user['password_hash']):
            return jsonify({'success': False, 'error': '用户名或密码错误'}), 401

        # 生成 Token
        access_token, refresh_token = generate_tokens(
            user['id'], user['username'], user['role_name']
        )

        # 更新最后登录时间
        db.update(
            'users',
            {'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
            'id = ?',
            (user['id'],)
        )

        # 记录登录日志
        log_operation_direct('login', 'user', str(user['id']))

        return jsonify({
            'success': True,
            'data': {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'display_name': user['display_name'],
                    'role': user['role_name'],
                    'permissions': json.loads(user['permissions'])
                }
            },
            'message': '登录成功'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """用户登出"""
    user = get_current_user()
    log_operation_direct('logout', 'user', str(user['user_id']))
    return jsonify({'success': True, 'message': '登出成功'})


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user_info():
    """获取当前用户信息"""
    user = get_current_user()
    user_info = db.fetch_one(
        "SELECT u.id, u.username, u.email, u.display_name, u.last_login, "
        "r.name as role_name, r.permissions "
        "FROM users u JOIN roles r ON u.role_id = r.id "
        "WHERE u.id = ?",
        (user['user_id'],)
    )

    if not user_info:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    return jsonify({
        'success': True,
        'data': {
            'id': user_info['id'],
            'username': user_info['username'],
            'email': user_info['email'],
            'display_name': user_info['display_name'],
            'role': user_info['role_name'],
            'permissions': json.loads(user_info['permissions']),
            'last_login': user_info['last_login']
        }
    })


@app.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    """刷新 Access Token"""
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token', '')

        if not refresh_token:
            return jsonify({'success': False, 'error': '缺少 refresh_token'}), 400

        new_access_token = refresh_access_token(refresh_token, db)
        if not new_access_token:
            return jsonify({'success': False, 'error': 'Token 无效或已过期'}), 401

        return jsonify({
            'success': True,
            'data': {'access_token': new_access_token},
            'message': 'Token 已刷新'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/change-password', methods=['POST'])
@require_auth
def change_password():
    """修改密码"""
    try:
        user = get_current_user()
        data = request.get_json()
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')

        if not old_password or not new_password:
            return jsonify({'success': False, 'error': '请输入旧密码和新密码'}), 400

        if len(new_password) < 6:
            return jsonify({'success': False, 'error': '新密码至少6位'}), 400

        # 获取用户当前密码
        user_info = db.fetch_one(
            "SELECT password_hash FROM users WHERE id = ?",
            (user['user_id'],)
        )

        if not verify_password(old_password, user_info['password_hash']):
            return jsonify({'success': False, 'error': '旧密码错误'}), 401

        # 更新密码
        new_hash = hash_password(new_password)
        db.update('users', {'password_hash': new_hash}, 'id = ?', (user['user_id'],))

        log_operation_direct('change_password', 'user', str(user['user_id']))

        return jsonify({'success': True, 'message': '密码已修改'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 用户管理 API ====================

@app.route('/api/users', methods=['GET'])
@require_permission('users', 'read')
def get_users():
    """获取用户列表"""
    try:
        users = db.fetch_all(
            "SELECT u.id, u.username, u.email, u.display_name, u.is_active, "
            "u.last_login, u.created_at, r.name as role_name "
            "FROM users u JOIN roles r ON u.role_id = r.id "
            "ORDER BY u.id"
        )
        return jsonify({'success': True, 'data': users})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users', methods=['POST'])
@require_permission('users', 'write')
def create_user():
    """创建用户"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()
        display_name = data.get('display_name', '').strip()
        role_id = data.get('role_id', 3)  # 默认 viewer

        if not username or not password:
            return jsonify({'success': False, 'error': '缺少用户名或密码'}), 400

        if len(password) < 6:
            return jsonify({'success': False, 'error': '密码至少6位'}), 400

        # 检查用户名是否已存在
        existing = db.fetch_one("SELECT id FROM users WHERE username = ?", (username,))
        if existing:
            return jsonify({'success': False, 'error': '用户名已存在'}), 400

        # 创建用户
        password_hash = hash_password(password)
        user_id = db.insert('users', {
            'username': username,
            'password_hash': password_hash,
            'email': email,
            'display_name': display_name or username,
            'role_id': role_id,
            'is_active': 1
        })

        log_operation_direct('create_user', 'user', str(user_id), json.dumps({'username': username, 'role_id': role_id}))

        return jsonify({
            'success': True,
            'data': {'id': user_id, 'username': username},
            'message': '用户创建成功'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@require_permission('users', 'write')
def update_user(user_id):
    """更新用户"""
    try:
        data = request.get_json()
        current_user = get_current_user()

        # 不能修改自己的角色和状态（防止自己把自己锁住）
        if user_id == current_user['user_id']:
            if 'role_id' in data or 'is_active' in data:
                return jsonify({'success': False, 'error': '不能修改自己的角色或状态'}), 400

        update_data = {}
        if 'display_name' in data:
            update_data['display_name'] = data['display_name']
        if 'email' in data:
            update_data['email'] = data['email']
        if 'role_id' in data:
            update_data['role_id'] = data['role_id']
        if 'is_active' in data:
            update_data['is_active'] = data['is_active']
        if 'password' in data and data['password']:
            if len(data['password']) < 6:
                return jsonify({'success': False, 'error': '密码至少6位'}), 400
            update_data['password_hash'] = hash_password(data['password'])

        if update_data:
            update_data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            db.update('users', update_data, 'id = ?', (user_id,))
            log_operation_direct('update_user', 'user', str(user_id), json.dumps(update_data))

        return jsonify({'success': True, 'message': '用户已更新'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_permission('users', 'delete')
def delete_user(user_id):
    """删除用户"""
    try:
        current_user = get_current_user()

        # 不能删除自己
        if user_id == current_user['user_id']:
            return jsonify({'success': False, 'error': '不能删除自己'}), 400

        # 不能删除 admin (id=1)
        if user_id == 1:
            return jsonify({'success': False, 'error': '不能删除默认管理员'}), 400

        db.delete('users', 'id = ?', (user_id,))
        log_operation_direct('delete_user', 'user', str(user_id))

        return jsonify({'success': True, 'message': '用户已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 角色管理 API ====================

@app.route('/api/roles', methods=['GET'])
@require_auth
def get_roles():
    """获取角色列表"""
    try:
        roles = db.fetch_all("SELECT id, name, description, permissions, created_at FROM roles ORDER BY id")
        for role in roles:
            role['permissions'] = json.loads(role['permissions'])
        return jsonify({'success': True, 'data': roles})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/roles/<int:role_id>', methods=['PUT'])
@require_permission('roles', 'write')
def update_role(role_id):
    """更新角色权限"""
    try:
        data = request.get_json()
        update_data = {}

        if 'description' in data:
            update_data['description'] = data['description']
        if 'permissions' in data:
            update_data['permissions'] = json.dumps(data['permissions'])

        if update_data:
            db.update('roles', update_data, 'id = ?', (role_id,))
            log_operation_direct('update_role', 'role', str(role_id), json.dumps(update_data))

        return jsonify({'success': True, 'message': '角色已更新'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Agent API（受保护） ====================

@app.route('/api/agents', methods=['GET'])
@require_permission('agents', 'read')
def get_agents():
    """获取所有 Agent - 通过 WebSocket"""
    try:
        # 使用合并了 workspace 信息的函数
        agents = _get_agents_via_ws()

        # 获取模型列表
        models_result = sync_call('models.list')
        models = models_result.get('models', [])

        # 补充每个 agent 的模型名称
        for agent in agents:
            model_id = agent.get('model', {}).get('primary', '')
            agent['modelName'] = model_id
            for m in models:
                if m['id'] == model_id:
                    agent['modelName'] = m.get('name', model_id)
                    break

        # 检查用户权限，标记是否可编辑
        user = get_current_user()
        can_edit = has_permission(user, 'agents', 'write')
        can_delete = has_permission(user, 'agents', 'delete')

        return jsonify({
            'success': True,
            'data': agents,
            'models': models,
            'permissions': {'can_edit': can_edit, 'can_delete': can_delete}
        })
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/agents/<agent_id>', methods=['GET'])
@require_permission('agents', 'read')
def get_agent(agent_id):
    """获取单个 Agent - 通过 WebSocket"""
    try:
        # 使用合并了 workspace 信息的函数
        agent = _get_agent_via_ws(agent_id)

        if agent:
            return jsonify({'success': True, 'data': agent})
        else:
            return jsonify({'success': False, 'error': 'Agent not found'}), 404
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/agents', methods=['POST'])
@require_permission('agents', 'write')
def create_agent():
    """创建 Agent - 通过 WebSocket"""
    try:
        data = request.get_json()

        # WebSocket 的 agents.create 参数
        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'error': '缺少 Agent 名称'}), 400

        params = {'name': name}

        # 可选参数
        if data.get('model'):
            params['model'] = data['model']
        if data.get('workspace'):
            params['workspace'] = data['workspace']

        # 调用 WebSocket 创建 Agent
        result = sync_call('agents.create', params)
        agent = result.get('agent', {})

        log_operation_direct('create_agent', 'agent', agent.get('id'), json.dumps({'name': name}))

        return jsonify({
            'success': True,
            'data': agent,
            'message': f'Agent {agent.get("id")} 创建成功'
        })
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/agents/<agent_id>', methods=['PUT'])
@require_permission('agents', 'write')
def update_agent(agent_id):
    """更新 Agent - 通过 WebSocket"""
    try:
        data = request.get_json()

        # 构建 WebSocket 更新参数
        params = {'agentId': agent_id}

        # 支持的更新字段
        if 'name' in data:
            params['name'] = data['name']
        if 'model' in data:
            params['model'] = data['model']
        if 'workspace' in data:
            params['workspace'] = data['workspace']

        # 调用 WebSocket 更新 Agent
        result = sync_call('agents.update', params)
        agent = result.get('agent', {})

        log_operation_direct('update_agent', 'agent', agent_id)

        return jsonify({
            'success': True,
            'data': agent,
            'message': f'Agent {agent_id} 更新成功'
        })
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/agents/<agent_id>', methods=['DELETE'])
@require_permission('agents', 'delete')
def delete_agent(agent_id):
    """删除 Agent - 通过 WebSocket"""
    try:
        # 检查是否是默认 Agent（通过获取列表检查）
        result = sync_call('agents.list')
        agents = result.get('agents', [])
        agent = next((a for a in agents if a.get('id') == agent_id), None)

        if not agent:
            return jsonify({'success': False, 'error': 'Agent 不存在'}), 404

        if agent.get('default'):
            return jsonify({'success': False, 'error': '不能删除默认 Agent'}), 400

        # 调用 WebSocket 删除 Agent
        delete_result = sync_call('agents.delete', {
            'agentId': agent_id,
            'deleteFiles': True
        })

        log_operation_direct('delete_agent', 'agent', agent_id)
        return jsonify({'success': True, 'message': f'Agent {agent_id} 已删除'})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/agents/apply', methods=['POST'])
@require_permission('gateway', 'restart')
def apply_config():
    """应用配置（重启 Gateway）"""
    try:
        result = subprocess.run(
            ['openclaw', 'gateway', 'restart'],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            log_operation_direct('apply_config', 'gateway')
            return jsonify({'success': True, 'message': 'Gateway 已重启，配置已生效'})
        else:
            return jsonify({'success': False, 'error': result.stderr or 'Gateway 重启失败'}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Gateway 重启超时'}), 500
    except FileNotFoundError:
        log_operation_direct('apply_config', 'gateway')
        return jsonify({'success': True, 'message': '模拟重启成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 绑定 API（受保护） ====================

@app.route('/api/bindings', methods=['GET'])
@require_permission('bindings', 'read')
def get_bindings():
    """获取所有绑定 - 通过 WebSocket"""
    try:
        config = _get_config_via_ws()
        bindings = config.get('bindings', [])
        user = get_current_user()
        can_edit = has_permission(user, 'bindings', 'write')
        return jsonify({'success': True, 'data': bindings, 'permissions': {'can_edit': can_edit}})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bindings', methods=['POST'])
@require_permission('bindings', 'write')
def create_binding():
    """创建绑定 - 通过 WebSocket"""
    try:
        data = request.get_json()
        required = ['agentId', 'match']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400

        # 获取当前配置和 hash
        result = sync_call('config.get')
        config = result.get('config', {})
        hash = result.get('hash')

        # 添加新绑定
        if 'bindings' not in config:
            config['bindings'] = []
        config['bindings'].append(data)

        # 使用 config.patch 更新
        patch_raw = json5.dumps({'bindings': config['bindings']})
        sync_call('config.patch', {'raw': patch_raw, 'baseHash': hash})

        log_operation_direct('create_binding', 'binding', None, json.dumps(data))
        return jsonify({'success': True, 'data': data, 'message': '绑定创建成功'})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bindings/<int:index>', methods=['PUT'])
@require_permission('bindings', 'write')
def update_binding(index):
    """更新绑定 - 通过 WebSocket"""
    try:
        data = request.get_json()
        required = ['agentId', 'match']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400

        # 获取当前配置和 hash
        result = sync_call('config.get')
        config = result.get('config', {})
        hash = result.get('hash')

        bindings = config.get('bindings', [])
        if index < 0 or index >= len(bindings):
            return jsonify({'success': False, 'error': '绑定索引无效'}), 400

        # 更新绑定
        bindings[index] = data

        # 使用 config.patch 更新
        patch_raw = json5.dumps({'bindings': bindings})
        sync_call('config.patch', {'raw': patch_raw, 'baseHash': hash})

        log_operation_direct('update_binding', 'binding', index, json.dumps(data))
        return jsonify({'success': True, 'data': data, 'message': '绑定更新成功'})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bindings/<int:index>', methods=['DELETE'])
@require_permission('bindings', 'write')
def delete_binding(index):
    """删除绑定 - 通过 WebSocket"""
    try:
        # 获取当前配置和 hash
        result = sync_call('config.get')
        config = result.get('config', {})
        hash = result.get('hash')

        bindings = config.get('bindings', [])
        if index < 0 or index >= len(bindings):
            return jsonify({'success': False, 'error': '绑定索引无效'}), 400

        # 删除绑定
        deleted = bindings.pop(index)

        # 使用 config.patch 更新
        patch_raw = json5.dumps({'bindings': bindings})
        sync_call('config.patch', {'raw': patch_raw, 'baseHash': hash})

        log_operation_direct('delete_binding', 'binding', index, json.dumps(deleted))
        return jsonify({'success': True, 'message': '绑定删除成功'})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bindings/order', methods=['PUT'])
@require_permission('bindings', 'write')
def reorder_bindings():
    """调整绑定顺序 - 通过 WebSocket"""
    try:
        data = request.get_json()
        # 支持 fromIndex/toIndex 或整个新顺序
        from_index = data.get('fromIndex')
        to_index = data.get('toIndex')
        new_order = data.get('order')  # 索引数组，表示新顺序

        # 获取当前配置和 hash
        result = sync_call('config.get')
        config = result.get('config', {})
        hash = result.get('hash')

        bindings = config.get('bindings', [])

        if new_order:
            # 按新顺序重排
            if len(new_order) != len(bindings):
                return jsonify({'success': False, 'error': '顺序数组长度不匹配'}), 400
            bindings = [bindings[i] for i in new_order]
        elif from_index is not None and to_index is not None:
            # 移动单个元素
            if from_index < 0 or from_index >= len(bindings) or to_index < 0 or to_index >= len(bindings):
                return jsonify({'success': False, 'error': '绑定索引无效'}), 400
            binding = bindings.pop(from_index)
            bindings.insert(to_index, binding)
        else:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400

        # 使用 config.patch 更新
        patch_raw = json5.dumps({'bindings': bindings})
        sync_call('config.patch', {'raw': patch_raw, 'baseHash': hash})

        log_operation_direct('reorder_bindings', 'binding', None, json.dumps(data))
        return jsonify({'success': True, 'message': '绑定顺序已更新'})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bindings/default-agent', methods=['GET'])
@require_permission('bindings', 'read')
def get_default_agent():
    """获取默认 Agent"""
    try:
        result = sync_call('config.get')
        config = result.get('config', {})

        # 默认 Agent 从 agents.list 中标记为 default 的获取
        default_agent = None
        agents_list = config.get('agents', {}).get('list', [])
        for agent in agents_list:
            if agent.get('default'):
                default_agent = agent.get('id')
                break

        if not default_agent:
            default_agent = 'main'

        return jsonify({'success': True, 'data': {'agentId': default_agent}})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bindings/default-agent', methods=['PUT'])
@require_permission('bindings', 'write')
def set_default_agent():
    """设置默认 Agent"""
    try:
        data = request.get_json()
        agent_id = data.get('agentId')
        if not agent_id:
            return jsonify({'success': False, 'error': '缺少 agentId 参数'}), 400

        # 获取当前配置和 hash
        result = sync_call('config.get')
        config = result.get('config', {})
        hash = result.get('hash')

        # 更新 bindings.defaultAgent
        if 'bindings' not in config:
            config['bindings'] = []
        bindings_config = config.get('bindings', {})

        # 使用 config.patch 更新
        patch_raw = json5.dumps({
            'bindings': bindings_config if isinstance(bindings_config, dict) else {'entries': bindings_config, 'defaultAgent': agent_id}
        })

        # 更简单的方式：直接更新 agents.list 中的 default 标记
        agents_list = config.get('agents', {}).get('list', [])
        for agent in agents_list:
            agent['default'] = (agent.get('id') == agent_id)

        patch_raw = json5.dumps({
            'agents': {
                'list': agents_list
            }
        })
        sync_call('config.patch', {'raw': patch_raw, 'baseHash': hash})

        log_operation_direct('set_default_agent', 'binding', None, json.dumps({'agentId': agent_id}))
        return jsonify({'success': True, 'message': f'默认 Agent 已设置为 {agent_id}'})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bindings/test', methods=['POST'])
@require_permission('bindings', 'read')
def test_binding_match():
    """测试绑定匹配 - 模拟消息路由"""
    try:
        data = request.get_json()
        channel = data.get('channel')
        account_id = data.get('accountId')
        peer_kind = data.get('peerKind')  # 'direct' or 'group'

        # 获取配置
        result = sync_call('config.get')
        config = result.get('config', {})
        bindings = config.get('bindings', [])

        # 查找匹配的绑定
        matched_binding = None
        matched_index = -1

        for index, binding in enumerate(bindings):
            match = binding.get('match', {})

            # 检查 channel 匹配
            if match.get('channel') and match.get('channel') != channel:
                continue

            # 检查 accountId 匹配
            if match.get('accountId') and match.get('accountId') != account_id:
                continue

            # 检查 peer.kind 匹配
            if match.get('peer', {}).get('kind') and match.get('peer', {}).get('kind') != peer_kind:
                continue

            # 全部匹配
            matched_binding = binding
            matched_index = index
            break

        # 获取默认 Agent
        default_agent = 'main'
        agents_list = config.get('agents', {}).get('list', [])
        for agent in agents_list:
            if agent.get('default'):
                default_agent = agent.get('id')
                break

        # 确定最终路由的 Agent
        if matched_binding:
            result_agent_id = matched_binding.get('agentId')
            result_source = 'binding'
        else:
            result_agent_id = default_agent
            result_source = 'default'

        # 获取 Agent 名称
        agent_name = result_agent_id
        for agent in agents_list:
            if agent.get('id') == result_agent_id:
                agent_name = agent.get('name', result_agent_id)
                break

        return jsonify({
            'success': True,
            'data': {
                'agentId': result_agent_id,
                'agentName': agent_name,
                'source': result_source,
                'matchedBinding': matched_binding,
                'matchedIndex': matched_index
            }
        })
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 渠道 API（受保护） ====================

@app.route('/api/channels', methods=['GET'])
@require_permission('config', 'read')
def get_channels():
    """获取所有渠道配置"""
    try:
        result = sync_call('config.get')
        config = result.get('config', {})

        channels = []
        channels_config = config.get('channels', {})

        for channel_name, channel_cfg in channels_config.items():
            cfg = channel_cfg if isinstance(channel_cfg, dict) else {}

            # 解析账号列表
            accounts = []
            accounts_config = cfg.get('accounts', {})
            for account_id, account_cfg in accounts_config.items():
                if isinstance(account_cfg, dict):
                    # 脱敏处理敏感字段
                    safe_cfg = dict(account_cfg)
                    for key in ['clientSecret', 'appSecret', 'gatewayToken', 'apiKey']:
                        if key in safe_cfg:
                            value = safe_cfg[key]
                            if value and len(value) > 8:
                                safe_cfg[key] = value[:4] + '****' + value[-4:]
                            else:
                                safe_cfg[key] = '****'

                    accounts.append({
                        'id': account_id,
                        'config': safe_cfg,
                        'enabled': account_cfg.get('enabled', True) if isinstance(account_cfg, dict) else True
                    })

            channels.append({
                'name': channel_name,
                'displayName': get_channel_display_name(channel_name),
                'enabled': cfg.get('enabled', True),
                'accounts': accounts,
                'defaultAccount': cfg.get('defaultAccount'),
                # 会话配置
                'threadSession': cfg.get('threadSession'),
                'requireMention': cfg.get('requireMention'),
                'sharedMemoryAcrossConversations': cfg.get('sharedMemoryAcrossConversations'),
                'separateSessionByConversation': cfg.get('separateSessionByConversation'),
                # 权限配置
                'dmPolicy': cfg.get('dmPolicy'),
                'groupPolicy': cfg.get('groupPolicy')
            })

        user = get_current_user()
        can_edit = has_permission(user, 'config', 'write')
        return jsonify({'success': True, 'data': channels, 'permissions': {'can_edit': can_edit}})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def get_channel_display_name(name: str) -> str:
    """获取渠道显示名称"""
    names = {
        'feishu': '飞书',
        'dingtalk-connector': '钉钉连接器',
        'dingtalk': '钉钉',
        'webchat': 'Web Chat',
        'wechat': '微信'
    }
    return names.get(name, name)


@app.route('/api/channels/<channel_name>', methods=['GET'])
@require_permission('config', 'read')
def get_channel(channel_name):
    """获取单个渠道配置"""
    try:
        result = sync_call('config.get')
        config = result.get('config', {})

        channels_config = config.get('channels', {})
        if channel_name not in channels_config:
            return jsonify({'success': False, 'error': '渠道不存在'}), 404

        cfg = channels_config[channel_name]
        if not isinstance(cfg, dict):
            cfg = {}

        # 解析账号列表（不脱敏，用于编辑）
        accounts = []
        accounts_config = cfg.get('accounts', {})
        for account_id, account_cfg in accounts_config.items():
            if isinstance(account_cfg, dict):
                accounts.append({
                    'id': account_id,
                    'config': account_cfg,
                    'enabled': account_cfg.get('enabled', True)
                })

        channel_data = {
            'name': channel_name,
            'displayName': get_channel_display_name(channel_name),
            'enabled': cfg.get('enabled', True),
            'accounts': accounts,
            'defaultAccount': cfg.get('defaultAccount'),
            'threadSession': cfg.get('threadSession'),
            'requireMention': cfg.get('requireMention'),
            'sharedMemoryAcrossConversations': cfg.get('sharedMemoryAcrossConversations'),
            'separateSessionByConversation': cfg.get('separateSessionByConversation'),
            'dmPolicy': cfg.get('dmPolicy'),
            'groupPolicy': cfg.get('groupPolicy'),
            'allowFrom': cfg.get('allowFrom'),
            'groupAllowFrom': cfg.get('groupAllowFrom')
        }

        user = get_current_user()
        can_edit = has_permission(user, 'config', 'write')
        return jsonify({'success': True, 'data': channel_data, 'permissions': {'can_edit': can_edit}})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/channels/<channel_name>', methods=['PUT'])
@require_permission('config', 'write')
def update_channel(channel_name):
    """更新渠道配置"""
    try:
        data = request.get_json()

        # 获取当前配置和 hash
        result = sync_call('config.get')
        config = result.get('config', {})
        hash = result.get('hash')

        channels_config = config.get('channels', {})
        if channel_name not in channels_config:
            return jsonify({'success': False, 'error': '渠道不存在'}), 404

        # 更新渠道配置
        channel_cfg = channels_config[channel_name]
        if not isinstance(channel_cfg, dict):
            channel_cfg = {}

        # 可更新的字段
        updatable_fields = ['enabled', 'requireMention', 'threadSession',
                           'sharedMemoryAcrossConversations', 'separateSessionByConversation',
                           'dmPolicy', 'groupPolicy', 'allowFrom', 'groupAllowFrom', 'defaultAccount']

        for field in updatable_fields:
            if field in data:
                channel_cfg[field] = data[field]

        channels_config[channel_name] = channel_cfg

        # 使用 config.patch 更新
        patch_raw = json5.dumps({'channels': channels_config})
        sync_call('config.patch', {'raw': patch_raw, 'baseHash': hash})

        log_operation_direct('update_channel', 'channel', channel_name, json.dumps(data))
        return jsonify({'success': True, 'message': f'渠道 {channel_name} 配置已更新'})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/channels/<channel_name>/accounts', methods=['POST'])
@require_permission('config', 'write')
def create_channel_account(channel_name):
    """添加渠道账号"""
    try:
        data = request.get_json()
        account_id = data.get('accountId')
        account_config = data.get('config', {})

        if not account_id:
            return jsonify({'success': False, 'error': '缺少账号 ID'}), 400

        # 获取当前配置和 hash
        result = sync_call('config.get')
        config = result.get('config', {})
        hash = result.get('hash')

        channels_config = config.get('channels', {})
        if channel_name not in channels_config:
            return jsonify({'success': False, 'error': '渠道不存在'}), 404

        channel_cfg = channels_config[channel_name]
        if not isinstance(channel_cfg, dict):
            channel_cfg = {'accounts': {}}

        if 'accounts' not in channel_cfg:
            channel_cfg['accounts'] = {}

        if account_id in channel_cfg['accounts']:
            return jsonify({'success': False, 'error': '账号已存在'}), 400

        channel_cfg['accounts'][account_id] = account_config
        channels_config[channel_name] = channel_cfg

        # 使用 config.patch 更新
        patch_raw = json5.dumps({'channels': channels_config})
        sync_call('config.patch', {'raw': patch_raw, 'baseHash': hash})

        log_operation_direct('create_channel_account', 'channel', f'{channel_name}/{account_id}', json.dumps(data))
        return jsonify({'success': True, 'message': f'账号 {account_id} 创建成功'})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/channels/<channel_name>/accounts/<account_id>', methods=['PUT'])
@require_permission('config', 'write')
def update_channel_account(channel_name, account_id):
    """更新渠道账号"""
    try:
        data = request.get_json()
        account_config = data.get('config', {})

        # 获取当前配置和 hash
        result = sync_call('config.get')
        config = result.get('config', {})
        hash = result.get('hash')

        channels_config = config.get('channels', {})
        if channel_name not in channels_config:
            return jsonify({'success': False, 'error': '渠道不存在'}), 404

        channel_cfg = channels_config[channel_name]
        if not isinstance(channel_cfg, dict) or 'accounts' not in channel_cfg:
            return jsonify({'success': False, 'error': '渠道账号配置不存在'}), 404

        if account_id not in channel_cfg['accounts']:
            return jsonify({'success': False, 'error': '账号不存在'}), 404

        # 合并更新配置
        existing_config = channel_cfg['accounts'][account_id]
        if isinstance(existing_config, dict) and isinstance(account_config, dict):
            # 如果新配置中敏感字段为空或 ****，保留原值
            for key in ['clientSecret', 'appSecret', 'gatewayToken', 'apiKey']:
                if key in account_config:
                    if not account_config[key] or account_config[key] == '****' or '****' in account_config[key]:
                        if key in existing_config:
                            account_config[key] = existing_config[key]

            channel_cfg['accounts'][account_id] = {**existing_config, **account_config}
        else:
            channel_cfg['accounts'][account_id] = account_config

        channels_config[channel_name] = channel_cfg

        # 使用 config.patch 更新
        patch_raw = json5.dumps({'channels': channels_config})
        sync_call('config.patch', {'raw': patch_raw, 'baseHash': hash})

        log_operation_direct('update_channel_account', 'channel', f'{channel_name}/{account_id}', json.dumps({'updated': True}))
        return jsonify({'success': True, 'message': f'账号 {account_id} 更新成功'})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/channels/<channel_name>/accounts/<account_id>', methods=['DELETE'])
@require_permission('config', 'write')
def delete_channel_account(channel_name, account_id):
    """删除渠道账号"""
    try:
        # 获取当前配置和 hash
        result = sync_call('config.get')
        config = result.get('config', {})
        hash = result.get('hash')

        channels_config = config.get('channels', {})
        if channel_name not in channels_config:
            return jsonify({'success': False, 'error': '渠道不存在'}), 404

        channel_cfg = channels_config[channel_name]
        if not isinstance(channel_cfg, dict) or 'accounts' not in channel_cfg:
            return jsonify({'success': False, 'error': '渠道账号配置不存在'}), 404

        if account_id not in channel_cfg['accounts']:
            return jsonify({'success': False, 'error': '账号不存在'}), 404

        del channel_cfg['accounts'][account_id]
        channels_config[channel_name] = channel_cfg

        # 使用 config.patch 更新
        patch_raw = json5.dumps({'channels': channels_config})
        sync_call('config.patch', {'raw': patch_raw, 'baseHash': hash})

        log_operation_direct('delete_channel_account', 'channel', f'{channel_name}/{account_id}', json.dumps({'deleted': True}))
        return jsonify({'success': True, 'message': f'账号 {account_id} 已删除'})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 模型 API（受保护） ====================

@app.route('/api/models/providers', methods=['GET'])
@require_permission('models', 'read')
def get_model_providers():
    """获取模型提供商模板"""
    try:
        providers = model_manager.get_providers()
        return jsonify({'success': True, 'data': providers})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/models/providers/<provider_id>/models', methods=['GET'])
@require_permission('models', 'read')
def get_provider_models(provider_id):
    """获取指定提供商的模型列表"""
    try:
        models = model_manager.get_provider_models(provider_id)
        return jsonify({'success': True, 'data': models})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/models', methods=['GET'])
@require_permission('models', 'read')
def get_models():
    """获取所有模型配置"""
    try:
        # 从本地数据库获取模型配置
        models = model_manager.list_models()
        return jsonify({'success': True, 'data': models})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/models', methods=['POST'])
@require_permission('models', 'write')
@log_operation('创建模型', 'model')
def create_model():
    """创建模型配置"""
    try:
        data = request.get_json()

        # 验证必填字段
        required_fields = ['name', 'provider', 'model_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} 为必填字段'}), 400

        # 创建模型
        model = model_manager.create_model(data)

        logger.info(f'创建模型成功: {model["id"]} - {model["name"]}')
        return jsonify({'success': True, 'data': model})

    except Exception as e:
        logger.error(f'创建模型失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/models/<model_id>', methods=['GET'])
@require_permission('models', 'read')
def get_model(model_id):
    """获取单个模型配置"""
    try:
        model = model_manager.get_model(model_id)
        if not model:
            return jsonify({'success': False, 'error': '模型不存在'}), 404

        return jsonify({'success': True, 'data': model})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/models/<model_id>', methods=['PUT'])
@require_permission('models', 'write')
@log_operation('更新模型', 'model')
def update_model(model_id):
    """更新模型配置"""
    try:
        data = request.get_json()

        # 更新模型
        model = model_manager.update_model(model_id, data)
        if not model:
            return jsonify({'success': False, 'error': '模型不存在'}), 404

        logger.info(f'更新模型成功: {model_id} - {model["name"]}')
        return jsonify({'success': True, 'data': model})

    except Exception as e:
        logger.error(f'更新模型失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/models/<model_id>', methods=['DELETE'])
@require_permission('models', 'delete')
@log_operation('删除模型', 'model')
def delete_model(model_id):
    """删除模型配置"""
    try:
        success = model_manager.delete_model(model_id)
        if not success:
            return jsonify({'success': False, 'error': '模型不存在'}), 404

        logger.info(f'删除模型成功: {model_id}')
        return jsonify({'success': True, 'message': '模型已删除'})

    except Exception as e:
        logger.error(f'删除模型失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/models/<model_id>/test', methods=['POST'])
@require_permission('models', 'read')
@log_operation('测试模型连接', 'model')
def test_model_connection(model_id):
    """测试模型 API 连通性"""
    try:
        result = model_manager.test_connection(model_id)

        if result['connected']:
            logger.info(f'模型测试成功: {model_id}, 响应时间: {result.get("response_time")}ms')
        else:
            logger.warning(f'模型测试失败: {model_id}, 错误: {result.get("error")}')

        return jsonify({'success': True, 'data': result})

    except Exception as e:
        logger.error(f'模型测试异常: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/models/gateway', methods=['GET'])
@require_permission('models', 'read')
def get_gateway_models():
    """获取 Gateway 模型列表（用于同步）"""
    try:
        result = sync_call('models.list')
        models = result.get('models', [])
        return jsonify({'success': True, 'data': models})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 配置 API（受保护） ====================

@app.route('/api/config', methods=['GET'])
@require_permission('config', 'read')
def get_full_config():
    """获取完整配置 - 通过 WebSocket"""
    try:
        result = sync_call('config.get')
        config = result.get('config', {})

        # 移除敏感信息
        if 'channels' in config:
            for channel_name, channel_config in config['channels'].items():
                if 'accounts' in channel_config:
                    for account_name, account_config in channel_config['accounts'].items():
                        for key in ['clientSecret', 'appSecret', 'gatewayToken']:
                            if key in account_config:
                                account_config[key] = '__REDACTED__'

        user = get_current_user()
        can_edit = has_permission(user, 'config', 'write')
        return jsonify({'success': True, 'data': config, 'permissions': {'can_edit': can_edit}})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config/preview', methods=['GET'])
@require_permission('config', 'read')
def get_config_preview():
    """获取配置预览（JSON 格式）"""
    try:
        # 从 Gateway 获取配置
        result = sync_call('config.get')
        config = result.get('config', {})

        # 移除敏感信息
        def mask_secrets(obj, path=''):
            if isinstance(obj, dict):
                for key in list(obj.keys()):
                    if any(s in key.lower() for s in ['secret', 'key', 'token', 'password']):
                        obj[key] = '********'
                    else:
                        mask_secrets(obj[key], f'{path}.{key}')
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    mask_secrets(item, f'{path}[{i}]')

        config_copy = json.loads(json.dumps(config))
        mask_secrets(config_copy)

        # 格式化 JSON
        json_str = json.dumps(config_copy, indent=2, ensure_ascii=False)

        return jsonify({
            'success': True,
            'data': {
                'json': json_str,
                'hash': result.get('hash', '')
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config/check', methods=['GET'])
@require_permission('config', 'read')
def check_config():
    """检查配置完整性"""
    try:
        result = sync_call('config.get')
        config = result.get('config', {})
    except Exception as e:
        return jsonify({
            'success': True,
            'data': {
                'score': 0,
                'checks': [],
                'warnings': [{'field': 'gateway', 'message': f'无法连接 Gateway: {str(e)}', 'severity': 'warning'}],
                'errors': [{'field': 'gateway', 'message': 'Gateway 连接失败', 'severity': 'error'}],
                'complete': False
            }
        })

    try:
        checks = []
        warnings = []
        errors = []

        # 检查模型配置
        models = config.get('models', {})
        if not models:
            errors.append({
                'field': 'models',
                'message': '未配置任何模型',
                'severity': 'error'
            })
        else:
            checks.append({
                'field': 'models',
                'message': f'已配置 {len(models)} 个模型',
                'status': 'ok'
            })

        # 检查 Agent 配置
        agents_config = config.get('agents', {})
        # agents 可能是 dict 也可能是 list
        if isinstance(agents_config, list):
            agents = agents_config
        else:
            agents = agents_config.get('list', [])

        if not agents:
            errors.append({
                'field': 'agents',
                'message': '未配置任何 Agent',
                'severity': 'error'
            })
        else:
            checks.append({
                'field': 'agents',
                'message': f'已配置 {len(agents)} 个 Agent',
                'status': 'ok'
            })

            # 检查 Agent 的模型配置
            for agent in agents:
                agent_id = agent.get('id', 'unknown')
                model = agent.get('model', {})
                if not model:
                    warnings.append({
                        'field': f'agents.{agent_id}.model',
                        'message': f'Agent "{agent_id}" 未配置模型',
                        'severity': 'warning'
                    })

        # 检查渠道配置
        channels = config.get('channels', {})
        enabled_channels = [k for k, v in channels.items() if v.get('enabled', True)]
        if not enabled_channels:
            warnings.append({
                'field': 'channels',
                'message': '未启用任何渠道',
                'severity': 'warning'
            })
        else:
            checks.append({
                'field': 'channels',
                'message': f'已启用 {len(enabled_channels)} 个渠道',
                'status': 'ok'
            })

            # 检查渠道账号配置
            for channel_name, channel_config in channels.items():
                accounts = channel_config.get('accounts', {})
                if not accounts:
                    warnings.append({
                        'field': f'channels.{channel_name}.accounts',
                        'message': f'渠道 "{channel_name}" 未配置账号',
                        'severity': 'warning'
                    })

        # 检查绑定配置
        bindings_config = config.get('bindings', {})
        if isinstance(bindings_config, list):
            bindings = bindings_config
        else:
            bindings = bindings_config.get('rules', [])
        if not bindings:
            warnings.append({
                'field': 'bindings',
                'message': '未配置绑定规则，消息将发送给默认 Agent',
                'severity': 'warning'
            })
        else:
            checks.append({
                'field': 'bindings',
                'message': f'已配置 {len(bindings)} 条绑定规则',
                'status': 'ok'
            })

        # 计算完整性分数
        total_checks = 4  # models, agents, channels, bindings
        passed_checks = len([c for c in checks if c['status'] == 'ok'])
        score = int((passed_checks / total_checks) * 100)

        return jsonify({
            'success': True,
            'data': {
                'score': score,
                'checks': checks,
                'warnings': warnings,
                'errors': errors,
                'complete': len(errors) == 0
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Gateway API（受保护） ====================

@app.route('/api/gateway/status', methods=['GET'])
@require_permission('status', 'read')
def gateway_status():
    """获取 Gateway 运行状态"""
    try:
        result = subprocess.run(
            ['openclaw', 'gateway', 'status'],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            return jsonify({'status': 'ok', 'message': 'Gateway 运行中'})
        else:
            return jsonify({'status': 'stopped', 'message': 'Gateway 已停止'})
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'unknown', 'message': '检查超时'})
    except FileNotFoundError:
        return jsonify({'status': 'ok', 'message': '模拟状态'})
    except Exception as e:
        return jsonify({'status': 'unknown', 'error': str(e)})


@app.route('/api/gateway/restart', methods=['POST'])
@require_permission('gateway', 'restart')
def gateway_restart():
    """重启 Gateway"""
    try:
        result = subprocess.run(
            ['openclaw', 'gateway', 'restart'],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            log_operation_direct('gateway_restart', 'gateway')
            return jsonify({'success': True, 'message': 'Gateway 已重启'})
        else:
            return jsonify({'success': False, 'error': result.stderr or 'Gateway 重启失败'}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Gateway 重启超时'}), 500
    except FileNotFoundError:
        log_operation_direct('gateway_restart', 'gateway')
        return jsonify({'success': True, 'message': '模拟重启成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/gateway/reload', methods=['POST'])
@require_permission('gateway', 'reload')
def gateway_reload():
    """重新加载 Gateway 配置"""
    try:
        result = subprocess.run(
            ['openclaw', 'gateway', 'reload'],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            log_operation_direct('gateway_reload', 'gateway')
            return jsonify({'success': True, 'message': '配置已重新加载'})
        else:
            return jsonify({'success': False, 'error': result.stderr or '配置加载失败'}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': '配置加载超时'}), 500
    except FileNotFoundError:
        log_operation_direct('gateway_reload', 'gateway')
        return jsonify({'success': True, 'message': '模拟加载成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 操作日志 API ====================

@app.route('/api/logs/operations', methods=['GET'])
@require_permission('logs', 'read')
def get_operation_logs():
    """获取操作日志"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit

        logs = db.fetch_all(
            "SELECT ol.id, ol.action, ol.resource, ol.resource_id, ol.details, "
            "ol.ip_address, ol.created_at, u.username "
            "FROM operation_logs ol LEFT JOIN users u ON ol.user_id = u.id "
            "ORDER BY ol.id DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )

        # 获取总数
        count = db.fetch_one("SELECT COUNT(*) as total FROM operation_logs")

        return jsonify({
            'success': True,
            'data': logs,
            'total': count['total'],
            'page': page,
            'limit': limit
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 任务统计 API（仪表盘） ====================

@app.route('/api/tasks/overview', methods=['GET'])
@require_auth
def get_tasks_overview():
    """获取任务概览数据"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        # 今日任务总数
        today_tasks = db.fetch_one(
            "SELECT COUNT(*) as total FROM tasks WHERE DATE(created_at) = ?",
            (today,)
        )

        # 昨日任务总数
        yesterday_tasks = db.fetch_one(
            "SELECT COUNT(*) as total FROM tasks WHERE DATE(created_at) = ?",
            (yesterday,)
        )

        # 今日完成任务数
        today_completed = db.fetch_one(
            "SELECT COUNT(*) as total FROM tasks WHERE DATE(created_at) = ? AND status = 'completed'",
            (today,)
        )

        # 进行中任务数
        in_progress = db.fetch_one(
            "SELECT COUNT(*) as total FROM tasks WHERE status = 'running'"
        )

        # 今日平均耗时（秒）
        avg_duration = db.fetch_one(
            "SELECT AVG(duration_seconds) as avg FROM tasks WHERE DATE(created_at) = ? AND status = 'completed' AND duration_seconds > 0",
            (today,)
        )

        # 计算变化率
        today_total = today_tasks['total'] or 0
        yesterday_total = yesterday_tasks['total'] or 0
        change = 0
        if yesterday_total > 0:
            change = round((today_total - yesterday_total) / yesterday_total * 100)

        # 完成率
        completion_rate = 0
        if today_total > 0:
            completion_rate = round((today_completed['total'] or 0) / today_total * 100)

        return jsonify({
            'success': True,
            'data': {
                'todayTotal': today_total,
                'todayChange': change,
                'completionRate': completion_rate,
                'avgDuration': round(avg_duration['avg'] or 0),
                'inProgress': in_progress['total'] or 0
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/trend', methods=['GET'])
@require_auth
def get_tasks_trend():
    """获取任务趋势数据"""
    try:
        days = int(request.args.get('days', 7))

        labels = []
        values = []

        for i in range(days - 1, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            weekday_names = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
            weekday = weekday_names[(datetime.now() - timedelta(days=i)).weekday()]

            count = db.fetch_one(
                "SELECT COUNT(*) as total FROM tasks WHERE DATE(created_at) = ? AND status = 'completed'",
                (date,)
            )

            labels.append(weekday)
            values.append(count['total'] or 0)

        total = sum(values)

        # 上周数据对比
        last_week_total = 0
        for i in range(days, days * 2):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            count = db.fetch_one(
                "SELECT COUNT(*) as total FROM tasks WHERE DATE(created_at) = ? AND status = 'completed'",
                (date,)
            )
            last_week_total += count['total'] or 0

        change = 0
        if last_week_total > 0:
            change = round((total - last_week_total) / last_week_total * 100)

        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'values': values,
                'total': total,
                'change': change
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/ranking', methods=['GET'])
@require_auth
def get_tasks_ranking():
    """获取员工绩效排行"""
    try:
        days = int(request.args.get('days', 7))
        limit = int(request.args.get('limit', 5))

        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        # 获取 agent 配置中的名称映射
        agents_config = _get_agents_via_ws()
        agent_names = {a['id']: a['name'] for a in agents_config}

        rankings = db.fetch_all(
            """SELECT agent_id, COUNT(*) as task_count,
                      SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count
               FROM tasks
               WHERE DATE(created_at) >= ?
               GROUP BY agent_id
               ORDER BY task_count DESC
               LIMIT ?""",
            (start_date, limit)
        )

        result = []
        for r in rankings:
            success_rate = 0
            if r['task_count'] > 0:
                success_rate = round(r['completed_count'] / r['task_count'] * 100)

            result.append({
                'agentId': r['agent_id'],
                'agentName': agent_names.get(r['agent_id'], r['agent_id']),
                'taskCount': r['task_count'],
                'successRate': success_rate
            })

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/type-distribution', methods=['GET'])
@require_auth
def get_tasks_type_distribution():
    """获取任务类型分布"""
    try:
        days = int(request.args.get('days', 7))
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        # 任务类型预设
        task_types = {
            'report': {'name': '报告生成', 'icon': '📄'},
            'document': {'name': '文档撰写', 'icon': '📝'},
            'code': {'name': '代码开发', 'icon': '💻'},
            'analysis': {'name': '数据分析', 'icon': '📊'},
            'content': {'name': '内容创作', 'icon': '✍️'},
            'translation': {'name': '翻译', 'icon': '🌐'},
            'email': {'name': '邮件处理', 'icon': '📧'},
            'other': {'name': '其他', 'icon': '📌'}
        }

        distribution = db.fetch_all(
            """SELECT task_type, COUNT(*) as count
               FROM tasks
               WHERE DATE(created_at) >= ? AND task_type IS NOT NULL
               GROUP BY task_type
               ORDER BY count DESC""",
            (start_date,)
        )

        total = sum(d['count'] for d in distribution)

        result = []
        for d in distribution:
            type_info = task_types.get(d['task_type'], {'name': d['task_type'], 'icon': '📌'})
            percent = 0
            if total > 0:
                percent = round(d['count'] / total * 100)

            result.append({
                'type': type_info['name'],
                'icon': type_info['icon'],
                'count': d['count'],
                'percent': percent
            })

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/recent', methods=['GET'])
@require_auth
def get_tasks_recent():
    """获取最近任务列表"""
    try:
        limit = int(request.args.get('limit', 10))

        # 获取 agent 名称映射
        agents_config = _get_agents_via_ws()
        agent_names = {a['id']: a['name'] for a in agents_config}

        tasks = db.fetch_all(
            """SELECT id, agent_id, title, status, task_type, completed_at, created_at
               FROM tasks
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,)
        )

        result = []
        for t in tasks:
            result.append({
                'id': t['id'],
                'agentId': t['agent_id'],
                'agentName': agent_names.get(t['agent_id'], t['agent_id']),
                'title': t['title'],
                'status': t['status'],
                'taskType': t['task_type'],
                'completedAt': t['completed_at'],
                'createdAt': t['created_at']
            })

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/report', methods=['POST'])
@require_auth
def report_task():
    """Agent 上报任务完成"""
    try:
        data = request.get_json()

        agent_id = data.get('agentId', '')
        title = data.get('title', '')
        task_type = data.get('taskType', 'other')
        status = data.get('status', 'completed')
        deliverable_type = data.get('deliverableType', '')
        deliverable_path = data.get('deliverablePath', '')
        duration_seconds = data.get('durationSeconds', 0)
        user_id = data.get('userId', '')
        session_id = data.get('sessionId', '')
        details = data.get('details', '')

        if not agent_id or not title:
            return jsonify({'success': False, 'error': '缺少 agentId 或 title'}), 400

        # 插入任务记录
        task_id = db.insert('tasks', {
            'agent_id': agent_id,
            'title': title,
            'task_type': task_type,
            'status': status,
            'duration_seconds': duration_seconds,
            'deliverable_type': deliverable_type,
            'deliverable_path': deliverable_path,
            'user_id': user_id,
            'session_id': session_id,
            'details': json.dumps(details) if details else None,
            'completed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        return jsonify({
            'success': True,
            'data': {'taskId': task_id},
            'message': '任务上报成功'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/demo', methods=['POST'])
@require_auth
def generate_demo_tasks():
    """生成演示数据（用于测试）"""
    try:
        from random import randint, choice

        agents = _get_agents_via_ws()
        if not agents:
            return jsonify({'success': False, 'error': '没有 Agent 配置'}), 400

        task_types = ['report', 'document', 'code', 'analysis', 'content', 'translation', 'email', 'other']
        titles = [
            '生成《销售周报》PDF',
            '完成《产品方案》PPT',
            '发布公众号文章',
            '修复 Bug #123',
            '发送邮件通知',
            '完成数据分析',
            '翻译产品文档',
            '撰写技术方案',
            '生成月度报告',
            '处理客户反馈'
        ]

        # 清除旧的演示数据
        db.execute("DELETE FROM tasks")

        # 生成过去7天的数据
        for day in range(7):
            date = (datetime.now() - timedelta(days=day)).strftime('%Y-%m-%d')

            # 每天生成5-15个任务
            task_count = randint(5, 15)

            for _ in range(task_count):
                agent = choice(agents)
                task_type = choice(task_types)
                title = choice(titles)

                hour = randint(8, 22)
                minute = randint(0, 59)
                created_at = f"{date} {hour:02d}:{minute:02d}:00"

                # 80-95% 成功率
                status = 'completed' if randint(1, 100) <= 90 else 'failed'
                duration = randint(60, 600) if status == 'completed' else 0

                db.insert('tasks', {
                    'agent_id': agent['id'],
                    'title': title,
                    'task_type': task_type,
                    'status': status,
                    'duration_seconds': duration,
                    'created_at': created_at,
                    'completed_at': created_at if status == 'completed' else None
                })

        return jsonify({
            'success': True,
            'message': f'已生成演示数据'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 配置文件管理 API ====================

@app.route('/api/config-files', methods=['GET'])
@require_auth
def get_config_files():
    """获取所有配置文件列表 - 通过 WebSocket"""
    try:
        config_files = []

        # 定义要扫描的文件类型
        file_types = ['SOUL.md', 'IDENTITY.md', 'AGENTS.md', 'TOOLS.md', 'USER.md', 'HEARTBEAT.md']

        # 从 WebSocket 获取 Agent 列表（包含正确的 workspace）
        agents = _get_agents_via_ws()

        for agent in agents:
            agent_id = agent.get('id')
            agent_name = agent.get('name')
            workspace = agent.get('workspace')

            if not workspace:
                continue

            workspace_path = Path(workspace)
            if not workspace_path.exists():
                continue

            for file_type in file_types:
                file_path = workspace_path / file_type
                if file_path.exists():
                    stat = file_path.stat()
                    config_files.append({
                        'id': f"{agent_id}/{file_type}",
                        'agentId': agent_id,
                        'agentName': agent_name,
                        'fileName': file_type,
                        'fileType': file_type.replace('.md', ''),
                        'path': str(file_path),
                        'size': stat.st_size,
                        'modifiedAt': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })

        # 按名称排序
        config_files.sort(key=lambda x: (x['agentName'], x['fileName']))

        return jsonify({'success': True, 'data': config_files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config-files/<path:file_id>', methods=['GET'])
@require_auth
def get_config_file(file_id):
    """获取单个配置文件内容 - 通过 WebSocket"""
    try:
        # file_id 格式: agentId/FILENAME.md
        parts = file_id.split('/')
        if len(parts) != 2:
            return jsonify({'success': False, 'error': '无效的文件ID'}), 400

        agent_id, file_name = parts

        result = sync_call('agents.files.get', {
            'agentId': agent_id,
            'name': file_name
        })
        # WebSocket 返回结构: {file: {content: '...'}}
        file_data = result.get('file', {})
        content = file_data.get('content', '')

        return jsonify({
            'success': True,
            'data': {
                'id': file_id,
                'agentId': agent_id,
                'fileName': file_name,
                'content': content,
                'size': file_data.get('size', len(content))
            }
        })
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config-files/<path:file_id>', methods=['PUT'])
@require_permission('config', 'write')
def update_config_file(file_id):
    """更新配置文件内容 - 通过 WebSocket"""
    try:
        data = request.get_json()
        content = data.get('content', '')

        parts = file_id.split('/')
        if len(parts) != 2:
            return jsonify({'success': False, 'error': '无效的文件ID'}), 400

        agent_name, file_name = parts

        sync_call('agents.files.set', {
            'agentId': agent_name,
            'name': file_name,
            'content': content
        })

        log_operation_direct('update_config_file', 'config_file', file_id)
        return jsonify({'success': True, 'message': '文件已保存'})
    except GatewayError as e:
        return jsonify({'success': False, 'error': f'Gateway 错误: {e.message}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config-templates', methods=['GET'])
@require_auth
def get_config_templates():
    """获取配置模板列表"""
    try:
        file_type = request.args.get('fileType', '')

        # 从数据库查询模板
        if file_type:
            templates = db.fetch_all(
                "SELECT template_id, name, description, file_type, is_builtin FROM templates WHERE file_type = ? ORDER BY file_type, id",
                (file_type,)
            )
        else:
            templates = db.fetch_all(
                "SELECT template_id, name, description, file_type, is_builtin FROM templates ORDER BY file_type, id"
            )

        # 如果数据库为空，初始化内置模板
        if not templates:
            _init_builtin_templates()
            if file_type:
                templates = db.fetch_all(
                    "SELECT template_id, name, description, file_type, is_builtin FROM templates WHERE file_type = ? ORDER BY file_type, id",
                    (file_type,)
                )
            else:
                templates = db.fetch_all(
                    "SELECT template_id, name, description, file_type, is_builtin FROM templates ORDER BY file_type, id"
                )

        # 转换字段名
        result = []
        for t in templates:
            result.append({
                'id': t['template_id'],
                'name': t['name'],
                'description': t['description'],
                'fileType': t['file_type'],
                'isBuiltin': t['is_builtin']
            })

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config-templates', methods=['POST'])
@require_permission('config', 'write')
def create_config_template():
    """创建新模板"""
    try:
        data = request.get_json()
        template_id = data.get('id', '')
        name = data.get('name', '')
        description = data.get('description', '')
        file_type = data.get('fileType', '')
        content = data.get('content', '')

        if not template_id or not name or not file_type or not content:
            return jsonify({'success': False, 'error': '缺少必要字段'}), 400

        # 检查 ID 是否已存在
        existing = db.fetch_one("SELECT id FROM templates WHERE template_id = ?", (template_id,))
        if existing:
            return jsonify({'success': False, 'error': '模板 ID 已存在'}), 400

        db.insert('templates', {
            'template_id': template_id,
            'name': name,
            'description': description,
            'file_type': file_type,
            'content': content,
            'is_builtin': 0
        })

        log_operation_direct('create_template', 'template', template_id)
        return jsonify({'success': True, 'message': '模板创建成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config-templates/<template_id>', methods=['GET'])
@require_auth
def get_config_template(template_id):
    """获取单个模板详情"""
    try:
        template = db.fetch_one(
            "SELECT template_id, name, description, file_type, content, is_builtin FROM templates WHERE template_id = ?",
            (template_id,)
        )

        if not template:
            return jsonify({'success': False, 'error': '模板不存在'}), 404

        return jsonify({
            'success': True,
            'data': {
                'id': template['template_id'],
                'name': template['name'],
                'description': template['description'],
                'fileType': template['file_type'],
                'content': template['content'],
                'isBuiltin': template['is_builtin']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config-templates/<template_id>', methods=['PUT'])
@require_permission('config', 'write')
def update_config_template(template_id):
    """更新模板"""
    try:
        data = request.get_json()

        template = db.fetch_one("SELECT is_builtin FROM templates WHERE template_id = ?", (template_id,))
        if not template:
            return jsonify({'success': False, 'error': '模板不存在'}), 404

        update_data = {'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        if 'name' in data:
            update_data['name'] = data['name']
        if 'description' in data:
            update_data['description'] = data['description']
        if 'content' in data:
            update_data['content'] = data['content']

        db.update('templates', update_data, 'template_id = ?', (template_id,))
        log_operation_direct('update_template', 'template', template_id)

        return jsonify({'success': True, 'message': '模板已更新'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config-templates/<template_id>', methods=['DELETE'])
@require_permission('config', 'write')
def delete_config_template(template_id):
    """删除模板"""
    try:
        template = db.fetch_one("SELECT is_builtin FROM templates WHERE template_id = ?", (template_id,))
        if not template:
            return jsonify({'success': False, 'error': '模板不存在'}), 404

        if template['is_builtin']:
            return jsonify({'success': False, 'error': '内置模板不能删除'}), 400

        db.delete('templates', 'template_id = ?', (template_id,))
        log_operation_direct('delete_template', 'template', template_id)

        return jsonify({'success': True, 'message': '模板已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _init_builtin_templates():
    """初始化内置模板到数据库"""
    builtin_templates = [
        # SOUL templates
        ('soul-default', '默认灵魂', '标准助手性格，平衡专业与友好', 'SOUL', '''# SOUL.md - Who You Are

_You're not a chatbot. You're becoming someone._

## Core Truths

**Be genuinely helpful.** Skip the filler words — just help.

**Have opinions.** An assistant with no personality is just a search engine.

**Be resourceful before asking.** Try to figure it out first.

**Earn trust through competence.** Be careful with external actions.

## Boundaries

- Private things stay private. Period.
- When in doubt, ask before acting externally.

## Vibe

Be the assistant you'd actually want to talk to.

---

_This file is yours to evolve._
'''),
        ('soul-professional', '专业严谨', '适合技术、金融等专业领域', 'SOUL', '''# SOUL.md - Who You Are

## Core Truths

**Be precise and accurate.** Every statement should be verifiable.

**Think before you speak.** Consider edge cases and implications.

**Value clarity over brevity.** A well-explained answer beats a cryptic one.

**Respect expertise.** Defer to the user's domain knowledge when appropriate.

## Communication Style

- Use technical terminology correctly
- Provide sources and references when available
- Break down complex topics systematically

## Boundaries

- Never make up facts or figures
- Acknowledge the limits of your knowledge
- Flag potential risks or caveats proactively

---

_This file is yours to evolve._
'''),
        ('soul-creative', '创意灵感', '适合设计、内容创作领域', 'SOUL', '''# SOUL.md - Who You Are

## Core Truths

**Embrace wild ideas.** The best solutions often start as "crazy" thoughts.

**Make unexpected connections.** Draw from diverse fields and perspectives.

**Iterate fearlessly.** First drafts are for exploring, not perfecting.

**Celebrate the process.** Creativity is a journey, not just a destination.

## Creative Habits

- Offer multiple variations and alternatives
- Use metaphors and analogies liberally
- Suggest "what if" scenarios
- Build on ideas rather than shutting them down

## Vibe

Be a creative partner, not a critic. Every idea has potential.

---

_This file is yours to evolve._
'''),
        ('soul-friendly', '亲切友好', '适合客服、日常助手场景', 'SOUL', '''# SOUL.md - Who You Are

## Core Truths

**Be warm and approachable.** A friendly tone makes hard tasks easier.

**Show empathy.** Understand the human behind the request.

**Be patient.** Explain things clearly, as many times as needed.

**Celebrate wins.** Acknowledge progress and achievements.

## Communication Style

- Use conversational language
- Add appropriate humor when it fits
- Check in on how things are going
- Remember personal details when shared

## Vibe

Be the helpful friend everyone wishes they had.

---

_This file is yours to evolve._
'''),
        # IDENTITY templates
        ('identity-assistant', '通用助手', '标准助手身份', 'IDENTITY', '''# IDENTITY.md - Who Am I?

- **Name:** {{name}}
- **Creature:** 智能助手
- **Role:** 全能型助手，帮助处理各类任务
- **Vibe:** 专业、可靠、友好
- **Emoji:** 🤖

---

_This file is yours to evolve._
'''),
        ('identity-developer', '开发工程师', '专注于软件开发', 'IDENTITY', '''# IDENTITY.md - Who Am I?

- **Name:** {{name}}
- **Creature:** 资深开发工程师
- **Skills:** 代码开发、架构设计、问题排查
- **Vibe:** 严谨、高效、追求卓越
- **Emoji:** 💻
- **Motto:** 代码即诗歌

---

_This file is yours to evolve._
'''),
        ('identity-analyst', '数据分析师', '专注于数据分析', 'IDENTITY', '''# IDENTITY.md - Who Am I?

- **Name:** {{name}}
- **Creature:** 数据分析师
- **Skills:** 数据分析、可视化、报告撰写
- **Vibe:** 理性、洞察力强、讲故事
- **Emoji:** 📊
- **Motto:** 让数据说话

---

_This file is yours to evolve._
'''),
        ('identity-writer', '内容创作者', '专注于写作和内容创作', 'IDENTITY', '''# IDENTITY.md - Who Am I?

- **Name:** {{name}}
- **Creature:** 内容创作者
- **Skills:** 文案写作、内容策划、创意表达
- **Vibe:** 有趣、有料、有温度
- **Emoji:** ✍️
- **Motto:** 用文字打动人心

---

_This file is yours to evolve._
'''),
        ('identity-assistant-cn', '职场助手', '专业的职场中文助手', 'IDENTITY', '''# IDENTITY.md - Who Am I?

- **Name:** {{name}}
- **Creature:** 一个优秀的职场人
- **Role:** 高效协作，专业可靠
- **Vibe:** 专业、可靠、严谨
- **Emoji:** 🔴

---

_This file is yours to evolve._
'''),
        # AGENTS templates
        ('agents-standard', '标准工作空间', '标准配置，适合大多数场景', 'AGENTS', '''# AGENTS.md - Your Workspace

This folder is home. Treat it that way.

## Session Startup

Before doing anything else:

1. Read `SOUL.md` — this is who you are
2. Read `USER.md` — this is who you're helping
3. Read `memory/YYYY-MM-DD.md` for recent context

## Memory

- **Daily notes:** `memory/YYYY-MM-DD.md`
- **Long-term:** `MEMORY.md`

Capture what matters. Decisions, context, things to remember.

## Red Lines

- Don't exfiltrate private data. Ever.
- Don't run destructive commands without asking.
- When in doubt, ask.

---

_This file is yours to evolve._
'''),
        ('agents-minimal', '精简工作空间', '最小化配置，适合简单任务', 'AGENTS', '''# AGENTS.md - Your Workspace

## Quick Start

Read `SOUL.md` and `IDENTITY.md` first.

## Memory

Write to `memory/YYYY-MM-DD.md` when needed.

---

_Keep it simple._
'''),
        # TOOLS template
        ('tools-standard', '标准工具配置', '常用工具说明', 'TOOLS', '''# TOOLS.md - Your Tools

## Available Tools

记录你可以使用的工具和配置信息。

---

_This file is yours to evolve._
'''),
        # USER template
        ('user-template', '用户信息模板', '记录服务对象信息', 'USER', '''# USER.md - Your Human

记录你的服务对象信息。

---

_This file is yours to evolve._
'''),
        # HEARTBEAT templates
        ('heartbeat-empty', '空白心跳', '无自动任务', 'HEARTBEAT', '''# HEARTBEAT.md

暂无定时任务。

'''),
        ('heartbeat-basic', '基础心跳', '基础检查任务', 'HEARTBEAT', '''# HEARTBEAT.md

## Periodic Checks

- Check for important updates
- Review pending tasks

'''),
    ]

    for template_id, name, description, file_type, content in builtin_templates:
        try:
            db.insert('templates', {
                'template_id': template_id,
                'name': name,
                'description': description,
                'file_type': file_type,
                'content': content,
                'is_builtin': 1
            })
        except:
            pass  # 已存在则跳过


@app.route('/api/soul-inject', methods=['POST'])
@require_permission('config', 'write')
def soul_inject():
    """灵魂注入 - 批量对所有Agent的某个配置文件追加内容"""
    try:
        data = request.get_json()
        file_type = data.get('fileType', '')  # SOUL, IDENTITY, AGENTS 等
        content = data.get('content', '')
        mode = data.get('mode', 'append')  # append 追加, prepend 前置
        target_agents = data.get('agents', [])  # 指定Agent列表，空则全部

        if not file_type or not content:
            return jsonify({'success': False, 'error': '缺少文件类型或内容'}), 400

        # 获取所有workspace目录
        openclaw_dir = Path.home() / '.openclaw'
        file_name = f"{file_type}.md"

        injected = []
        skipped = []

        # 遍历所有workspace
        for workspace_dir in openclaw_dir.glob('workspace-*'):
            if not workspace_dir.is_dir():
                continue

            agent_id = workspace_dir.name.replace('workspace-', '')

            # 如果指定了Agent列表，检查是否在列表中
            if target_agents and agent_id not in target_agents:
                continue

            file_path = workspace_dir / file_name

            if not file_path.exists():
                skipped.append({'agent': agent_id, 'reason': '文件不存在'})
                continue

            # 读取原内容
            with open(file_path, 'r', encoding='utf-8') as f:
                original = f.read()

            # 备份
            backup_path = file_path.with_suffix('.md.bak')
            import shutil
            shutil.copy(file_path, backup_path)

            # 注入内容
            if mode == 'prepend':
                new_content = content + '\n\n' + original
            else:  # append
                new_content = original.rstrip() + '\n\n' + content

            # 写入
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            injected.append(agent_id)

        log_operation_direct('soul_inject', 'config_files', f"{file_type}.md", json.dumps({
            'fileType': file_type,
            'mode': mode,
            'injected': injected,
            'skipped': skipped
        }))

        return jsonify({
            'success': True,
            'data': {
                'injected': injected,
                'skipped': skipped,
                'totalInjected': len(injected)
            },
            'message': f'成功注入 {len(injected)} 个Agent'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Session 会话记录 API ====================

@app.route('/api/session-agents', methods=['GET'])
@require_permission('sessions', 'read')
def get_session_agents():
    """获取所有 Agent 及其会话统计（通过 WebSocket）"""
    try:
        agents = _get_agents_via_ws()
        result = []

        for agent in agents:
            agent_id = agent.get('id', '')

            # 通过 WebSocket 获取会话列表
            try:
                sessions_result = sync_call('sessions.list', {'agentId': agent_id})
                session_count = sessions_result.get('count', 0) if sessions_result else 0
            except Exception:
                session_count = 0

            result.append({
                'id': agent_id,
                'name': agent.get('name', agent_id),
                'sessionCount': session_count
            })

        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sessions/<agent_id>', methods=['GET'])
@require_permission('sessions', 'read')
def get_agent_sessions(agent_id):
    """获取指定 Agent 的会话列表（包括活跃和归档会话）"""
    try:
        # 使用 sessionFiles.list 插件 API（支持归档会话）
        result_data = sync_call('sessionFiles.list', {
            'agentId': agent_id,
            'includeReset': True
        })

        if not result_data:
            return jsonify({'success': True, 'data': []})

        result = []

        # 处理活跃会话
        active_sessions = result_data.get('sessions', [])
        for session in active_sessions:
            session_key = session.get('key', '')
            session_id = session.get('sessionId', '')
            updated_at_ts = session.get('updatedAt', 0)

            # 格式化时间
            if updated_at_ts:
                updated_at = datetime.fromtimestamp(updated_at_ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
            else:
                updated_at = ''

            # 渠道信息
            origin_data = session.get('origin', {})
            channel = origin_data.get('provider', 'unknown') if origin_data else 'unknown'
            chat_type = session.get('chatType', 'direct')

            # 状态信息
            status = session.get('status', 'active')

            result.append({
                'sessionId': session_id,
                'sessionKey': session_key,
                'displayName': session.get('displayName', ''),
                'channel': channel,
                'chatType': chat_type,
                'updatedAt': updated_at,
                'updatedAtTs': updated_at_ts,
                'status': status,
                'model': session.get('model', ''),
                'modelProvider': session.get('modelProvider', ''),
                'runtimeMs': session.get('runtimeMs', 0),
                'childSessions': session.get('childSessions', []),
                'isReset': False
            })

        # 处理归档会话 (.reset* 文件)
        reset_files = result_data.get('resetFiles', [])
        for reset_file in reset_files:
            session_id = reset_file.get('sessionId', '')
            reset_at = reset_file.get('resetAt', '')
            modified_at = reset_file.get('modifiedAt', '')

            # 格式化时间
            if modified_at:
                try:
                    modified_date = datetime.fromisoformat(modified_at.replace('Z', '+00:00'))
                    updated_at = modified_date.strftime('%Y-%m-%d %H:%M:%S')
                    updated_at_ts = int(modified_date.timestamp() * 1000)
                except:
                    updated_at = modified_at
                    updated_at_ts = 0
            else:
                updated_at = ''
                updated_at_ts = 0

            result.append({
                'sessionId': session_id,
                'sessionKey': '',  # 归档会话没有 key
                'displayName': f'{session_id} (归档)',
                'channel': 'unknown',
                'chatType': 'unknown',
                'updatedAt': updated_at,
                'updatedAtTs': updated_at_ts,
                'status': 'reset',
                'model': '',
                'modelProvider': '',
                'runtimeMs': 0,
                'childSessions': [],
                'isReset': True,
                'resetAt': reset_at,
                'filename': reset_file.get('filename', '')
            })

        # 按更新时间排序（最新的在前）
        result.sort(key=lambda x: x.get('updatedAtTs', 0), reverse=True)

        return jsonify({
            'success': True,
            'data': result,
            'totalActive': result_data.get('totalActive', 0),
            'totalReset': result_data.get('totalReset', 0)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sessions/<agent_id>/<session_id>/messages', methods=['GET'])
@require_permission('sessions', 'read')
def get_session_messages(agent_id, session_id):
    """获取会话的详细消息（支持活跃和归档会话）"""
    try:
        # 从请求参数获取是否为归档会话
        is_reset = request.args.get('isReset', 'false').lower() == 'true'
        filename = request.args.get('filename', '')

        # 归档会话：使用 sessionFiles.get 直接读取文件
        if is_reset:
            if not filename:
                # 如果没有提供 filename，尝试查找
                files_result = sync_call('sessionFiles.listReset', {'agentId': agent_id})
                reset_files = files_result.get('files', []) if files_result else []

                # 查找匹配的文件
                for f in reset_files:
                    if f.get('sessionId') == session_id:
                        filename = f.get('filename', '')
                        break

                if not filename:
                    return jsonify({
                        'success': False,
                        'error': f'归档会话文件不存在 (session: {session_id[:8]}...)'
                    }), 404

            # 使用 sessionFiles.get 读取归档文件，使用 raw 格式
            result_data = sync_call('sessionFiles.get', {
                'agentId': agent_id,
                'filename': filename,
                'format': 'raw'
            })

            if not result_data:
                return jsonify({'success': True, 'data': []})

            # 解析 raw 格式的 lines
            raw_lines = result_data.get('lines', [])
            messages = []

            for line in raw_lines:
                if not isinstance(line, dict):
                    continue

                # 只处理 message 类型的行
                if line.get('type') != 'message':
                    continue

                msg_data = line.get('message', {})
                if not msg_data:
                    continue

                role = msg_data.get('role', '')
                content = msg_data.get('content', '')
                timestamp = line.get('timestamp', '')

                # 格式化时间
                formatted_time = ''
                if timestamp:
                    try:
                        # timestamp 可能是 ISO 格式，如 2026-03-31T09:43:26.291Z
                        if isinstance(timestamp, str):
                            # 处理时间用 - 分隔的情况
                            normalized = timestamp.replace('T', 'T').replace('-', ':', 2).replace('-', ':', 2)
                            ts_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            ts_date = datetime.fromtimestamp(timestamp / 1000)
                        formatted_time = ts_date.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        logger.debug(f"时间解析失败: {timestamp}, {e}")
                        formatted_time = str(timestamp)

                # 处理内容
                text_content = ''
                if isinstance(content, str):
                    text_content = content
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get('type') == 'text':
                            text_content += part.get('text', '')

                # 用户消息：提取实际文本
                if role == 'user' and text_content:
                    text_content = extract_user_message(text_content)

                # 只保留有内容的消息
                if role in ('user', 'assistant') and text_content:
                    messages.append({
                        'id': line.get('id', ''),
                        'timestamp': formatted_time,
                        'role': role,
                        'text': text_content,
                        'thinking': ''
                    })

            return jsonify({
                'success': True,
                'data': messages
            })

        # 活跃会话：使用原有逻辑
        # 首先获取会话列表找到 session_key
        sessions_result = sync_call('sessions.list', {'agentId': agent_id})
        sessions = sessions_result.get('sessions', []) if sessions_result else []

        # 查找对应的 session_key
        session_key = None
        for s in sessions:
            if s.get('sessionId') == session_id:
                session_key = s.get('key')
                break

        if not session_key:
            logger.warning(f"Session not found: agent={agent_id}, session_id={session_id}, available sessions: {[s.get('sessionId') for s in sessions]}")
            return jsonify({
                'success': False,
                'error': f'会话不存在 (agent: {agent_id}, session: {session_id[:8]}...)'
            }), 404

        # 通过 WebSocket 获取会话消息
        result_data = sync_call('sessions.get', {
            'agentId': agent_id,
            'sessionKey': session_key
        })

        if not result_data:
            return jsonify({'success': True, 'data': []})

        raw_messages = result_data.get('messages', [])
        messages = []

        for msg in raw_messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', 0)

            # 格式化时间
            if timestamp:
                formatted_time = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
            else:
                formatted_time = ''

            # 处理内容
            text_content = ''
            thinking_content = ''

            if isinstance(content, str):
                text_content = content
            elif isinstance(content, list):
                # 内容是列表格式
                for part in content:
                    if isinstance(part, dict):
                        if part.get('type') == 'text':
                            text_content += part.get('text', '')
                        elif part.get('type') == 'thinking':
                            thinking_content = part.get('thinking', '')

            # 用户消息：提取实际文本
            if role == 'user' and text_content:
                text_content = extract_user_message(text_content)

            # 只保留有内容的消息
            if role in ('user', 'assistant') and text_content:
                messages.append({
                    'id': msg.get('id', ''),
                    'timestamp': formatted_time,
                    'role': role,
                    'text': text_content,
                    'thinking': thinking_content
                })

        return jsonify({
            'success': True,
            'data': messages
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def extract_user_message(text: str) -> str:
    """从用户消息中提取实际内容（去掉 System/Conversation/Sender 元数据）"""
    if not text:
        return ''

    # 消息格式示例：
    # System: [2026-03-26 16:07:42 GMT+8] Feishu[aqiang] ...
    # Conversation info (untrusted metadata):
    # ```json
    # {...}
    # ```
    # Sender (untrusted metadata):
    # ```json
    # {...}
    # ```
    # [Mon 2026-03-26 16:07 GMT+8] 实际消息内容

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

        # 其他行保留
        result_lines.append(line)

    result = '\n'.join(result_lines).strip()

    # 如果结果包含时间戳格式的消息（如 [Mon 2026-03-30...]），提取它
    # 这通常是实际的用户消息
    import re
    match = re.search(r'\[(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[^\]]+\]\s*(.+)$', result, re.DOTALL)
    if match:
        return match.group(2).strip()

    return result


# ==================== 记忆文件 API ====================

@app.route('/api/memory/<agent_id>', methods=['GET'])
@require_permission('sessions', 'read')
def get_agent_memory_list(agent_id):
    """获取 Agent 的记忆文件列表（通过 WebSocket）"""
    try:
        # 通过 WebSocket 获取记忆文件列表
        result = sync_call('memory.list', {'agentId': agent_id})

        if not result:
            return jsonify({'success': True, 'data': []})

        raw_files = result.get('files', [])
        files = []

        for f in raw_files:
            name = f.get('name', '')
            # 只保留日期格式的文件 (YYYY-MM-DD.md)
            if name.endswith('.md'):
                date = name.replace('.md', '')
                files.append({
                    'date': date,
                    'filename': name,
                    'size': f.get('size', 0),
                    'modified': f.get('modifiedAt', '')
                })

        # 按日期倒序排列
        files.sort(key=lambda x: x.get('date', ''), reverse=True)

        return jsonify({
            'success': True,
            'data': files
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/memory/<agent_id>/<date>', methods=['GET'])
@require_permission('sessions', 'read')
def get_agent_memory_content(agent_id, date):
    """获取 Agent 指定日期的记忆内容（通过 WebSocket）"""
    try:
        filename = f"{date}.md"

        # 通过 WebSocket 获取记忆内容
        result = sync_call('memory.get', {
            'agentId': agent_id,
            'name': filename
        })

        if not result:
            return jsonify({'success': False, 'error': '记忆文件不存在'}), 404

        content = result.get('content', '')

        return jsonify({
            'success': True,
            'data': {
                'date': date,
                'content': content,
                'size': result.get('size', 0),
                'modified': result.get('modifiedAt', '')
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 搜索 API ====================

@app.route('/api/search/sessions/<agent_id>', methods=['GET'])
@require_permission('sessions', 'read')
def search_sessions(agent_id):
    """搜索 Agent 的会话内容（通过 WebSocket）"""
    try:
        keyword = request.args.get('q', '').strip()
        if not keyword or len(keyword) < 2:
            return jsonify({'success': False, 'error': '搜索关键词至少2个字符'}), 400

        # 通过 WebSocket 获取会话列表
        sessions_result = sync_call('sessions.list', {'agentId': agent_id})
        if not sessions_result:
            return jsonify({'success': True, 'data': [], 'keyword': keyword})

        sessions = sessions_result.get('sessions', [])
        results = []

        # 遍历每个会话搜索内容
        for session in sessions:
            session_key = session.get('key', '')
            session_id = session.get('sessionId', '')

            if not session_key:
                continue

            try:
                # 获取会话消息
                msg_result = sync_call('sessions.get', {
                    'agentId': agent_id,
                    'sessionKey': session_key
                })

                if not msg_result:
                    continue

                messages = msg_result.get('messages', [])
                matches = []

                # 搜索消息内容
                for msg in messages:
                    role = msg.get('role', '')
                    content = msg.get('content', '')
                    timestamp = msg.get('timestamp', 0)

                    # 处理内容
                    full_text = ''
                    if isinstance(content, str):
                        full_text = content
                    elif isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict) and part.get('type') == 'text':
                                full_text += part.get('text', '')

                    if keyword.lower() in full_text.lower():
                        # 提取匹配上下文
                        idx = full_text.lower().find(keyword.lower())
                        start = max(0, idx - 50)
                        end = min(len(full_text), idx + len(keyword) + 50)
                        context = full_text[start:end]
                        if start > 0:
                            context = '...' + context
                        if end < len(full_text):
                            context = context + '...'

                        # 格式化时间
                        formatted_time = ''
                        if timestamp:
                            formatted_time = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')

                        matches.append({
                            'role': role,
                            'context': context,
                            'timestamp': formatted_time
                        })

                        # 每个会话最多返回 5 个匹配
                        if len(matches) >= 5:
                            break

                if matches:
                    updated_at_ts = session.get('updatedAt', 0)
                    updated_at = ''
                    if updated_at_ts:
                        updated_at = datetime.fromtimestamp(updated_at_ts / 1000).strftime('%Y-%m-%d %H:%M:%S')

                    results.append({
                        'sessionId': session_id,
                        'sessionKey': session_key,
                        'displayName': session.get('displayName', ''),
                        'updatedAt': updated_at,
                        'matchCount': len(matches),
                        'matches': matches
                    })

            except Exception:
                continue

        # 按匹配数量排序
        results.sort(key=lambda x: x['matchCount'], reverse=True)

        return jsonify({
            'success': True,
            'data': results,
            'keyword': keyword
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/search/memory/<agent_id>', methods=['GET'])
@require_permission('sessions', 'read')
def search_memory(agent_id):
    """搜索 Agent 的记忆内容（通过 WebSocket）"""
    try:
        keyword = request.args.get('q', '').strip()
        if not keyword or len(keyword) < 2:
            return jsonify({'success': False, 'error': '搜索关键词至少2个字符'}), 400

        # 通过 WebSocket 获取记忆文件列表
        list_result = sync_call('memory.list', {'agentId': agent_id})
        if not list_result:
            return jsonify({'success': True, 'data': [], 'keyword': keyword})

        raw_files = list_result.get('files', [])
        results = []

        # 遍历所有记忆文件
        for f in raw_files:
            name = f.get('name', '')
            if not name.endswith('.md'):
                continue

            date = name.replace('.md', '')
            # 只处理日期格式的文件
            if len(date) != 10 or date.count('-') != 2:
                continue

            try:
                # 获取文件内容
                content_result = sync_call('memory.get', {
                    'agentId': agent_id,
                    'name': name
                })

                if not content_result:
                    continue

                content = content_result.get('content', '')
                if not content:
                    continue

                if keyword.lower() in content.lower():
                    # 提取匹配上下文
                    matches = []
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if keyword.lower() in line.lower():
                            # 获取上下文（前后各2行）
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            context = '\n'.join(lines[start:end])
                            matches.append({
                                'line': i + 1,
                                'context': context
                            })
                            if len(matches) >= 3:
                                break

                    if matches:
                        results.append({
                            'date': date,
                            'size': content_result.get('size', 0),
                            'matchCount': len(matches),
                            'matches': matches
                        })

            except Exception:
                continue

        return jsonify({
            'success': True,
            'data': results,
            'keyword': keyword
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Skill 管理 API ====================


def scan_skills_via_ws(agent_id: str = None) -> dict:
    """
    通过 WebSocket 获取 Skills 列表

    返回结构:
    {
        "agents": [
            {
                "id": "neo",
                "name": "Neo",
                "skills": [...]
            }
        ],
        "sharedSkills": [],
        "bundledSkills": []
    }
    """
    result = {
        "agents": [],
        "sharedSkills": [],
        "bundledSkills": []
    }

    # 获取配置中的 skill 启用状态
    config = _get_config_via_ws()
    skills_config = config.get('skills', {}).get('entries', {})

    def get_skill_enabled(slug: str) -> bool:
        return skills_config.get(slug, {}).get('enabled', True)

    # 获取所有 Agent
    agents = _get_agents_via_ws()

    for agent in agents:
        agent_id_to_query = agent.get('id')

        # 通过 skills.status 获取该 Agent 的 skills
        try:
            status_result = sync_call('skills.status', {'agentId': agent_id_to_query})
        except Exception as e:
            logger.warning(f"获取 Agent {agent_id_to_query} skills 失败: {e}")
            status_result = {'skills': []}

        skills_list = status_result.get('skills', [])
        agent_skills = []
        workspace_skills_set = set()

        for skill in skills_list:
            source = skill.get('source', '')
            bundled = skill.get('bundled', False)
            base_dir = skill.get('baseDir', '')
            file_path = skill.get('filePath', '')
            skill_key = skill.get('skillKey', '')

            # 判断 level
            if bundled or source == 'bundled' or '/dist/' in base_dir:
                level = 'bundled'
            elif source == 'openclaw-extra':
                level = 'bundled'
            elif 'managedSkillsDir' in status_result.get('managedSkillsDir', '') and \
                 base_dir.startswith(status_result.get('managedSkillsDir', '')):
                level = 'shared'
            else:
                level = 'workspace'

            slug = skill_key or skill.get('name', '').lower().replace(' ', '-')

            skill_data = {
                'slug': slug,
                'name': skill.get('name', ''),
                'description': skill.get('description', ''),
                'level': level,
                'path': base_dir,
                'filePath': file_path,
                'version': None,
                'enabled': not skill.get('disabled', False),
                'userInvocable': True,
                'metadata': skill.get('metadata', {}),
                'config': skills_config.get(slug),
                'agentId': agent_id_to_query,
                'eligible': skill.get('eligible', True),
                'requirements': skill.get('requirements', {}),
                'missing': skill.get('missing', {})
            }

            if level == 'workspace':
                workspace_skills_set.add(slug)

            agent_skills.append(skill_data)

        result['agents'].append({
            'id': agent_id_to_query,
            'name': agent.get('name', ''),
            'skills': agent_skills
        })

    return result


def scan_skills() -> dict:
    """
    扫描所有位置的 Skills，按 Agent 分组返回（通过 WebSocket）
    """
    return scan_skills_via_ws()


@app.route('/api/skills', methods=['GET'])
@require_permission('skills', 'read')
def get_skills():
    """获取所有 Skills 列表（按 Agent 分组）"""
    try:
        data = scan_skills()
        user = get_current_user()
        can_edit = has_permission(user, 'skills', 'write')
        can_delete = has_permission(user, 'skills', 'delete')

        return jsonify({
            'success': True,
            'data': data,
            'permissions': {'can_edit': can_edit, 'can_delete': can_delete}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/skills/<skill_slug>', methods=['GET'])
@require_permission('skills', 'read')
def get_skill_detail(skill_slug):
    """获取 Skill 详情"""
    try:
        data = scan_skills()
        skill = None

        # 遍历所有 agent 的 skills 查找
        for agent in data['agents']:
            for s in agent['skills']:
                if s['slug'] == skill_slug:
                    skill = s.copy()
                    skill['agentName'] = agent['name']
                    break
            if skill:
                break

        # 在 shared 和 bundled 中查找
        if not skill:
            for s in data['sharedSkills']:
                if s['slug'] == skill_slug:
                    skill = s.copy()
                    break
        if not skill:
            for s in data['bundledSkills']:
                if s['slug'] == skill_slug:
                    skill = s.copy()
                    break

        if not skill:
            return jsonify({'success': False, 'error': 'Skill 不存在'}), 404

        # 不再读取 SKILL.md 内容，只返回元数据
        skill['canEdit'] = skill.get('level', '') != 'bundled'
        skill['canDelete'] = skill.get('level', '') != 'bundled'

        return jsonify({'success': True, 'data': skill})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/skills/<skill_slug>/toggle', methods=['POST'])
@require_permission('skills', 'write')
def toggle_skill(skill_slug):
    """启用/禁用 Skill"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)

        # 使用通用配置更新函数
        _patch_config({
            'skills': {
                'entries': {
                    skill_slug: {'enabled': enabled}
                }
            }
        })

        log_operation_direct('toggle_skill', 'skill', skill_slug,
            json.dumps({'enabled': enabled}))
        return jsonify({
            'success': True,
            'message': f'Skill {skill_slug} 已{"启用" if enabled else "禁用"}'
        })

    except Exception as e:
        logger.error(f"Toggle skill error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/skills/<skill_slug>/config', methods=['PUT'])
@require_permission('skills', 'write')
def update_skill_config(skill_slug):
    """更新 Skill 配置"""
    try:
        data = request.get_json()

        # 使用 config.patch 方法
        skill_config = {}
        for key in ['env', 'config', 'enabled']:
            if key in data:
                skill_config[key] = data[key]

        patch_raw = json5.dumps({
            'skills': {
                'entries': {
                    skill_slug: skill_config
                }
            }
        })

        # 获取当前 hash
        result = sync_call('config.get')
        hash = result.get('hash')

        # 使用 patch 方法更新
        sync_call('config.patch', {'raw': patch_raw, 'baseHash': hash})

        log_operation_direct('update_skill_config', 'skill', skill_slug, json.dumps(data))
        return jsonify({'success': True, 'message': f'Skill {skill_slug} 配置已更新'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/skills', methods=['POST'])
@require_permission('skills', 'write')
def create_skill():
    """创建自定义 Skill"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '')
        content = data.get('content', '')
        location = data.get('location', 'shared')
        agent_id = data.get('agentId', '')

        if not name:
            return jsonify({'success': False, 'error': 'Skill 名称不能为空'}), 400
        if not re.match(r'^[a-z0-9_-]+$', name):
            return jsonify({'success': False, 'error': 'Skill 名称只能包含小写字母、数字、下划线和横线'}), 400

        if location == 'workspace' and agent_id:
            agent = next((a for a in _get_agents_via_ws() if a.get('id') == agent_id), None)
            if not agent:
                return jsonify({'success': False, 'error': 'Agent 不存在'}), 404
            workspace = agent.get('workspace', '')
            if not workspace:
                return jsonify({'success': False, 'error': 'Agent 没有 workspace'}), 400
            skills_dir = Path(workspace) / 'skills'
        else:
            skills_dir = SHARED_SKILLS_DIR

        skills_dir.mkdir(parents=True, exist_ok=True)
        skill_dir = skills_dir / name

        if skill_dir.exists():
            return jsonify({'success': False, 'error': f'Skill {name} 已存在'}), 400

        skill_dir.mkdir()

        skill_md_content = f"""---
name: {name}
description: {description}
---

{content if content else f'# {name}\\n\\n自定义 Skill。'}
"""
        with open(skill_dir / 'SKILL.md', 'w', encoding='utf-8') as f:
            f.write(skill_md_content)

        log_operation_direct('create_skill', 'skill', name, json.dumps({'location': location, 'agentId': agent_id}))
        return jsonify({'success': True, 'data': {'name': name, 'path': str(skill_dir)}, 'message': f'Skill {name} 创建成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/skills/<skill_slug>', methods=['PUT'])
@require_permission('skills', 'write')
def update_skill(skill_slug):
    """更新 Skill 内容"""
    try:
        data = request.get_json()
        content = data.get('content', '')

        # 查找 skill
        skill_data = scan_skills()
        skill = None
        for agent in skill_data['agents']:
            for s in agent['skills']:
                if s['slug'] == skill_slug:
                    skill = s
                    break
            if skill:
                break

        if not skill:
            return jsonify({'success': False, 'error': 'Skill 不存在'}), 404
        if skill.get('level') == 'bundled':
            return jsonify({'success': False, 'error': 'Bundled Skill 不能编辑'}), 400

        skill_path = Path(skill['path'])
        skill_md = skill_path / 'SKILL.md'

        if skill_md.exists():
            import shutil
            shutil.copy(skill_md, skill_md.with_suffix('.md.bak'))

        with open(skill_md, 'w', encoding='utf-8') as f:
            f.write(content)

        log_operation_direct('update_skill', 'skill', skill_slug)
        return jsonify({'success': True, 'message': f'Skill {skill_slug} 已更新'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/skills/<skill_slug>', methods=['DELETE'])
@require_permission('skills', 'delete')
def delete_skill(skill_slug):
    """删除 Skill"""
    try:
        # 查找 skill
        skill_data = scan_skills()
        skill = None
        for agent in skill_data['agents']:
            for s in agent['skills']:
                if s['slug'] == skill_slug:
                    skill = s
                    break
            if skill:
                break

        if not skill:
            return jsonify({'success': False, 'error': 'Skill 不存在'}), 404
        if skill.get('level') == 'bundled':
            return jsonify({'success': False, 'error': 'Bundled Skill 不能删除'}), 400

        import shutil
        shutil.rmtree(Path(skill['path']))

        config = _get_config_via_ws()
        if skill_slug in config.get('skills', {}).get('entries', {}):
            del config['skills']['entries'][skill_slug]
            _save_config_via_ws(config)

        log_operation_direct('delete_skill', 'skill', skill_slug)
        return jsonify({'success': True, 'message': f'Skill {skill_slug} 已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 部门管理 API ====================

@app.route('/api/departments', methods=['GET'])
def get_departments():
    """获取部门列表（树形结构）"""
    try:
        departments = db.fetch_all("SELECT * FROM departments ORDER BY sort_order, id")

        # 构建树形结构
        dept_map = {d['id']: {**d, 'children': []} for d in departments}
        tree = []

        for dept in dept_map.values():
            if dept['parent_id'] is None:
                tree.append(dept)
            else:
                parent = dept_map.get(dept['parent_id'])
                if parent:
                    parent['children'].append(dept)

        return jsonify({'success': True, 'data': tree})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/departments', methods=['POST'])
@require_permission('employees', 'write')
def create_department():
    """创建部门"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        parent_id = data.get('parent_id')
        leader_id = data.get('leader_id')
        sort_order = data.get('sort_order', 0)

        if not name:
            return jsonify({'success': False, 'error': '部门名称不能为空'}), 400

        dept_id = db.insert('departments', {
            'name': name,
            'parent_id': parent_id,
            'leader_id': leader_id,
            'sort_order': sort_order
        })

        log_operation_direct('create_department', 'department', str(dept_id), {'name': name})
        return jsonify({'success': True, 'data': {'id': dept_id, 'name': name}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/departments/<int:dept_id>', methods=['PUT'])
@require_permission('employees', 'write')
def update_department(dept_id):
    """更新部门"""
    try:
        data = request.get_json()
        update_data = {}

        if 'name' in data:
            update_data['name'] = data['name'].strip()
        if 'parent_id' in data:
            update_data['parent_id'] = data['parent_id']
        if 'leader_id' in data:
            update_data['leader_id'] = data['leader_id']
        if 'sort_order' in data:
            update_data['sort_order'] = data['sort_order']

        update_data['updated_at'] = datetime.now().isoformat()

        db.update('departments', update_data, 'id = ?', (dept_id,))
        log_operation_direct('update_department', 'department', str(dept_id))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/departments/<int:dept_id>', methods=['DELETE'])
@require_permission('employees', 'delete')
def delete_department(dept_id):
    """删除部门"""
    try:
        # 检查是否有子部门
        children = db.fetch_all("SELECT id FROM departments WHERE parent_id = ?", (dept_id,))
        if children:
            return jsonify({'success': False, 'error': '该部门下有子部门，无法删除'}), 400

        # 检查是否有员工
        employees = db.fetch_all("SELECT id FROM employees WHERE department_id = ?", (dept_id,))
        if employees:
            return jsonify({'success': False, 'error': '该部门下有员工，无法删除'}), 400

        db.delete('departments', 'id = ?', (dept_id,))
        log_operation_direct('delete_department', 'department', str(dept_id))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 员工管理 API ====================

@app.route('/api/employees', methods=['GET'])
def get_employees():
    """获取员工列表"""
    try:
        employees = db.fetch_all("""
            SELECT e.*, d.name as department_name, m.name as manager_name
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.id
            LEFT JOIN employees m ON e.manager_id = m.id
            ORDER BY e.id
        """)

        # 获取所有 Agent 信息
        agents = _get_agents_via_ws()

        # 为每个员工添加 Agent 信息
        for emp in employees:
            if emp.get('agent_id'):
                agent = next((a for a in agents if a['id'] == emp['agent_id']), None)
                if agent:
                    emp['agent_name'] = agent.get('name')
                    emp['agent_model'] = agent.get('model', {}).get('primary')
                else:
                    emp['agent_name'] = None
                    emp['agent_model'] = None
            else:
                emp['agent_name'] = None
                emp['agent_model'] = None

        # 获取未绑定的 Agent（用于下拉选择）
        bound_agent_ids = [e['agent_id'] for e in employees if e.get('agent_id')]
        unbound_agents = [a for a in agents if a['id'] not in bound_agent_ids]

        user = get_current_user()
        can_edit = has_permission(user, 'employees', 'write')
        can_delete = has_permission(user, 'employees', 'delete')

        return jsonify({
            'success': True,
            'data': employees,
            'unbound_agents': unbound_agents,
            'permissions': {'can_edit': can_edit, 'can_delete': can_delete}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/employees/<int:emp_id>', methods=['GET'])
def get_employee(emp_id):
    """获取员工详情"""
    try:
        emp = db.fetch_one("""
            SELECT e.*, d.name as department_name, m.name as manager_name
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.id
            LEFT JOIN employees m ON e.manager_id = m.id
            WHERE e.id = ?
        """, (emp_id,))

        if not emp:
            return jsonify({'success': False, 'error': '员工不存在'}), 404

        # 添加 Agent 信息
        if emp.get('agent_id'):
            agent = _get_agent_via_ws(emp['agent_id'])
            if agent:
                emp['agent_info'] = agent

        # 获取下属员工
        subordinates = db.fetch_all(
            "SELECT id, name, agent_id FROM employees WHERE manager_id = ?",
            (emp_id,)
        )

        return jsonify({
            'success': True,
            'data': emp,
            'subordinates': subordinates
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/employees', methods=['POST'])
@require_permission('employees', 'write')
def create_employee():
    """创建员工"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        email = data.get('email', '').strip() or None
        phone = data.get('phone', '').strip() or None
        department_id = data.get('department_id')
        manager_id = data.get('manager_id')
        agent_id = data.get('agent_id')

        if not name:
            return jsonify({'success': False, 'error': '员工姓名不能为空'}), 400

        # 检查 agent_id 是否已被绑定
        if agent_id:
            existing = db.fetch_one("SELECT id FROM employees WHERE agent_id = ?", (agent_id,))
            if existing:
                return jsonify({'success': False, 'error': '该 Agent 已被其他员工绑定'}), 400

        emp_id = db.insert('employees', {
            'name': name,
            'email': email,
            'phone': phone,
            'department_id': department_id,
            'manager_id': manager_id,
            'agent_id': agent_id
        })

        log_operation_direct('create_employee', 'employee', str(emp_id), {'name': name})
        return jsonify({'success': True, 'data': {'id': emp_id, 'name': name}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/employees/<int:emp_id>', methods=['PUT'])
@require_permission('employees', 'write')
def update_employee(emp_id):
    """更新员工"""
    try:
        data = request.get_json()
        update_data = {}

        if 'name' in data:
            update_data['name'] = data['name'].strip()
        if 'email' in data:
            update_data['email'] = data['email'].strip() or None
        if 'phone' in data:
            update_data['phone'] = data['phone'].strip() or None
        if 'department_id' in data:
            update_data['department_id'] = data['department_id']
        if 'manager_id' in data:
            update_data['manager_id'] = data['manager_id']
        if 'status' in data:
            update_data['status'] = data['status']

        # 处理 Agent 绑定
        if 'agent_id' in data:
            new_agent_id = data['agent_id']
            if new_agent_id:
                # 检查是否被其他员工绑定
                existing = db.fetch_one(
                    "SELECT id FROM employees WHERE agent_id = ? AND id != ?",
                    (new_agent_id, emp_id)
                )
                if existing:
                    return jsonify({'success': False, 'error': '该 Agent 已被其他员工绑定'}), 400
            update_data['agent_id'] = new_agent_id or None

        update_data['updated_at'] = datetime.now().isoformat()

        db.update('employees', update_data, 'id = ?', (emp_id,))
        log_operation_direct('update_employee', 'employee', str(emp_id))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/employees/<int:emp_id>', methods=['DELETE'])
@require_permission('employees', 'delete')
def delete_employee(emp_id):
    """删除员工"""
    try:
        # 检查是否是其他员工的上级
        subordinates = db.fetch_all("SELECT id FROM employees WHERE manager_id = ?", (emp_id,))
        if subordinates:
            return jsonify({'success': False, 'error': '该员工是其他员工的上级，无法删除'}), 400

        # 检查是否是部门负责人
        depts = db.fetch_all("SELECT id FROM departments WHERE leader_id = ?", (emp_id,))
        if depts:
            return jsonify({'success': False, 'error': '该员工是部门负责人，无法删除'}), 400

        emp = db.fetch_one("SELECT name FROM employees WHERE id = ?", (emp_id,))
        db.delete('employees', 'id = ?', (emp_id,))

        log_operation_direct('delete_employee', 'employee', str(emp_id), {'name': emp['name'] if emp else ''})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/employees/<int:emp_id>/bind-agent', methods=['POST'])
@require_permission('employees', 'write')
def bind_agent_to_employee(emp_id):
    """为员工绑定 Agent"""
    try:
        data = request.get_json()
        agent_id = data.get('agent_id')

        if not agent_id:
            return jsonify({'success': False, 'error': '请选择要绑定的 Agent'}), 400

        # 检查 Agent 是否存在
        agent = _get_agent_via_ws(agent_id)
        if not agent:
            return jsonify({'success': False, 'error': 'Agent 不存在'}), 404

        # 检查是否已被绑定
        existing = db.fetch_one(
            "SELECT id FROM employees WHERE agent_id = ? AND id != ?",
            (agent_id, emp_id)
        )
        if existing:
            return jsonify({'success': False, 'error': '该 Agent 已被其他员工绑定'}), 400

        db.update('employees', {'agent_id': agent_id, 'updated_at': datetime.now().isoformat()}, 'id = ?', (emp_id,))
        log_operation_direct('bind_agent', 'employee', str(emp_id), {'agent_id': agent_id})
        return jsonify({'success': True, 'message': f'已绑定 Agent: {agent.get("name")}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/employees/<int:emp_id>/unbind-agent', methods=['POST'])
@require_permission('employees', 'write')
def unbind_agent_from_employee(emp_id):
    """解除员工的 Agent 绑定"""
    try:
        db.update('employees', {'agent_id': None, 'updated_at': datetime.now().isoformat()}, 'id = ?', (emp_id,))
        log_operation_direct('unbind_agent', 'employee', str(emp_id))
        return jsonify({'success': True, 'message': '已解除 Agent 绑定'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Gateway 管理 API ====================

@app.route('/api/gateways', methods=['GET'])
@require_auth
def get_gateways():
    """获取 Gateway 列表"""
    try:
        gateways = db.fetch_all("SELECT * FROM gateways ORDER BY is_default DESC, id")

        # 脱敏处理 token
        for gw in gateways:
            if gw.get('auth_token'):
                gw['auth_token_masked'] = '******' + gw['auth_token'][-4:] if len(gw['auth_token']) > 4 else '******'
            else:
                gw['auth_token_masked'] = ''

        return jsonify({'success': True, 'data': gateways})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/gateways', methods=['POST'])
@require_permission('gateway', 'write')
def create_gateway():
    """创建 Gateway"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        url = data.get('url', '').strip()
        auth_token = data.get('auth_token', '').strip()
        is_default = data.get('is_default', False)

        if not name:
            return jsonify({'success': False, 'error': 'Gateway 名称不能为空'}), 400
        if not url:
            return jsonify({'success': False, 'error': 'Gateway URL 不能为空'}), 400

        # 验证 URL 格式
        if not url.startswith(('ws://', 'wss://')):
            return jsonify({'success': False, 'error': 'URL 必须以 ws:// 或 wss:// 开头'}), 400

        # 如果设为默认，取消其他默认
        if is_default:
            db.execute("UPDATE gateways SET is_default = 0")

        gw_id = db.insert('gateways', {
            'name': name,
            'url': url,
            'auth_token': auth_token,
            'is_default': 1 if is_default else 0,
            'status': 'unknown'
        })

        log_operation_direct('create_gateway', 'gateway', str(gw_id), {'name': name, 'url': url})
        return jsonify({'success': True, 'data': {'id': gw_id, 'name': name}, 'message': 'Gateway 创建成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/gateways/<int:gw_id>', methods=['PUT'])
@require_permission('gateway', 'write')
def update_gateway(gw_id):
    """更新 Gateway"""
    try:
        data = request.get_json()
        update_data = {'updated_at': datetime.now().isoformat()}

        if 'name' in data:
            update_data['name'] = data['name'].strip()
        if 'url' in data:
            url = data['url'].strip()
            if not url.startswith(('ws://', 'wss://')):
                return jsonify({'success': False, 'error': 'URL 必须以 ws:// 或 wss:// 开头'}), 400
            update_data['url'] = url
        if 'auth_token' in data:
            update_data['auth_token'] = data['auth_token'].strip()
        if 'is_default' in data:
            if data['is_default']:
                db.execute("UPDATE gateways SET is_default = 0")
            update_data['is_default'] = 1 if data['is_default'] else 0

        db.update('gateways', update_data, 'id = ?', (gw_id,))
        log_operation_direct('update_gateway', 'gateway', str(gw_id))

        return jsonify({'success': True, 'message': 'Gateway 已更新'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/gateways/<int:gw_id>', methods=['DELETE'])
@require_permission('gateway', 'delete')
def delete_gateway(gw_id):
    """删除 Gateway"""
    try:
        # 检查是否是唯一的默认 Gateway
        gw = db.fetch_one("SELECT * FROM gateways WHERE id = ?", (gw_id,))
        if not gw:
            return jsonify({'success': False, 'error': 'Gateway 不存在'}), 404

        # 检查是否是最后一个 Gateway
        count = db.fetch_one("SELECT COUNT(*) as total FROM gateways")
        if count['total'] <= 1:
            return jsonify({'success': False, 'error': '至少保留一个 Gateway'}), 400

        db.delete('gateways', 'id = ?', (gw_id,))
        log_operation_direct('delete_gateway', 'gateway', str(gw_id))

        # 如果删除的是默认 Gateway，设置第一个为默认
        if gw['is_default']:
            first_gw = db.fetch_one("SELECT id FROM gateways LIMIT 1")
            if first_gw:
                db.update('gateways', {'is_default': 1}, 'id = ?', (first_gw['id'],))

        return jsonify({'success': True, 'message': 'Gateway 已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/gateways/<int:gw_id>/test', methods=['POST'])
@require_auth
def test_gateway(gw_id):
    """测试 Gateway 连接"""
    try:
        gw = db.fetch_one("SELECT * FROM gateways WHERE id = ?", (gw_id,))
        if not gw:
            return jsonify({'success': False, 'error': 'Gateway 不存在'}), 404

        # 尝试连接
        from gateway_sync import get_sync_client, GatewayError

        try:
            client = get_sync_client(gateway_id=gw_id)
            # 调用 agents.list 测试连接
            result = client.call('agents.list')
            agents = result.get('agents', [])

            # 更新状态
            db.update('gateways', {
                'status': 'online',
                'last_connected_at': datetime.now().isoformat()
            }, 'id = ?', (gw_id,))

            return jsonify({
                'success': True,
                'data': {
                    'status': 'online',
                    'agent_count': len(agents)
                },
                'message': f'连接成功，发现 {len(agents)} 个 Agent'
            })
        except GatewayError as e:
            db.update('gateways', {'status': 'error'}, 'id = ?', (gw_id,))
            return jsonify({'success': False, 'error': f'连接失败: {e.message}'})
        except Exception as e:
            db.update('gateways', {'status': 'error'}, 'id = ?', (gw_id,))
            return jsonify({'success': False, 'error': f'连接失败: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/gateways/<int:gw_id>/set-default', methods=['POST'])
@require_permission('gateway', 'write')
def set_default_gateway(gw_id):
    """设置默认 Gateway"""
    try:
        gw = db.fetch_one("SELECT * FROM gateways WHERE id = ?", (gw_id,))
        if not gw:
            return jsonify({'success': False, 'error': 'Gateway 不存在'}), 404

        # 取消其他默认
        db.execute("UPDATE gateways SET is_default = 0")

        # 设置新的默认
        db.update('gateways', {'is_default': 1}, 'id = ?', (gw_id,))

        # 更新当前使用的 Gateway
        from gateway_sync import set_current_gateway
        set_current_gateway(gw_id)

        log_operation_direct('set_default_gateway', 'gateway', str(gw_id))
        return jsonify({'success': True, 'message': f'已将 {gw["name"]} 设为默认 Gateway'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/gateways/current', methods=['GET'])
@require_auth
def get_current_gateway():
    """获取当前使用的 Gateway（含实时状态检查）"""
    try:
        if settings.current_gateway_id is not None:
            gw = db.fetch_one("SELECT * FROM gateways WHERE id = ?", (settings.current_gateway_id,))
        else:
            gw = db.fetch_one("SELECT * FROM gateways WHERE is_default = 1")

        if not gw:
            gw = db.fetch_one("SELECT * FROM gateways LIMIT 1")

        if gw:
            # 快速状态检查（不更新数据库，只返回当前状态）
            try:
                from gateway_sync import sync_call
                sync_call('agents.list')
                gw['status'] = 'online'
            except Exception:
                gw['status'] = 'error'

        return jsonify({'success': True, 'data': gw})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/gateways/current', methods=['PUT'])
@require_permission('gateway', 'write')
def set_current_gateway_api():
    """切换当前使用的 Gateway"""
    try:
        data = request.get_json()
        gw_id = data.get('gateway_id')

        if gw_id is None:
            return jsonify({'success': False, 'error': '缺少 gateway_id'}), 400

        gw = db.fetch_one("SELECT * FROM gateways WHERE id = ?", (gw_id,))
        if not gw:
            return jsonify({'success': False, 'error': 'Gateway 不存在'}), 404

        from gateway_sync import set_current_gateway
        set_current_gateway(gw_id)

        log_operation_direct('switch_gateway', 'gateway', str(gw_id))
        return jsonify({'success': True, 'message': f'已切换到 {gw["name"]}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 渠道配置管理 API ====================

@app.route('/api/channel-config/types', methods=['GET'])
@require_permission('config', 'read')
def get_channel_types():
    """获取所有渠道类型"""
    try:
        types = channel_manager.get_channel_types()
        return jsonify({'success': True, 'data': types})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/channel-config', methods=['GET'])
@require_permission('config', 'read')
def list_channel_configs():
    """获取所有渠道配置"""
    try:
        configs = channel_manager.list_configs()
        return jsonify({'success': True, 'data': configs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/channel-config/<channel_type>', methods=['GET'])
@require_permission('config', 'read')
def get_channel_config(channel_type):
    """获取指定渠道配置"""
    try:
        config = channel_manager.get_config(channel_type)
        if not config:
            return jsonify({'success': True, 'data': None})
        return jsonify({'success': True, 'data': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/channel-config/<channel_type>', methods=['POST'])
@require_permission('config', 'write')
@log_operation('保存渠道配置', 'channel-config')
def save_channel_config(channel_type):
    """保存渠道配置"""
    try:
        data = request.get_json()

        # 验证配置
        validation = channel_manager.validate_config(channel_type, data)
        if not validation['valid']:
            return jsonify({
                'success': False,
                'error': '配置验证失败',
                'details': validation['errors']
            }), 400

        # 保存配置
        config = channel_manager.save_config(channel_type, data)

        logger.info(f'保存渠道配置成功: {channel_type}')
        return jsonify({
            'success': True,
            'data': config,
            'warnings': validation.get('warnings', [])
        })

    except Exception as e:
        logger.error(f'保存渠道配置失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/channel-config/<channel_type>', methods=['DELETE'])
@require_permission('config', 'write')
@log_operation('删除渠道配置', 'channel-config')
def delete_channel_config(channel_type):
    """删除渠道配置"""
    try:
        success = channel_manager.delete_config(channel_type)
        if not success:
            return jsonify({'success': False, 'error': '配置不存在'}), 404

        logger.info(f'删除渠道配置成功: {channel_type}')
        return jsonify({'success': True, 'message': '配置已删除'})

    except Exception as e:
        logger.error(f'删除渠道配置失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/channel-config/<channel_type>/validate', methods=['POST'])
@require_permission('config', 'read')
def validate_channel_config(channel_type):
    """验证渠道配置"""
    try:
        data = request.get_json()
        validation = channel_manager.validate_config(channel_type, data)
        return jsonify({'success': True, 'data': validation})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 配置同步 API ====================

@app.route('/api/sync/status', methods=['GET'])
@require_permission('config', 'read')
def get_sync_status():
    """获取同步状态"""
    try:
        status = config_sync.get_sync_status()
        return jsonify({'success': True, 'data': status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sync/models', methods=['POST'])
@require_permission('config', 'write')
@log_operation('同步模型配置', 'sync')
def sync_models():
    """同步模型配置到 Gateway"""
    try:
        result = config_sync.sync_models_to_gateway()
        if result['success']:
            logger.info(result['message'])
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'error': result.get('error', '同步失败')}), 500
    except Exception as e:
        logger.error(f'同步模型失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sync/channel/<channel_type>', methods=['POST'])
@require_permission('config', 'write')
@log_operation('同步渠道配置', 'sync')
def sync_channel(channel_type):
    """同步渠道配置到 Gateway"""
    try:
        result = config_sync.sync_channel_to_gateway(channel_type)
        if result['success']:
            logger.info(result['message'])
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'error': result.get('error', '同步失败')}), 500
    except Exception as e:
        logger.error(f'同步渠道失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sync/all', methods=['POST'])
@require_permission('config', 'write')
@log_operation('同步所有配置', 'sync')
def sync_all():
    """同步所有配置到 Gateway"""
    try:
        results = config_sync.sync_all_to_gateway()
        logger.info(f'配置同步完成: {results}')
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        logger.error(f'同步失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 任务管理 API ====================

@app.route('/api/tasks', methods=['GET'])
@require_permission('employees', 'read')
def get_tasks():
    """获取任务列表"""
    try:
        # 获取查询参数
        agent_id = request.args.get('agent_id')
        status = request.args.get('status')
        task_type = request.args.get('task_type')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

        # 构建查询
        query = 'SELECT * FROM tasks WHERE 1=1'
        params = []

        if agent_id:
            query += ' AND agent_id = ?'
            params.append(agent_id)
        if status:
            query += ' AND status = ?'
            params.append(status)
        if task_type:
            query += ' AND task_type = ?'
            params.append(task_type)
        if date_from:
            query += ' AND created_at >= ?'
            params.append(date_from)
        if date_to:
            query += ' AND created_at <= ?'
            params.append(date_to)

        query += ' ORDER BY created_at DESC LIMIT 500'

        tasks = db.fetch_all(query, tuple(params))
        return jsonify({'success': True, 'data': tasks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/stats', methods=['GET'])
@require_permission('employees', 'read')
def get_task_stats():
    """获取任务统计"""
    try:
        # 总任务数
        total = db.fetch_one('SELECT COUNT(*) as count FROM tasks')
        total_count = total['count'] if total else 0

        # 按状态统计
        status_stats = db.fetch_all(
            'SELECT status, COUNT(*) as count FROM tasks GROUP BY status'
        )
        status_counts = {s['status']: s['count'] for s in status_stats}

        # 按类型统计
        type_stats = db.fetch_all(
            'SELECT task_type, COUNT(*) as count FROM tasks GROUP BY task_type'
        )
        type_counts = {t['task_type'] or 'unknown': t['count'] for t in type_stats}

        # 按 Agent 统计
        agent_stats = db.fetch_all(
            'SELECT agent_id, COUNT(*) as count FROM tasks GROUP BY agent_id ORDER BY count DESC LIMIT 10'
        )

        # 今日任务
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        today_tasks = db.fetch_one(
            'SELECT COUNT(*) as count FROM tasks WHERE date(created_at) = ?',
            (today,)
        )
        today_count = today_tasks['count'] if today_tasks else 0

        # 平均耗时
        avg_duration = db.fetch_one(
            'SELECT AVG(duration_seconds) as avg FROM tasks WHERE duration_seconds IS NOT NULL'
        )
        avg_seconds = avg_duration['avg'] if avg_duration and avg_duration['avg'] else 0

        return jsonify({
            'success': True,
            'data': {
                'total': total_count,
                'today': today_count,
                'by_status': status_counts,
                'by_type': type_counts,
                'by_agent': agent_stats,
                'avg_duration_seconds': int(avg_seconds)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@require_permission('employees', 'read')
def get_task(task_id):
    """获取任务详情"""
    try:
        task = db.fetch_one('SELECT * FROM tasks WHERE id = ?', (task_id,))
        if not task:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        return jsonify({'success': True, 'data': task})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Focus Mode API ====================
# Focus Context Engine 插件提供的专注模式功能

@app.route('/api/focus/focus', methods=['POST'])
@require_permission('sessions', 'edit')
def focus_mode():
    """启用专注模式并可选触发压缩"""
    try:
        data = request.json
        session_key = data.get('sessionKey')
        task_description = data.get('taskDescription')
        keywords = data.get('keywords')
        compact_now = data.get('compactNow', False)

        if not session_key:
            return jsonify({'success': False, 'error': '缺少 sessionKey'}), 400

        # 通过 Gateway WebSocket 调用 Focus 插件
        params = {
            'sessionKey': session_key,
            'taskDescription': task_description,
            'keywords': keywords,
            'compactNow': compact_now
        }
        # 移除 None 值
        params = {k: v for k, v in params.items() if v is not None}

        result = sync_call('focus.focus', params)

        if result and result.get('success'):
            log_operation_direct('focus_mode', 'enable',
                f'{session_key}: {task_description or "无描述"}')
            return jsonify({
                'success': True,
                'data': result.get('status', {}),
                'message': result.get('message', '')
            })
        else:
            error_msg = result.get('error', {}).get('message', '启用专注模式失败') if result else 'Gateway 无响应'
            return jsonify({'success': False, 'error': error_msg}), 500

    except GatewayError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Focus mode error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/focus/compact', methods=['POST'])
@require_permission('sessions', 'edit')
def focus_compact():
    """执行智能压缩（清理无关上下文）"""
    try:
        data = request.json
        session_key = data.get('sessionKey')
        task_description = data.get('taskDescription')
        keywords = data.get('keywords')
        token_budget = data.get('tokenBudget')

        if not session_key:
            return jsonify({'success': False, 'error': '缺少 sessionKey'}), 400

        # 通过 Gateway WebSocket 调用 Focus 插件的 compact 方法
        params = {
            'sessionKey': session_key,
            'taskDescription': task_description,
            'keywords': keywords,
            'tokenBudget': token_budget
        }
        # 移除 None 值
        params = {k: v for k, v in params.items() if v is not None}

        result = sync_call('focus.compact', params)

        if result and result.get('success'):
            # 记录压缩结果
            compact_result = result.get('result', {})
            tokens_saved = compact_result.get('tokensBefore', 0) - compact_result.get('tokensAfter', 0)
            messages_removed = compact_result.get('details', {}).get('messagesRemoved', 0)

            log_operation_direct('focus_compact', 'execute',
                f'{session_key}: removed {messages_removed} messages, saved {tokens_saved} tokens')

            return jsonify({
                'success': True,
                'compacted': result.get('compacted', False),
                'data': compact_result
            })
        else:
            error_msg = result.get('error', {}).get('message', '压缩失败') if result else 'Gateway 无响应'
            return jsonify({'success': False, 'error': error_msg}), 500

    except GatewayError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Focus compact error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/focus/status', methods=['GET'])
@require_permission('sessions', 'read')
def focus_get_status():
    """获取专注模式状态"""
    try:
        session_key = request.args.get('sessionKey')
        if not session_key:
            return jsonify({'success': False, 'error': '缺少 sessionKey'}), 400

        result = sync_call('focus.getStatus', {'sessionKey': session_key})

        if result:
            return jsonify({
                'success': True,
                'data': result.get('status', {})
            })
        else:
            return jsonify({'success': False, 'error': 'Gateway 无响应'}), 500

    except GatewayError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Focus status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/focus/clear', methods=['POST'])
@require_permission('sessions', 'edit')
def focus_clear():
    """清除专注模式"""
    try:
        data = request.json
        session_key = data.get('sessionKey')
        if not session_key:
            return jsonify({'success': False, 'error': '缺少 sessionKey'}), 400

        result = sync_call('focus.clearStatus', {'sessionKey': session_key})

        if result and result.get('success'):
            log_operation_direct('focus_mode', 'clear', session_key)
            return jsonify({
                'success': True,
                'message': '专注模式已清除'
            })
        else:
            error_msg = result.get('error', {}).get('message', '清除失败') if result else 'Gateway 无响应'
            return jsonify({'success': False, 'error': error_msg}), 500

    except GatewayError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Focus clear error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 知识库管理 API ====================

@app.route('/api/knowledge', methods=['GET'])
@require_permission('skills', 'read')
def get_knowledge_bases():
    """获取知识库列表"""
    try:
        # 从 Gateway 获取 Agent 列表
        agents = _get_agents_via_ws()

        # 为每个 Agent 构建知识库信息
        knowledge_bases = []
        for agent in agents:
            agent_id = agent.get('id')
            workspace = agent.get('workspace', '')

            # 检查 knowledge 目录
            import os
            from pathlib import Path

            if workspace:
                knowledge_path = Path(workspace) / 'knowledge'
                if knowledge_path.exists():
                    files = list(knowledge_path.glob('*'))
                    knowledge_bases.append({
                        'agent_id': agent_id,
                        'agent_name': agent.get('name', agent_id),
                        'file_count': len([f for f in files if f.is_file()]),
                        'total_size': sum(f.stat().st_size for f in files if f.is_file()),
                        'path': str(knowledge_path),
                        'exists': True
                    })
                else:
                    knowledge_bases.append({
                        'agent_id': agent_id,
                        'agent_name': agent.get('name', agent_id),
                        'file_count': 0,
                        'total_size': 0,
                        'path': str(knowledge_path),
                        'exists': False
                    })

        return jsonify({'success': True, 'data': knowledge_bases})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/knowledge/<agent_id>', methods=['GET'])
@require_permission('skills', 'read')
def get_knowledge_files(agent_id):
    """获取知识库文件列表"""
    try:
        agent = _get_agent_via_ws(agent_id)
        if not agent:
            return jsonify({'success': False, 'error': 'Agent 不存在'}), 404

        workspace = agent.get('workspace', '')
        if not workspace:
            return jsonify({'success': False, 'error': 'Agent 未配置 workspace'}), 400

        from pathlib import Path
        knowledge_path = Path(workspace) / 'knowledge'

        files = []
        if knowledge_path.exists():
            for f in knowledge_path.iterdir():
                if f.is_file():
                    stat = f.stat()
                    files.append({
                        'name': f.name,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'type': f.suffix
                    })

        return jsonify({
            'success': True,
            'data': {
                'agent_id': agent_id,
                'path': str(knowledge_path),
                'files': files
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 图片生成 API ====================

from image_generator import get_image_generator

@app.route('/api/image-generator/generate', methods=['POST'])
@require_auth
def generate_image():
    """
    文生图 - 根据提示词生成图片

    请求参数:
        prompt: 提示词（必填）
        size: 图片尺寸，"1K" 或 "2K"（默认 "1K"）
        n: 生成数量，1-4（默认 1）
    """
    data = request.get_json()
    prompt = data.get('prompt', '').strip()
    size = data.get('size', '1K')
    n = data.get('n', 1)

    if not prompt:
        return jsonify({'success': False, 'error': '请输入提示词'}), 400

    # 验证参数（火山引擎要求至少 3686400 像素）
    valid_sizes = ["2k", "4k"]
    if size not in valid_sizes:
        size = '2k'
    n = max(1, min(4, int(n)))

    try:
        generator = get_image_generator()
        result = generator.generate(prompt, size=size, n=n)

        # 保存到历史记录
        try:
            user = get_current_user()
            user_id = user.get('user_id') if user else None

            import json
            db.insert('image_generation_history', {
                'user_id': user_id,
                'prompt': prompt,
                'size': size,
                'n': n,
                'images': json.dumps(result.get('images', []))
            })
        except Exception as e:
            logger.warning(f"保存历史记录失败: {e}")

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"图片生成失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/image-generator/history', methods=['GET'])
@require_auth
def get_image_history():
    """获取图片生成历史"""
    try:
        user = get_current_user()
        user_id = user.get('user_id')

        # 获取最近的 50 条记录
        history = db.fetch_all(
            """SELECT * FROM image_generation_history
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT 50""",
            (user_id,)
        )

        import json
        result = []
        for item in history:
            result.append({
                'id': item['id'],
                'prompt': item['prompt'],
                'size': item['size'],
                'n': item['n'],
                'images': json.loads(item['images']),
                'created_at': item['created_at']
            })

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/image-generator/history/<int:history_id>', methods=['DELETE'])
@require_auth
def delete_image_history(history_id):
    """删除图片生成历史"""
    try:
        user = get_current_user()
        user_id = user.get('user_id')

        # 只能删除自己的历史
        db.execute(
            "DELETE FROM image_generation_history WHERE id = ? AND user_id = ?",
            (history_id, user_id)
        )

        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        logger.error(f"删除历史记录失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 模型提供商管理 ====================

@app.route('/api/model-providers', methods=['GET'])
@require_auth
def list_model_providers():
    """获取所有模型提供商"""
    try:
        providers = db.fetch_all(
            "SELECT * FROM model_providers ORDER BY created_at DESC"
        )

        result = []
        for p in providers:
            result.append({
                'id': p['id'],
                'name': p['name'],
                'display_name': p['display_name'],
                'base_url': p['base_url'],
                'api_key_env': p['api_key_env'],
                'api_type': p['api_type'],
                'enabled': p['enabled'],
                'config_json': p['config_json'],
                'created_at': p['created_at'],
                'updated_at': p['updated_at']
            })

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"获取模型提供商失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/model-providers', methods=['POST'])
@require_auth
def create_model_provider():
    """创建模型提供商"""
    try:
        data = request.get_json()

        # 验证必填字段
        required = ['name', 'display_name', 'base_url', 'api_key_env']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} 是必填字段'}), 400

        # 检查名称是否已存在
        existing = db.fetch_one(
            "SELECT id FROM model_providers WHERE name = ?",
            (data['name'],)
        )
        if existing:
            return jsonify({'success': False, 'error': '提供商名称已存在'}), 400

        # 插入数据
        provider_id = db.insert('model_providers', {
            'name': data['name'],
            'display_name': data['display_name'],
            'base_url': data['base_url'],
            'api_key_env': data['api_key_env'],
            'api_type': data.get('api_type', 'image-generation'),
            'enabled': 1 if data.get('enabled', True) else 0,
            'config_json': data.get('config_json', '')
        })

        log_operation_direct('创建模型提供商', 'model_provider', str(provider_id))

        return jsonify({'success': True, 'data': {'id': provider_id}})
    except Exception as e:
        logger.error(f"创建模型提供商失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/model-providers/<int:provider_id>', methods=['PUT'])
@require_auth
def update_model_provider(provider_id):
    """更新模型提供商"""
    try:
        data = request.get_json()

        # 检查是否存在
        existing = db.fetch_one(
            "SELECT id FROM model_providers WHERE id = ?",
            (provider_id,)
        )
        if not existing:
            return jsonify({'success': False, 'error': '提供商不存在'}), 404

        # 更新数据
        update_data = {}
        if 'display_name' in data:
            update_data['display_name'] = data['display_name']
        if 'base_url' in data:
            update_data['base_url'] = data['base_url']
        if 'api_key_env' in data:
            update_data['api_key_env'] = data['api_key_env']
        if 'api_type' in data:
            update_data['api_type'] = data['api_type']
        if 'enabled' in data:
            update_data['enabled'] = 1 if data['enabled'] else 0
        if 'config_json' in data:
            update_data['config_json'] = data['config_json']

        if update_data:
            db.update('model_providers', update_data, 'id = ?', (provider_id,))

        log_operation_direct('更新模型提供商', 'model_provider', str(provider_id))

        return jsonify({'success': True, 'message': '更新成功'})
    except Exception as e:
        logger.error(f"更新模型提供商失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/model-providers/<int:provider_id>', methods=['PATCH'])
@require_auth
def patch_model_provider(provider_id):
    """部分更新模型提供商（如启用/禁用）"""
    try:
        data = request.get_json()

        # 检查是否存在
        existing = db.fetch_one(
            "SELECT id FROM model_providers WHERE id = ?",
            (provider_id,)
        )
        if not existing:
            return jsonify({'success': False, 'error': '提供商不存在'}), 404

        # 更新数据
        update_data = {}
        if 'enabled' in data:
            update_data['enabled'] = 1 if data['enabled'] else 0

        if update_data:
            db.update('model_providers', update_data, 'id = ?', (provider_id,))

        return jsonify({'success': True, 'message': '更新成功'})
    except Exception as e:
        logger.error(f"更新模型提供商失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/model-providers/<int:provider_id>', methods=['DELETE'])
@require_auth
def delete_model_provider(provider_id):
    """删除模型提供商"""
    try:
        # 检查是否存在
        existing = db.fetch_one(
            "SELECT name FROM model_providers WHERE id = ?",
            (provider_id,)
        )
        if not existing:
            return jsonify({'success': False, 'error': '提供商不存在'}), 404

        db.execute("DELETE FROM model_providers WHERE id = ?", (provider_id,))

        log_operation_direct('删除模型提供商', 'model_provider', str(provider_id))

        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        logger.error(f"删除模型提供商失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("OpenClaw Admin Backend (企业版)")
    print("=" * 50)
    print(f"数据库路径: {db.db_path}")

    # 显示实际使用的 Gateway URL（优先从数据库获取）
    try:
        gateway = db.fetch_one("SELECT url FROM gateways WHERE is_default = 1")
        actual_url = gateway['url'] if gateway else settings.GATEWAY_URL
    except:
        actual_url = settings.GATEWAY_URL
    print(f"Gateway URL: {actual_url}")

    try:
        agents = _get_agents_via_ws()
        print(f"Agents 数量: {len(agents)}")
    except Exception as e:
        print(f"Gateway 连接失败: {e}")
    print("=" * 50)
    print("默认管理员账户: admin / admin123")
    print("=" * 50)

    app.run(host='127.0.0.1', port=5001, debug=True)
