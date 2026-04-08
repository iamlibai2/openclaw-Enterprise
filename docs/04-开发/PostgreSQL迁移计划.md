# PostgreSQL 迁移计划（SQLite → PostgreSQL + SQLAlchemy）

> 文档创建时间：2026-04-05
> 状态：待执行

---

## 一、Context

### 需求

将现有 SQLite 数据库迁移到 PostgreSQL，使用 SQLAlchemy ORM。

### 原因

- 企业级应用需要更健壮的数据库支持
- 预期未来需求：数据量增长、多实例部署、高并发写入
- 尽早迁移避免后期风险

### 现状分析

| 项目 | 数据 |
|------|------|
| 数据库文件 | `backend/data/admin.db` |
| 表数量 | 13 个（不含动态创建） |
| 使用数据库的文件 | 15 个 |
| 数据库调用次数 | 约 200+ 处 |

### 表清单

| 表名 | 说明 |
|------|------|
| `roles` | 角色 |
| `users` | 用户 |
| `refresh_tokens` | Token 刷新 |
| `operation_logs` | 操作日志 |
| `tasks` | 任务记录 |
| `templates` | 模板 |
| `departments` | 部门 |
| `employees` | 呡工 |
| `gateways` | Gateway 配置 |
| `models` | 模型配置 |
| `channel_configs` | 渠道配置 |
| `agent_profiles` | Agent 档案 |
| `scheduled_tasks` | 定时任务 |
| `task_executions` | 任务执行记录 |
| `model_providers` | 模型提供商（动态创建） |
| `image_generation_history` | 图片生成历史（动态创建） |
| `system_settings` | 系统设置（动态创建） |

---

## 二、技术方案

### 方案选择：SQLAlchemy ORM

**优势**：

- 数据库抽象，未来迁移更容易
- 连接池自动管理
- 类型安全，代码更清晰
- 支持复杂查询和关系

### 架构设计

```
backend/
├── database.py          # SQLAlchemy 模型定义（重写）
├── db_session.py        # 新增：Session 和连接管理
├── repositories/        # 可选：数据访问层封装
│   ├── __init__.py
│   ├── user_repo.py
│   ├── task_repo.py
│   └── ...
└── *.py                  # 逐步替换 db.fetch_*/db.execute 调用
```

### 连接配置

```python
# db_session.py
DATABASE_URL = os.getenv('DATABASE_URL',
    'postgresql://openclaw:openclaw123@localhost:5432/openclaw_control')

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine)
```

---

## 三、实现步骤

### Step 0: 环境准备（用户执行）

```bash
# 1. 安装 PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# 2. 启动服务
sudo service postgresql start

# 3. 创建数据库和用户
sudo -u postgres psql -c "CREATE USER openclaw WITH PASSWORD 'openclaw123';"
sudo -u postgres psql -c "CREATE DATABASE openclaw_control OWNER openclaw;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE openclaw_control TO openclaw;"
```

### Step 1: 安装 Python 依赖

```bash
source /home/iamlibai/workspace/python_env_common/bin/activate
cd backend
uv pip install sqlalchemy psycopg2-binary
```

### Step 2: 创建 SQLAlchemy 模型

**文件**: `backend/database.py`（重写）

```python
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

Base = declarative_base()

class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    permissions = Column(Text, default='{}')
    created_at = Column(DateTime, default=datetime.utcnow)
    users = relationship('User', back_populates='role')

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    email = Column(String(100), unique=True)
    display_name = Column(String(100))
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    role = relationship('Role', back_populates='users')

# ... 其他模型
```

### Step 3: 创建 Session 管理

**文件**: `backend/db_session.py`（新增）

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
import os

DATABASE_URL = os.getenv('DATABASE_URL',
    'postgresql://openclaw:openclaw123@localhost:5432/openclaw_control')

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
```

### Step 4: 创建 Repository 层（可选但推荐）

为高频使用的表创建 Repository，简化调用：

**文件**: `backend/repositories/user_repo.py`

```python
from sqlalchemy.orm import Session
from database import User, Role

class UserRepo:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str) -> User | None:
        return self.db.query(User).filter(User.username == username).first()

    def create(self, user_data: dict) -> User:
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    # ... 其他方法
```

### Step 5: 逐步替换调用

**改动策略**：按文件逐个替换，优先级：

| 优先级 | 文件 | 改动量 | 说明 |
|--------|------|--------|------|
| P0 | `app.py` | ~150处 | 主应用，核心逻辑 |
| P1 | `auth.py` | ~2处 | 认证逻辑 |
| P1 | `decorators.py` | ~4处 | 权限装饰器 |
| P1 | `tasks/scheduler.py` | ~5处 | 定时任务调度 |
| P1 | `tasks/executor.py` | ~6处 | 任务执行 |
| P2 | `events/router.py` | ~8处 | 事件路由 |
| P2 | `events/listener.py` | ~1处 | 事件监听 |
| P2 | `agent_profile.py` | ~6处 | Agent 档案 |
| P2 | `gateway_sync.py` | ~4处 | Gateway 同步 |
| P3 | 其他 | ~20处 | 辅助模块 |

**替换示例**：

```python
# 原代码
user = db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))

