"""
SQLAlchemy 数据库模型定义

从 SQLite 迁移到 PostgreSQL，使用 SQLAlchemy ORM。
原有表结构保持不变，新增 ORM 模型定义。
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey,
    create_engine, select, update, delete, insert
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session, sessionmaker
from sqlalchemy.pool import QueuePool

import os

# ============================================================================
# SQLAlchemy Base 和模型定义
# ============================================================================

Base = declarative_base()


class Role(Base):
    """角色表"""
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    permissions = Column(Text, nullable=False, default='{}')
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    users = relationship('User', back_populates='role')


class User(Base):
    """用户表"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    email = Column(String(100), unique=True)
    display_name = Column(String(100))
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    role = relationship('Role', back_populates='users')
    refresh_tokens = relationship('RefreshToken', back_populates='user', cascade='all, delete-orphan')


class RefreshToken(Base):
    """刷新令牌表"""
    __tablename__ = 'refresh_tokens'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token_hash = Column(String(200), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship('User', back_populates='refresh_tokens')


class OperationLog(Base):
    """操作日志表"""
    __tablename__ = 'operation_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(String(50), nullable=False)
    resource = Column(String(100))
    resource_id = Column(String(50))
    details = Column(Text)
    ip_address = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    """任务表"""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    task_type = Column(String(50))
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)
    deliverable_type = Column(String(50))
    deliverable_path = Column(String(500))
    user_id = Column(String(100))
    session_id = Column(String(100))
    details = Column(Text)


class Template(Base):
    """模板表"""
    __tablename__ = 'templates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    file_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    is_builtin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Department(Base):
    """部门表（支持多层级）"""
    __tablename__ = 'departments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey('departments.id'))
    leader_id = Column(Integer, ForeignKey('employees.id'))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    parent = relationship('Department', remote_side=[id], back_populates='children')
    children = relationship('Department', back_populates='parent')
    employees = relationship('Employee', foreign_keys='Employee.department_id', back_populates='department')
    leader = relationship('Employee', foreign_keys=[leader_id], post_update=True)


class Employee(Base):
    """员工表"""
    __tablename__ = 'employees'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100))
    phone = Column(String(20))
    avatar = Column(String(500))
    department_id = Column(Integer, ForeignKey('departments.id'))
    manager_id = Column(Integer, ForeignKey('employees.id'))
    agent_id = Column(String(50))
    user_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系（明确指定 foreign_keys）
    department = relationship('Department', foreign_keys=[department_id], back_populates='employees')
    manager = relationship('Employee', remote_side=[id], foreign_keys=[manager_id], back_populates='subordinates')
    subordinates = relationship('Employee', foreign_keys=[manager_id], back_populates='manager')


class Gateway(Base):
    """Gateway 配置表"""
    __tablename__ = 'gateways'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    auth_token = Column(String(500))
    is_default = Column(Boolean, default=False)
    status = Column(String(20), default='unknown')
    last_connected_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Model(Base):
    """模型配置表"""
    __tablename__ = 'models'

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)
    model_type = Column(String(20), default='chat')
    api_key_encrypted = Column(Text)
    api_base = Column(String(500))
    model_name = Column(String(100), nullable=False)
    parameters = Column(Text)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChannelConfig(Base):
    """渠道配置表"""
    __tablename__ = 'channel_configs'

    id = Column(String(50), primary_key=True)
    channel_type = Column(String(50), nullable=False)
    config_encrypted = Column(Text)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentProfile(Base):
    """Agent 扩展档案表（拟人化属性）"""
    __tablename__ = 'agent_profiles'

    agent_id = Column(String(50), primary_key=True)

    # 拟人化属性
    gender = Column(String(20))
    birthday = Column(String(10))
    age_display = Column(String(20))
    personality = Column(Text)
    hobbies = Column(Text)
    voice_style = Column(String(50))

    # 扩展属性
    custom_fields = Column(Text)

    # 统计
    total_conversations = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # 备注
    admin_notes = Column(Text)
    tags = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScheduledTask(Base):
    """定时任务表"""
    __tablename__ = 'scheduled_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    agent_id = Column(String(50), nullable=False)
    task_type = Column(String(50), nullable=False)
    task_params = Column(Text)
    cron_expr = Column(String(50))
    interval_minutes = Column(Integer)
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime)
    next_run_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    executions = relationship('TaskExecution', back_populates='task', cascade='all, delete-orphan')


