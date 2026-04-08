"""
测试数据工厂

使用 factory_boy 生成测试数据
"""

import factory
from datetime import datetime, timedelta
import secrets


# Session 将在测试时动态设置
_factory_session = None

def set_factory_session(session):
    """设置 factory 使用的 session"""
    global _factory_session
    _factory_session = session


class RoleFactory(factory.Factory):
    """角色工厂"""
    class Meta:
        model = type('Role', (), {})

    name = factory.Sequence(lambda n: f'role_{n}')
    description = factory.Faker('sentence', nb_words=3)
    permissions = '{"users":["read"]}'
    created_at = factory.LazyFunction(datetime.utcnow)


class UserFactory(factory.Factory):
    """用户工厂"""
    class Meta:
        model = type('User', (), {})

    username = factory.Sequence(lambda n: f'user_{n}')
    password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA/7.J6LlZy'
    email = factory.LazyAttribute(lambda o: f'{o.username}@test.com')
    display_name = factory.Faker('name')
    role_id = 1
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class DepartmentFactory(factory.Factory):
    """部门工厂"""
    class Meta:
        model = type('Department', (), {})

    name = factory.Sequence(lambda n: f'部门_{n}')
    parent_id = None
    leader_id = None
    sort_order = factory.Sequence(lambda n: n)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class EmployeeFactory(factory.Factory):
    """员工工厂"""
    class Meta:
        model = type('Employee', (), {})

    name = factory.Faker('name', locale='zh_CN')
    email = factory.LazyAttribute(lambda o: f'{o.name.lower().replace(" ", ".")}@test.com')
    phone = factory.Faker('phone_number', locale='zh_CN')
    department_id = None
    manager_id = None
    agent_id = None
    user_id = None
    status = 'active'
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class GatewayFactory(factory.Factory):
    """Gateway 工厂"""
    class Meta:
        model = type('Gateway', (), {})

    name = factory.Sequence(lambda n: f'Gateway_{n}')
    url = factory.Sequence(lambda n: f'ws://127.0.0.1:1878{n}')
    auth_token = ''
    is_default = False
    status = 'unknown'
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class AgentProfileFactory(factory.Factory):
    """Agent 档案工厂"""
    class Meta:
        model = type('AgentProfile', (), {})

    agent_id = factory.Sequence(lambda n: f'agent_{n}')
    gender = factory.Faker('random_element', elements=['男', '女', '未知'])
    birthday = '2000-01-01'
    personality = '友好、专业、高效'
    total_conversations = 0
    total_tokens = 0
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class ScheduledTaskFactory(factory.Factory):
    """定时任务工厂"""
    class Meta:
        model = type('ScheduledTask', (), {})

    name = factory.Sequence(lambda n: f'任务_{n}')
    agent_id = factory.Sequence(lambda n: f'agent_{n}')
    task_type = 'schedule'
    task_params = '{}'
    interval_minutes = 60
    enabled = True
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class TaskExecutionFactory(factory.Factory):
    """任务执行记录工厂"""
    class Meta:
        model = type('TaskExecution', (), {})

    task_id = 1
    status = 'pending'
    is_read = False
    created_at = factory.LazyFunction(datetime.utcnow)


class TaskFactory(factory.Factory):
    """任务记录工厂"""
    class Meta:
        model = type('Task', (), {})

    agent_id = factory.Sequence(lambda n: f'agent_{n}')
    title = factory.Sequence(lambda n: f'任务标题_{n}')
    task_type = 'general'
    status = 'pending'
    created_at = factory.LazyFunction(datetime.utcnow)


class TemplateFactory(factory.Factory):
    """模板工厂"""
    class Meta:
        model = type('Template', (), {})

    template_id = factory.Sequence(lambda n: f'tpl_{n}')
    name = factory.Sequence(lambda n: f'模板_{n}')
    description = factory.Faker('sentence')
    file_type = 'json'
    content = '{}'
    is_builtin = False
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class OperationLogFactory(factory.Factory):
    """操作日志工厂"""
    class Meta:
        model = type('OperationLog', (), {})

    user_id = 1
    action = factory.Faker('random_element', elements=['create', 'update', 'delete', 'login', 'logout'])
    resource = 'users'
    resource_id = '1'
    details = '{}'
    ip_address = '127.0.0.1'
    created_at = factory.LazyFunction(datetime.utcnow)


class ModelProviderFactory(factory.Factory):
    """模型提供商工厂"""
    class Meta:
        model = type('ModelProvider', (), {})

    name = factory.Sequence(lambda n: f'provider_{n}')
    provider_type = factory.Faker('random_element', elements=['openai', 'anthropic', 'baidu'])
    api_key_encrypted = None
    api_base = None
    default_model = 'gpt-4'
    models = '[]'
    enabled = True
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class SystemSettingFactory(factory.Factory):
    """系统设置工厂"""
    class Meta:
        model = type('SystemSetting', (), {})

    key = factory.Sequence(lambda n: f'setting_{n}')
    value = 'test_value'
    value_type = 'string'
    description = '测试设置'
    category = 'general'
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class RefreshTokenFactory(factory.Factory):
    """刷新令牌工厂"""
    class Meta:
        model = type('RefreshToken', (), {})

    user_id = 1
    token_hash = factory.LazyFunction(lambda: secrets.token_hex(32))
    expires_at = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(days=7))
    created_at = factory.LazyFunction(datetime.utcnow)