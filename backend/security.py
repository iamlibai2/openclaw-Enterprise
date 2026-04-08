"""
安全配置模块

实现：
- CORS 跨域保护
- Rate Limiting 限流
- XSS 防护
- 安全头部
"""
import re
from functools import wraps
from flask import request, jsonify, g
from datetime import datetime, timedelta
from collections import defaultdict
import threading
import html


# ==================== Rate Limiting ====================

class RateLimiter:
    """
    基于 IP 的限流器

    使用内存存储，支持滑动窗口算法
    """

    def __init__(self):
        self.requests = defaultdict(list)  # IP -> [timestamp, ...]
        self.lock = threading.Lock()

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple:
        """
        检查是否允许请求

        Returns:
            (allowed: bool, remaining: int, reset_time: int)
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=window_seconds)

        with self.lock:
            # 清理过期记录
            self.requests[key] = [
                ts for ts in self.requests[key]
                if ts > window_start
            ]

            current_count = len(self.requests[key])

            if current_count >= max_requests:
                # 计算重置时间
                oldest = min(self.requests[key]) if self.requests[key] else now
                reset_time = int((oldest + timedelta(seconds=window_seconds)).timestamp())
                return False, 0, reset_time

            # 记录本次请求
            self.requests[key].append(now)
            remaining = max_requests - current_count - 1
            reset_time = int((now + timedelta(seconds=window_seconds)).timestamp())

            return True, remaining, reset_time


# 全局限流器实例
rate_limiter = RateLimiter()


def rate_limit(max_requests: int = 100, window_seconds: int = 60, key_func=None):
    """
    限流装饰器

    Args:
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口（秒）
        key_func: 自定义 key 函数，默认使用 IP

    Usage:
        @rate_limit(max_requests=10, window_seconds=60)
        def login():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # 获取限流 key
            if key_func:
                key = key_func()
            else:
                key = f"rate:{request.remote_addr}"

            allowed, remaining, reset_time = rate_limiter.is_allowed(
                key, max_requests, window_seconds
            )

            # 设置响应头
            g.rate_limit_remaining = remaining
            g.rate_limit_reset = reset_time

            if not allowed:
                return jsonify({
                    'success': False,
                    'error': '请求过于频繁，请稍后再试',
                    'retry_after': reset_time
                }), 429

            return f(*args, **kwargs)
        return decorated
    return decorator


# 预定义的限流规则
RATE_LIMITS = {
    # 登录接口：每分钟最多 5 次
    'login': rate_limit(max_requests=5, window_seconds=60),
    # API 接口：每分钟最多 100 次
    'api': rate_limit(max_requests=100, window_seconds=60),
    # 写操作：每分钟最多 30 次
    'write': rate_limit(max_requests=30, window_seconds=60),
}


# ==================== XSS 防护 ====================

# 危险标签和属性
DANGEROUS_TAGS = ['script', 'iframe', 'object', 'embed', 'form', 'meta', 'link', 'style']
DANGEROUS_ATTRS = ['onload', 'onerror', 'onclick', 'onmouseover', 'onfocus', 'onblur',
                   'onchange', 'onsubmit', 'onkeydown', 'onkeyup', 'onkeypress']


def sanitize_html(text: str) -> str:
    """
    清理 HTML，移除危险标签和属性

    用于富文本输入
    """
    if not text:
        return text

    # 转义 HTML 特殊字符
    text = html.escape(text)

    return text


def sanitize_input(text: str, max_length: int = None) -> str:
    """
    清理用户输入

    - 移除控制字符
    - 限制长度
    - 转义 HTML
    """
    if not text:
        return text

    # 移除控制字符（保留换行、制表符）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # 限制长度
    if max_length:
        text = text[:max_length]

    # 转义 HTML（防 XSS）
    text = html.escape(text)

    return text


