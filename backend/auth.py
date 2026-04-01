"""
JWT 认证和密码处理
"""
import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

# JWT 配置
JWT_SECRET_KEY = secrets.token_hex(32)  # 生产环境应从配置文件读取
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    """密码哈希"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def generate_tokens(user_id: int, username: str, role: str) -> Tuple[str, str]:
    """生成 access_token 和 refresh_token"""
    now = datetime.utcnow()

    # Access Token
    access_payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'type': 'access',
        'exp': now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        'iat': now
    }
    access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    # Refresh Token
    refresh_payload = {
        'user_id': user_id,
        'type': 'refresh',
        'exp': now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        'iat': now
    }
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    return access_token, refresh_token


def decode_token(token: str) -> Optional[Dict]:
    """解码 Token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_access_token(token: str) -> Optional[Dict]:
    """验证 Access Token"""
    payload = decode_token(token)
    if payload and payload.get('type') == 'access':
        return payload
    return None


def verify_refresh_token(token: str) -> Optional[int]:
    """验证 Refresh Token，返回 user_id"""
    payload = decode_token(token)
    if payload and payload.get('type') == 'refresh':
        return payload.get('user_id')
    return None


def refresh_access_token(refresh_token: str, db) -> Optional[str]:
    """使用 Refresh Token 刷新 Access Token"""
    user_id = verify_refresh_token(refresh_token)
    if not user_id:
        return None

    # 从数据库获取用户信息
    user = db.fetch_one(
        "SELECT u.id, u.username, u.is_active, r.name as role_name "
        "FROM users u JOIN roles r ON u.role_id = r.id WHERE u.id = ?",
        (user_id,)
    )

    if not user or not user['is_active']:
        return None

    # 生成新的 Access Token
    now = datetime.utcnow()
    access_payload = {
        'user_id': user['id'],
        'username': user['username'],
        'role': user['role_name'],
        'type': 'access',
        'exp': now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        'iat': now
    }
    access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    return access_token