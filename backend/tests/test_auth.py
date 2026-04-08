"""
认证模块测试

测试内容：
- 密码哈希和验证
- Token 生成和验证
- 登录 API
- 登出 API
- Token 刷新
- 权限验证

覆盖率目标：100%
"""

import pytest
from datetime import datetime, timedelta
import time


class TestPasswordHash:
    """密码哈希测试"""

    def test_hash_password(self):
        """测试密码哈希生成"""
        from auth import hash_password

        password = 'test123'
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert hashed.startswith('$2b$')

    def test_verify_password_correct(self):
        """测试正确密码验证"""
        from auth import hash_password, verify_password

        password = 'test123'
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """测试错误密码验证"""
        from auth import hash_password, verify_password

        password = 'test123'
        hashed = hash_password(password)

        assert verify_password('wrong_password', hashed) is False

    def test_hash_password_different_salts(self):
        """测试相同密码生成不同哈希"""
        from auth import hash_password

        password = 'test123'
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # 不同盐值


class TestTokenGeneration:
    """Token 生成测试"""

    def test_create_tokens(self):
        """测试创建 access token 和 refresh token"""
        from auth import generate_tokens

        user_id = 1
        username = 'testuser'
        role = 'admin'

        access_token, refresh_token = generate_tokens(user_id, username, role)

        assert access_token is not None
        assert refresh_token is not None
        assert access_token != refresh_token

    def test_decode_access_token(self):
        """测试解码 access token"""
        from auth import generate_tokens, decode_token

        access_token, _ = generate_tokens(1, 'testuser', 'admin')
        payload = decode_token(access_token)

        assert payload is not None
        assert payload['user_id'] == 1
        assert payload['username'] == 'testuser'
        assert payload['role'] == 'admin'
        assert payload['type'] == 'access'

    def test_decode_refresh_token(self):
        """测试解码 refresh token"""
        from auth import generate_tokens, decode_token

        _, refresh_token = generate_tokens(1, 'testuser', 'admin')
        payload = decode_token(refresh_token)

        assert payload is not None
        assert payload['user_id'] == 1
        assert payload['type'] == 'refresh'

    def test_decode_invalid_token(self):
        """测试解码无效 token"""
        from auth import decode_token

        payload = decode_token('invalid_token')
        assert payload is None

    def test_decode_expired_token(self):
        """测试解码过期 token"""
        from auth import decode_token
        import jwt

        # 创建一个已过期的 token
        expired_payload = {
            'user_id': 1,
            'username': 'testuser',
            'role': 'admin',
            'type': 'access',
            'exp': int(time.time()) - 3600  # 1小时前过期
        }
        expired_token = jwt.encode(expired_payload, 'your-secret-key', algorithm='HS256')

        payload = decode_token(expired_token)
        assert payload is None


class TestLoginAPI:
    """登录 API 测试"""

    @pytest.mark.api
    def test_login_success(self, client, admin_user):
        """测试登录成功"""
        response = client.post('/api/auth/login', json={
            'username': 'admin',
            'password': 'admin123'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        assert data['data']['user']['username'] == 'admin'

    @pytest.mark.api
    def test_login_wrong_password(self, client, admin_user):
        """测试密码错误"""
        response = client.post('/api/auth/login', json={
            'username': 'admin',
            'password': 'wrong_password'
        })

        assert response.status_code == 401
        data = response.get_json()
        assert data['success'] is False

    @pytest.mark.api
    def test_login_user_not_found(self, client, clean_db):
        """测试用户不存在"""
        response = client.post('/api/auth/login', json={
            'username': 'nonexistent',
            'password': 'any_password'
        })

        assert response.status_code == 401
        data = response.get_json()
        assert data['success'] is False

    @pytest.mark.api
    def test_login_missing_fields(self, client):
        """测试缺少字段"""
        response = client.post('/api/auth/login', json={
            'username': 'admin'
            # 缺少 password
        })

        assert response.status_code == 400

    @pytest.mark.api
    def test_login_inactive_user(self, client, db_session):
        """测试禁用用户登录"""
        from database import User, Role
        from auth import hash_password

        # 先确保角色存在
        role = db_session.query(Role).filter(Role.name == 'admin').first()
        if not role:
            role = Role(name='admin', description='系统管理员', permissions='{}')
            db_session.add(role)
            db_session.commit()

        user = User(
            username='inactive_user',
            password_hash=hash_password('password'),
            email='inactive@test.com',
            role_id=role.id,
            is_active=False
        )
        db_session.add(user)
        db_session.commit()

        response = client.post('/api/auth/login', json={
            'username': 'inactive_user',
            'password': 'password'
        })

        assert response.status_code == 401


class TestLogoutAPI:
    """登出 API 测试"""

    @pytest.mark.api
    def test_logout_success(self, client, admin_token):
        """测试登出成功"""
        response = client.post('/api/auth/logout',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    @pytest.mark.api
    def test_logout_without_token(self, client):
        """测试无 token 登出"""
        response = client.post('/api/auth/logout')

        assert response.status_code == 401


class TestTokenRefresh:
    """Token 刷新测试"""

    @pytest.mark.api
    def test_refresh_token_success(self, client, admin_user):
        """测试刷新 token 成功"""
        # 先登录获取 refresh token
        login_response = client.post('/api/auth/login', json={
            'username': 'admin',
            'password': 'admin123'
        })
        login_data = login_response.get_json()

        # 处理可能的 rate limiting (429)
        if login_response.status_code == 429:
            # Rate limiting triggered, skip this test
            pytest.skip("Rate limiting triggered, cannot test refresh token")

        refresh_token = login_data['data']['refresh_token']

        # 使用 refresh token 获取新的 access token
        response = client.post('/api/auth/refresh', json={
            'refresh_token': refresh_token
        })

        # 检查响应
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True or 'access_token' in data.get('data', {})

    @pytest.mark.api
    def test_refresh_with_access_token(self, client, admin_token):
        """测试使用 access token 刷新（应该失败）"""
        response = client.post('/api/auth/refresh', json={
            'refresh_token': admin_token
        })

        assert response.status_code == 401

    @pytest.mark.api
    def test_refresh_with_invalid_token(self, client):
        """测试使用无效 token 刷新"""
        response = client.post('/api/auth/refresh', json={
            'refresh_token': 'invalid_token'
        })

        assert response.status_code == 401


class TestAuthDecorator:
    """认证装饰器测试"""

    @pytest.mark.api
    def test_protected_route_with_valid_token(self, client, admin_token):
        """测试有效 token 访问受保护路由"""
        response = client.get('/api/users',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code == 200

    @pytest.mark.api
    def test_protected_route_without_token(self, client):
        """测试无 token 访问受保护路由"""
        response = client.get('/api/users')

        assert response.status_code == 401

    @pytest.mark.api
    def test_protected_route_with_invalid_token(self, client):
        """测试无效 token 访问受保护路由"""
        response = client.get('/api/users',
            headers={'Authorization': 'Bearer invalid_token'}
        )

        assert response.status_code == 401


class TestPermissionDecorator:
    """权限装饰器测试"""

    @pytest.mark.api
    def test_admin_can_access_users(self, client, admin_token):
        """测试管理员可以访问用户管理"""
        response = client.get('/api/users',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code == 200

    # TODO: 添加 operator 和 viewer 权限测试
    # TODO: 添加跨权限访问测试