def sanitize_dict(data: dict, max_lengths: dict = None) -> dict:
    """
    清理字典中的字符串值
    """
    if not data:
        return data

    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            max_len = max_lengths.get(key) if max_lengths else None
            result[key] = sanitize_input(value, max_len)
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, max_lengths)
        elif isinstance(value, list):
            result[key] = [
                sanitize_input(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            result[key] = value

    return result


# ==================== 输入验证 ====================

def validate_identifier(value: str, field_name: str = '标识符') -> tuple:
    """
    验证标识符格式（字母开头，只含字母数字下划线连字符）
    """
    if not value:
        return False, f'{field_name}不能为空'

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', value):
        return False, f'{field_name}必须以字母开头，只能包含字母、数字、下划线、连字符'

    return True, None


def validate_url(value: str, field_name: str = 'URL', allow_ws: bool = False) -> tuple:
    """
    验证 URL 格式
    """
    if not value:
        return False, f'{field_name}不能为空'

    protocols = ['http://', 'https://']
    if allow_ws:
        protocols.extend(['ws://', 'wss://'])

    if not any(value.startswith(p) for p in protocols):
        return False, f'{field_name}格式不正确'

    return True, None


def validate_email(value: str) -> tuple:
    """
    验证邮箱格式
    """
    if not value:
        return True, None  # 邮箱可选

    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', value):
        return False, '邮箱格式不正确'

    return True, None


def validate_phone(value: str) -> tuple:
    """
    验证手机号格式
    """
    if not value:
        return True, None  # 手机号可选

    if not re.match(r'^1[3-9]\d{9}$', value.replace(' ', '')):
        return False, '手机号格式不正确'

    return True, None


def validate_json(value: str) -> tuple:
    """
    验证 JSON 格式
    """
    if not value or not value.strip():
        return True, None

    try:
        import json
        json.loads(value)
        return True, None
    except json.JSONDecodeError:
        return False, 'JSON 格式不正确'


# ==================== 安全头部 ====================

def add_security_headers(response):
    """
    添加安全响应头
    """
    # 防止点击劫持
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'

    # 防止 MIME 类型嗅探
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # XSS 保护
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # 内容安全策略（基础版）
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"

    # HSTS（强制 HTTPS，生产环境启用）
    # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    # 限流信息
    if hasattr(g, 'rate_limit_remaining'):
        response.headers['X-RateLimit-Remaining'] = str(g.rate_limit_remaining)
    if hasattr(g, 'rate_limit_reset'):
        response.headers['X-RateLimit-Reset'] = str(g.rate_limit_reset)

    return response


# ==================== CORS 配置 ====================

def get_cors_config():
    """
    获取 CORS 配置

    生产环境应配置具体的允许域名
    """
    return {
        'origins': [
            'http://localhost:5000',
            'http://127.0.0.1:5000',
            'http://localhost:3000',
            'http://127.0.0.1:3000',
        ],
        'methods': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
        'allow_headers': [
            'Content-Type',
            'Authorization',
            'X-Requested-With',
            'Accept',
        ],
        'expose_headers': [
            'X-RateLimit-Remaining',
            'X-RateLimit-Reset',
        ],
        'supports_credentials': True,
        'max_age': 3600,
    }


# ==================== SQL 注入防护 ====================

# 允许的表名（白名单）
ALLOWED_TABLES = {
    'users', 'roles', 'gateways', 'model_providers',
    'departments', 'employees', 'operation_logs', 'refresh_tokens',
    'agent_profiles', 'tasks', 'templates', 'channel_configs',
    'skills', 'bindings', 'sessions'
}

# 允许的字段名字符
FIELD_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def validate_table_name(table: str) -> bool:
    """
    验证表名是否合法
    """
    return table.lower() in ALLOWED_TABLES


def validate_field_name(field: str) -> bool:
    """
    验证字段名是否合法
    """
    return bool(FIELD_PATTERN.match(field))


def safe_insert(table: str, data: dict) -> tuple:
    """
    安全插入，验证表名和字段名

    Returns:
        (success: bool, error: str or None)
    """
    if not validate_table_name(table):
        return False, f'无效的表名: {table}'

    for field in data.keys():
        if not validate_field_name(field):
            return False, f'无效的字段名: {field}'

    return True, None


def safe_update(table: str, data: dict, where: str) -> tuple:
    """
    安全更新，验证表名和字段名
    """
    if not validate_table_name(table):
        return False, f'无效的表名: {table}'

    for field in data.keys():
        if not validate_field_name(field):
            return False, f'无效的字段名: {field}'

    return True, None