"""
权限装饰器和日志装饰器
"""
from functools import wraps
from flask import request, jsonify, g
from auth import verify_access_token
from database import db
import json
import logging
import traceback
from datetime import datetime


# 获取日志器
logger = logging.getLogger('api')


def get_current_user():
    """从请求中获取当前用户"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header[7:]
    payload = verify_access_token(token)
    if not payload:
        return None

    return payload


def require_auth(f):
    """需要登录验证"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'error': '未登录或 Token 已过期'
            }), 401
        return f(*args, **kwargs)
    return decorated


def get_user_permissions(role_id: int) -> dict:
    """获取用户角色的权限配置"""
    role = db.fetch_one("SELECT permissions FROM roles WHERE id = ?", (role_id,))
    if role:
        return json.loads(role['permissions'])
    return {}


def has_permission(user: dict, resource: str, action: str) -> bool:
    """检查用户是否有指定权限"""
    # admin 角色拥有所有权限
    if user.get('role') == 'admin':
        return True

    # 获取用户完整信息
    user_info = db.fetch_one(
        "SELECT role_id FROM users WHERE id = ?",
        (user['user_id'],)
    )
    if not user_info:
        return False

    permissions = get_user_permissions(user_info['role_id'])
    resource_permissions = permissions.get(resource, [])

    return action in resource_permissions


def require_permission(resource: str, action: str):
    """需要特定权限"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not has_permission(user, resource, action):
                return jsonify({
                    'success': False,
                    'error': f'没有权限执行此操作 ({resource}:{action})'
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def log_exceptions(f):
    """
    异常日志装饰器

    自动捕获并记录 API 异常，包括：
    - 请求参数
    - 异常类型和消息
    - 堆栈追踪
    - 用户信息
    - 请求耗时
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        start_time = datetime.utcnow()
        user = get_current_user()
        user_id = user.get('user_id') if user else None

        try:
            return f(*args, **kwargs)
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000

            # 构建日志信息
            log_data = {
                'endpoint': request.path,
                'method': request.method,
                'user_id': user_id,
                'ip_address': request.remote_addr,
                'duration_ms': round(duration, 2),
                'exception_type': type(e).__name__,
                'exception_message': str(e),
                'traceback': traceback.format_exc()
            }

            # 记录请求参数（排除敏感信息）
            try:
                if request.is_json:
                    params = request.get_json()
                    # 脱敏
                    if isinstance(params, dict):
                        params = {k: '***' if k in ['password', 'token', 'auth_token'] else v
                                  for k, v in params.items()}
                    log_data['params'] = params
            except:
                pass

            # 记录错误日志
            logger.error(
                f"API异常: {request.method} {request.path} - {type(e).__name__}: {str(e)}",
                extra=log_data,
                exc_info=True
            )

            # 返回错误响应
            return jsonify({
                'success': False,
                'error': f'服务器错误: {str(e)}'
            }), 500

    return decorated


def log_operation(action: str, resource: str = None, resource_id_param: str = None):
    """
    操作日志装饰器

    用法:
        @log_operation('创建模型', 'model')
        def create_model():
            ...

        或获取动态 resource_id:
        @log_operation('删除模型', 'model', resource_id_param='model_id')
        def delete_model(model_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # 执行原函数
            result = f(*args, **kwargs)

            # 记录日志
            try:
                user = get_current_user()
                user_id = user.get('user_id') if user else None
                ip_address = request.remote_addr

                # 获取 resource_id
                resource_id = None
                if resource_id_param:
                    # 从 URL 参数获取
                    resource_id = kwargs.get(resource_id_param) or request.view_args.get(resource_id_param)

                db.insert('operation_logs', {
                    'user_id': user_id,
                    'action': action,
                    'resource': resource,
                    'resource_id': str(resource_id) if resource_id else None,
                    'details': None,
                    'ip_address': ip_address
                })
            except Exception:
                pass  # 日志记录失败不影响主流程

            return result
        return decorated
    return decorator


def log_operation_direct(action: str, resource: str = None, resource_id: str = None, details: str = None):
    """直接记录操作日志（非装饰器用法）"""
    user = get_current_user()
    user_id = user.get('user_id') if user else None
    ip_address = request.remote_addr

    db.insert('operation_logs', {
        'user_id': user_id,
        'action': action,
        'resource': resource,
        'resource_id': resource_id,
        'details': details,
        'ip_address': ip_address
    })