class TaskExecution(Base):
    """任务执行记录表"""
    __tablename__ = 'task_executions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('scheduled_tasks.id'), nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    result = Column(Text)
    error_message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    task = relationship('ScheduledTask', back_populates='executions')


class ModelProvider(Base):
    """模型提供商表"""
    __tablename__ = 'model_providers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    provider_type = Column(String(50), nullable=False)
    api_key_encrypted = Column(Text)
    api_base = Column(String(500))
    default_model = Column(String(100))
    models = Column(Text)  # JSON 格式的模型列表
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ImageGenerationHistory(Base):
    """图片生成历史表"""
    __tablename__ = 'image_generation_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    prompt = Column(Text, nullable=False)
    model = Column(String(100))
    image_url = Column(String(500))
    image_path = Column(String(500))
    width = Column(Integer)
    height = Column(Integer)
    style = Column(String(50))
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemSetting(Base):
    """系统设置表"""
    __tablename__ = 'system_settings'

    key = Column(String(100), primary_key=True)
    value = Column(Text)
    value_type = Column(String(20), default='string')  # string, int, float, bool, json
    description = Column(String(500))
    category = Column(String(50), default='general')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# 数据库连接和 Session 管理
# ============================================================================

# 数据库连接配置
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://openclawen:openclawen@localhost:5432/openclaw_en'
)

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False
)

# Session 工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_session() -> Session:
    """获取数据库 Session"""
    return SessionLocal()


def init_db():
    """初始化数据库表"""
    Base.metadata.create_all(bind=engine)
    print("[Database] PostgreSQL 表创建完成")


# ============================================================================
# 兼容旧代码的 Database 类（逐步替换）
# ============================================================================

class DatabaseCompat:
    """
    兼容旧 SQLite 代码风格的 Database 类
    使用 SQLAlchemy Session 实现，保持接口不变

    用法：
        from database import db
        user = db.fetch_one("SELECT * FROM users WHERE id = ?", (1,))

    注意：这是过渡方案，最终应全部改为 ORM 方式
    """

    def __init__(self):
        self._session = None
        self._test_mode = False  # 测试模式标志
        # 兼容旧代码中的 db_path 属性
        self.db_path = f"PostgreSQL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}"

    def set_test_session(self, session: Session):
        """设置测试 session（用于 pytest）"""
        self._session = session
        self._test_mode = True

    def clear_test_session(self):
        """清除测试 session"""
        self._session = None
        self._test_mode = False

    def _get_session(self) -> Session:
        """获取或创建 Session"""
        if self._session is None:
            self._session = SessionLocal()
        return self._session

    def _close_session(self):
        """关闭 Session（测试模式下不关闭）"""
        if self._test_mode:
            return  # 测试模式下不关闭 session
        if self._session:
            self._session.close()
            self._session = None

    def _convert_params(self, query: str, params: tuple) -> tuple:
        """
        将 SQLite 风格的 ? 占位符和元组参数转换为 SQLAlchemy 的命名参数格式
        例如：("SELECT * FROM users WHERE id = ?", (1,))
        转换为：("SELECT * FROM users WHERE id = :param0", {"param0": 1})

        同时处理 SQLite 到 PostgreSQL 的语法差异：
        - BOOLEAN 比较：= 1 → = true, = 0 → = false
        - LIMIT 语法兼容

        返回：(new_query, param_dict)
        """
        if not params:
            # 即使没有参数，也需要处理布尔转换
            new_query = query
            # SQLite 布尔比较转换为 PostgreSQL
            new_query = new_query.replace('= 1', '= true')
            new_query = new_query.replace('= 0', '= false')
            new_query = new_query.replace('=1', '= true')
            new_query = new_query.replace('=0', '= false')
            return new_query, {}

        # 替换 ? 为 :param0, :param1, ...
        param_dict = {}
        new_query = query
        for i, value in enumerate(params):
            param_name = f"param{i}"
            new_query = new_query.replace("?", f":{param_name}", 1)
            param_dict[param_name] = value

        # SQLite 布尔比较转换为 PostgreSQL
        new_query = new_query.replace('= 1', '= true')
        new_query = new_query.replace('= 0', '= false')
        new_query = new_query.replace('=1', '= true')
        new_query = new_query.replace('=0', '= false')

        return new_query, param_dict

    def execute(self, query: str, params: tuple = ()) -> Any:
        """执行 SQL 语句"""
        session = self._get_session()
        try:
            from sqlalchemy import text
            new_query, param_dict = self._convert_params(query, params)
            result = session.execute(text(new_query), param_dict)
            session.commit()
            return result.lastrowid if result.lastrowid else result.rowcount
        except Exception as e:
            session.rollback()
            raise e

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """查询单条记录"""
        session = self._get_session()
        try:
            from sqlalchemy import text
            new_query, param_dict = self._convert_params(query, params)
            result = session.execute(text(new_query), param_dict)
            row = result.fetchone()
            if row:
                # 将 Row 对象转为字典
                return dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
            return None
        finally:
            self._close_session()

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """查询多条记录"""
        session = self._get_session()
        try:
            from sqlalchemy import text
            new_query, param_dict = self._convert_params(query, params)
            result = session.execute(text(new_query), param_dict)
            rows = result.fetchall()
            return [dict(row._mapping) if hasattr(row, '_mapping') else dict(row) for row in rows]
        finally:
            self._close_session()

    def insert(self, table: str, data: Dict) -> int:
        """插入记录"""
        session = self._get_session()
        try:
            # 处理布尔值：Python bool 转 PostgreSQL bool
            processed_data = {}
            for k, v in data.items():
                if isinstance(v, bool):
                    processed_data[k] = v
                elif isinstance(v, int) and k in ('is_active', 'enabled', 'is_default', 'is_builtin', 'is_read'):
                    # 常见的布尔字段
                    processed_data[k] = bool(v)
                else:
                    processed_data[k] = v

            # 构建原始 SQL INSERT 语句
            columns = ', '.join(processed_data.keys())
            placeholders = ', '.join([f':{k}' for k in processed_data.keys()])
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            from sqlalchemy import text
            result = session.execute(text(sql), processed_data)
            session.commit()
            # PostgreSQL 使用 RETURNING 获取插入的 ID
            if result.lastrowid:
                return result.lastrowid
            # 尝试获取最后插入的 ID
            try:
                id_result = session.execute(text(f"SELECT currval(pg_get_serial_sequence('{table}', 'id'))"))
                return id_result.scalar()
            except:
                return 0
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self._close_session()

    def update(self, table: str, data: Dict, where: str, where_params: tuple = ()) -> int:
        """更新记录"""
        session = self._get_session()
        try:
            # 构建原始 SQL UPDATE 语句
            set_clause = ', '.join([f"{k} = :{k}" for k in data.keys()])
            new_where, where_param_dict = self._convert_params(where, where_params)
            # 合并参数
            all_params = {**data, **where_param_dict}
            sql = f"UPDATE {table} SET {set_clause} WHERE {new_where}"
            from sqlalchemy import text
            result = session.execute(text(sql), all_params)
            session.commit()
            return result.rowcount
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self._close_session()

    def delete(self, table: str, where: str, where_params: tuple = ()) -> int:
        """删除记录"""
        session = self._get_session()
        try:
            # 构建原始 SQL DELETE 语句
            new_where, param_dict = self._convert_params(where, where_params)
            sql = f"DELETE FROM {table} WHERE {new_where}"
            from sqlalchemy import text
            result = session.execute(text(sql), param_dict)
            session.commit()
            return result.rowcount
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self._close_session()


