"""
PostgreSQL 连接和 Session 管理
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

# 数据库连接配置
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://openclawen:openclawen@localhost:5432/openclaw_en'
)

# 创建引擎（连接池）
engine = create_engine(
    DATABASE_URL,
    pool_size=5,          # 连接池大小
    max_overflow=10,      # 最大溢出连接数
    pool_pre_ping=True,   # 连接前检查可用性
    echo=False            # 不打印 SQL（调试时可设为 True）
)

# Session 工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Session:
    """
    获取数据库 Session（用于依赖注入）
    """
    db = SessionLocal()
    try:
        return db
    finally:
        # 注意：调用者需要负责关闭
        pass


@contextmanager
def db_session():
    """
    上下文管理器，自动关闭 Session
    用法：
        with db_session() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    初始化数据库（创建所有表）
    """
    from database import Base
    Base.metadata.create_all(bind=engine)
    print("[db_session] 数据库表创建完成")


# 全局 db 实例（兼容旧代码，逐步替换）
_db_instance = None

def get_db_instance():
    """
    获取全局 db 实例（用于兼容旧代码）
    """
    global _db_instance
    if _db_instance is None:
        from database import DatabaseCompat
        _db_instance = DatabaseCompat()
    return _db_instance


# 导出兼容旧代码的 db 变量
db = None  # 在 database.py 中设置