# 新代码
user = db.query(User).filter(User.id == user_id).first()
```

```python
# 原代码
db.insert('users', {'username': 'test', 'password_hash': 'xxx', 'role_id': 1})

# 新代码
user = User(username='test', password_hash='xxx', role_id=1)
db.add(user)
db.commit()
```

### Step 6: 初始化数据库

运行初始化脚本创建表和默认数据：

```python
# backend/init_postgres.py
from db_session import init_db, SessionLocal
from database import Role, User
from auth import hash_password

init_db()

db = SessionLocal()
# 创建默认角色和管理员
if db.query(Role).count() == 0:
    # ... 初始化逻辑
db.close()
```

### Step 7: 数据迁移（如有现有数据）

如果 SQLite 有重要数据，需要迁移：

```python
# backend/migrate_data.py
# 1. 从 SQLite 导出数据
# 2. 导入到 PostgreSQL
```

---

## 四、文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| **重写** | `backend/database.py` | SQLAlchemy 模型定义 |
| **新增** | `backend/db_session.py` | Session 和连接管理 |
| **新增** | `backend/repositories/__init__.py` | Repository 入口 |
| **新增** | `backend/repositories/user_repo.py` | 用户 Repository |
| **新增** | `backend/repositories/task_repo.py` | 任务 Repository |
| **新增** | `backend/init_postgres.py` | 数据库初始化脚本 |
| **修改** | `backend/app.py` | 替换数据库调用 (~150处) |
| **修改** | `backend/auth.py` | 替换数据库调用 |
| **修改** | `backend/decorators.py` | 替换数据库调用 |
| **修改** | `backend/tasks/*.py` | 替换数据库调用 |
| **修改** | `backend/events/*.py` | 替换数据库调用 |
| **修改** | `backend/agent_profile.py` | 替换数据库调用 |
| **修改** | `backend/gateway_sync.py` | 替换数据库调用 |
| **修改** | 其他使用 db 的文件 | 替换数据库调用 |
| **删除** | `backend/data/admin.db` | 迁移后删除 SQLite 文件 |
| **新增** | `.env` 或环境配置 | DATABASE_URL |

---

## 五、验证方法

### 功能验证

1. 登录功能：admin/admin123 能正常登录
2. 用户管理：创建、编辑、删除用户
3. 部门管理：多层级部门 CRUD
4. 任务管理：定时任务创建和执行记录
5. Gateway 管理：多 Gateway 配置

### 性能验证

1. 连接池：多请求并发，检查连接复用
2. 查询性能：大数据量查询响应时间

### 数据验证

1. 数据完整性：迁移后数据一致
2. 关系正确：外键关联正常

---

## 六、风险和注意事项

### SQL 语法差异

| SQLite | PostgreSQL | 处理方式 |
|---------|------------|---------|
| `?` 参数 | `$1, $2` 或命名参数 | SQLAlchemy 自动处理 |
| `DATETIME` | `TIMESTAMP` | 模型中使用 DateTime |
| `BOOLEAN 1/0` | `BOOLEAN true/false` | SQLAlchemy 自动处理 |
| `AUTOINCREMENT` | `SERIAL` | SQLAlchemy 自动处理 |

### 需要注意的点

1. **外键约束**：PostgreSQL 默认强制外键约束，删除时需先删除关联数据
2. **大小写敏感**：PostgreSQL 对字符串大小写敏感
3. **事务隔离**：PostgreSQL 事务隔离级别与 SQLite 不同
4. **动态创建的表**：`model_providers`、`image_generation_history`、`system_settings` 在 app.py 中动态创建，需要改为模型定义

---

## 七、时间估算

| 步骤 | 预估时间 |
|------|---------|
| Step 1-3（基础架构） | 2-3 小时 |
| Step 4（Repository） | 2-3 小时 |
| Step 5（替换调用） | 4-6 小时 |
| Step 6-7（初始化和迁移） | 1-2 小时 |
| 测试验证 | 2-3 小时 |
| **总计** | **1-2 天** |

---

## 八、后续优化

迁移完成后可考虑：

1. 添加数据库备份策略
2. 添加连接池监控
3. 添加慢查询日志
4. 添加数据库迁移工具（Alembic）