# 全局 db 实例（兼容旧代码）
db = DatabaseCompat()


# ============================================================================
# 初始化默认数据
# ============================================================================

def init_default_data():
    """初始化默认角色和管理员账户"""
    from auth import hash_password

    session = SessionLocal()
    try:
        # 检查是否已有角色
        if session.query(Role).count() > 0:
            return

        # 插入默认角色
        default_roles = [
            Role(
                name='admin',
                description='系统管理员，拥有所有权限',
                permissions='{"agents":["read","write","delete"],"bindings":["read","write","delete"],"tools":["read","write"],"models":["read"],"status":["read"],"sessions":["read"],"logs":["read"],"config":["read","write"],"security":["read","write"],"users":["read","write","delete"],"roles":["read","write"],"gateway":["start","stop","restart","reload","write","delete"],"skills":["read","write","delete"],"employees":["read","write","delete"],"tasks":["read","write","delete"]}'
            ),
            Role(
                name='operator',
                description='运维人员，可管理 Agent 和绑定',
                permissions='{"agents":["read","write"],"bindings":["read","write"],"tools":["read"],"models":["read"],"status":["read"],"sessions":["read"],"logs":["read"],"config":["read"],"gateway":["start","stop","restart","reload"],"skills":["read","write"],"employees":["read"],"tasks":["read","write"]}'
            ),
            Role(
                name='viewer',
                description='查看者，只读权限',
                permissions='{"agents":["read"],"bindings":["read"],"tools":["read"],"models":["read"],"status":["read"],"sessions":["read"],"logs":["read"],"config":["read"],"skills":["read"],"employees":["read"],"tasks":["read"]}'
            )
        ]

        for role in default_roles:
            session.add(role)

        session.commit()

        # 创建默认管理员账户
        admin_role = session.query(Role).filter(Role.name == 'admin').first()
        if admin_role and session.query(User).filter(User.role_id == admin_role.id).count() == 0:
            admin = User(
                username='admin',
                password_hash=hash_password('admin123'),
                email='admin@openclaw.local',
                display_name='系统管理员',
                role_id=admin_role.id,
                is_active=True
            )
            session.add(admin)
            session.commit()

        print("[Database] 默认数据初始化完成")
        print("[Database] 默认管理员: admin / admin123")

    finally:
        session.close()


def init_default_departments():
    """初始化默认部门"""
    session = SessionLocal()
    try:
        if session.query(Department).count() > 0:
            return

        # 创建默认部门结构
        company = Department(name='OpenClaw 公司', sort_order=0)
        session.add(company)
        session.flush()  # 获取 company.id

        tech_dept = Department(name='技术部', parent_id=company.id, sort_order=1)
        product_dept = Department(name='产品部', parent_id=company.id, sort_order=2)
        session.add_all([tech_dept, product_dept])
        session.flush()

        # 子部门
        session.add_all([
            Department(name='研发一组', parent_id=tech_dept.id, sort_order=0),
            Department(name='研发二组', parent_id=tech_dept.id, sort_order=1),
            Department(name='产品一组', parent_id=product_dept.id, sort_order=0),
        ])

        session.commit()
        print("[Database] 默认部门初始化完成")

    finally:
        session.close()


def init_default_gateways():
    """初始化默认 Gateway"""
    session = SessionLocal()
    try:
        if session.query(Gateway).count() > 0:
            return

        gateway = Gateway(
            name='本地 Gateway',
            url='ws://127.0.0.1:18789',
            auth_token='',
            is_default=True,
            status='unknown'
        )
        session.add(gateway)
        session.commit()
        print("[Database] 默认 Gateway 初始化完成")

    finally:
        session.close()


def init_all():
    """完整初始化"""
    init_db()
    init_default_data()
    init_default_departments()
    init_default_gateways()


# 自动初始化（如果表不存在）
if __name__ == '__main__':
    init_all()