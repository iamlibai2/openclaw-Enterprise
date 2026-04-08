"""
OpenClaw Control UI 后端测试配置

使用 pytest + PostgreSQL 测试数据库
"""

import pytest
import os
import sys

# 添加 backend 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database import Base, DATABASE_URL

# 测试数据库配置
TEST_DATABASE_URL = os.getenv(
    'TEST_DATABASE_URL',
    'postgresql://openclawen:openclawen@localhost:5432/openclawen_test'
)


# ============================================================================
# Fixtures: 数据库
# ============================================================================

@pytest.fixture(scope='session')
def db_engine():
    """
    Session 级别的数据库引擎
    在所有测试开始前创建表，测试结束后删除
    """
    # 创建测试数据库引擎
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    yield engine

    # 清理：使用 CASCADE 删除（PostgreSQL 会自动处理外键）
    with engine.connect() as conn:
        # 获取所有表名并逐个删除
        for table in reversed(Base.metadata.sorted_tables):
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table.name} CASCADE"))
            except Exception:
                pass
        conn.commit()
    engine.dispose()


@pytest.fixture(scope='function')
def db_session(db_engine):
    """
    Function 级别的数据库 Session
    每个测试函数使用独立的事务，测试结束后回滚
    """
    # 创建连接和事务
    connection = db_engine.connect()
    transaction = connection.begin()

    # 创建 Session
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    # 清理：回滚事务，关闭连接
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope='function')
def clean_db(db_engine):
    """
    清空数据库（用于需要干净状态的测试）
    """
    connection = db_engine.connect()
    # 按依赖顺序清空表
    tables = [
        'task_executions',
        'scheduled_tasks',
        'image_generation_history',
        'agent_profiles',
        'employees',
        'departments',
        'operation_logs',
        'refresh_tokens',
        'users',
        'roles',
        'templates',
        'tasks',
        'gateways',
        'models',
        'channel_configs',
        'model_providers',
        'system_settings',
    ]
    for table in tables:
        try:
            connection.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        except Exception:
            pass  # 表可能不存在
    connection.commit()
    connection.close()
    yield db_engine


# ============================================================================
# Fixtures: 测试客户端
# ============================================================================

@pytest.fixture
def app(db_session):
    """创建测试 Flask 应用"""
    from app import app as flask_app
    from database import db as global_db

    # 配置测试环境
    flask_app.config['TESTING'] = True
    flask_app.config['DATABASE_URL'] = TEST_DATABASE_URL

    # 使用测试 session（不会被关闭）
    global_db.set_test_session(db_session)

    yield flask_app

    # 清理：清除测试 session
    global_db.clear_test_session()


@pytest.fixture
def client(app):
    """Flask 测试客户端"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLI 测试运行器"""
    return app.test_cli_runner()


# ============================================================================
# Fixtures: 认证
# ============================================================================

@pytest.fixture
def auth_headers(client, db_session):
    """
    获取认证 headers
    返回一个函数，可以获取指定用户的认证 headers
    """
    def _get_auth_headers(user_id=1, username='admin'):
        # 直接生成 token
        from auth import generate_tokens
        access_token, _ = generate_tokens(user_id, username, 'admin')
        return {'Authorization': f'Bearer {access_token}'}

    return _get_auth_headers


@pytest.fixture
def admin_token(db_session, admin_user):
    """管理员用户的 access token"""
    from auth import generate_tokens
    token, _ = generate_tokens(admin_user.id, admin_user.username, 'admin')
    return token


# ============================================================================
# Fixtures: 默认数据
# ============================================================================

@pytest.fixture
def default_roles(db_session):
    """创建默认角色"""
    from database import Role

    roles = [
        Role(name='admin', description='系统管理员', permissions='{"users":["read","write"]}'),
        Role(name='operator', description='运维人员', permissions='{"users":["read"]}'),
        Role(name='viewer', description='查看者', permissions='{"users":["read"]}'),
    ]

    for role in roles:
        db_session.add(role)
    db_session.commit()

    return roles


@pytest.fixture
def admin_user(db_session, default_roles):
    """创建管理员用户"""
    from database import User
    from auth import hash_password

    # 确保角色已存在
    from database import Role
    admin_role = db_session.query(Role).filter(Role.name == 'admin').first()
    if not admin_role:
        admin_role = Role(name='admin', description='系统管理员', permissions='{"users":["read","write"]}')
        db_session.add(admin_role)
        db_session.commit()

    user = User(
        username='admin',
        password_hash=hash_password('admin123'),
        email='admin@test.com',
        display_name='管理员',
        role_id=admin_role.id,
        is_active=True
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)  # 获取自动生成的 id

    return user


@pytest.fixture
def test_department(db_session):
    """创建测试部门"""
    from database import Department

    dept = Department(
        name='测试部门',
        sort_order=0
    )

    db_session.add(dept)
    db_session.commit()
    db_session.refresh(dept)  # 获取自动生成的 id

    return dept


# ============================================================================
# pytest 配置
# ============================================================================

def pytest_configure(config):
    """pytest 配置"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )