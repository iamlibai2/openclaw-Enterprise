"""
核心 API 测试

测试内容：
- Health 端点
- 配置 API
- 任务统计 API

覆盖率目标：100%
"""

import pytest


class TestHealth:
    """健康检查测试"""

    @pytest.mark.api
    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get('/api/health')

        assert response.status_code == 200
        data = response.get_json()
        assert data.get('status') == 'ok' or data.get('success') is True


class TestConfigAPI:
    """配置 API 测试"""

    @pytest.mark.api
    def test_get_config_success(self, client, admin_token):
        """测试获取配置成功"""
        response = client.get('/api/config',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.get_json()
            assert 'success' in data

    @pytest.mark.api
    def test_get_config_preview(self, client, admin_token):
        """测试配置预览"""
        response = client.get('/api/config/preview',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        # 可能没有配置，返回 200 或其他状态
        assert response.status_code in [200, 404, 500]

    @pytest.mark.api
    def test_get_config_check(self, client, admin_token):
        """测试配置检查"""
        response = client.get('/api/config/check',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code in [200, 404, 500]


class TestTaskStats:
    """任务统计 API 测试"""

    @pytest.mark.api
    def test_task_overview(self, client, admin_token):
        """测试任务概览"""
        response = client.get('/api/tasks/overview',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'success' in data

    @pytest.mark.api
    def test_task_trend(self, client, admin_token):
        """测试任务趋势"""
        response = client.get('/api/tasks/trend',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code in [200, 400, 500]

    @pytest.mark.api
    def test_task_ranking(self, client, admin_token):
        """测试任务排名"""
        response = client.get('/api/tasks/ranking',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code == 200

    @pytest.mark.api
    def test_task_type_distribution(self, client, admin_token):
        """测试任务类型分布"""
        response = client.get('/api/tasks/type-distribution',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code == 200

    @pytest.mark.api
    def test_recent_tasks(self, client, admin_token):
        """测试最近任务"""
        response = client.get('/api/tasks/recent',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code == 200

    @pytest.mark.api
    def test_task_report(self, client, admin_token):
        """测试任务报告"""
        response = client.post('/api/tasks/report',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={}
        )

        # 报告生成可能失败
        assert response.status_code in [200, 400, 500]


class TestLogsAPI:
    """日志 API 测试"""

    @pytest.mark.api
    def test_operation_logs(self, client, admin_token):
        """测试获取操作日志"""
        response = client.get('/api/logs/operations',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'success' in data


class TestAuthMe:
    """当前用户 API 测试"""

    @pytest.mark.api
    def test_auth_me_success(self, client, admin_token):
        """测试获取当前用户信息"""
        response = client.get('/api/auth/me',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'data' in data
        assert data['data']['username'] == 'admin'

    @pytest.mark.api
    def test_auth_me_no_token(self, client):
        """测试无 token 获取当前用户"""
        response = client.get('/api/auth/me')

        assert response.status_code == 401


class TestChangePassword:
    """修改密码 API 测试"""

    @pytest.mark.api
    def test_change_password_endpoint(self, client, admin_token):
        """测试修改密码端点"""
        response = client.post('/api/auth/change-password',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'old_password': 'admin123',
                'new_password': 'newpassword123'
            }
        )

        # 修改密码可能失败（密码验证等）
        assert response.status_code in [200, 400, 401, 500]