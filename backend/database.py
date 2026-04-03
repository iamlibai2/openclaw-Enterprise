"""
SQLite 数据库管理
"""
import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any


class Database:
    """SQLite 数据库管理器"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            # 数据库存储在项目目录下 backend/data/admin.db
            self.db_path = Path(__file__).parent / "data" / "admin.db"

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """初始化数据库表"""
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = self._get_connection()
        cursor = conn.cursor()

        # 创建角色表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) UNIQUE NOT NULL,
                description VARCHAR(200),
                permissions TEXT NOT NULL DEFAULT '{}',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(200) NOT NULL,
                email VARCHAR(100) UNIQUE,
                display_name VARCHAR(100),
                role_id INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                last_login DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (role_id) REFERENCES roles(id)
            )
        """)

        # 创建 refresh_tokens 表（用于 Token 刷新）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash VARCHAR(200) NOT NULL,
                expires_at DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 创建操作日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action VARCHAR(50) NOT NULL,
                resource VARCHAR(100),
                resource_id VARCHAR(50),
                details TEXT,
                ip_address VARCHAR(50),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 创建任务表（用于仪表盘统计）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                task_type VARCHAR(50),
                status VARCHAR(20) DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                completed_at DATETIME,
                duration_seconds INTEGER,
                deliverable_type VARCHAR(50),
                deliverable_path VARCHAR(500),
                user_id VARCHAR(100),
                session_id VARCHAR(100),
                details TEXT
            )
        """)

        # 创建模板表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                description VARCHAR(500),
                file_type VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                is_builtin BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建部门表（支持多层级）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                parent_id INTEGER,
                leader_id INTEGER,
                sort_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES departments(id),
                FOREIGN KEY (leader_id) REFERENCES employees(id)
            )
        """)

        # 创建员工表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100),
                phone VARCHAR(20),
                avatar VARCHAR(500),
                department_id INTEGER,
                manager_id INTEGER,
                agent_id VARCHAR(50),
                user_id INTEGER,
                status VARCHAR(20) DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (department_id) REFERENCES departments(id),
                FOREIGN KEY (manager_id) REFERENCES employees(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 创建 Gateway 配置表（支持多 Gateway）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gateways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                url VARCHAR(500) NOT NULL,
                auth_token VARCHAR(500),
                is_default BOOLEAN DEFAULT 0,
                status VARCHAR(20) DEFAULT 'unknown',
                last_connected_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建模型配置表（用于模型管理）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                provider VARCHAR(50) NOT NULL,
                model_type VARCHAR(20) DEFAULT 'chat',
                api_key_encrypted TEXT,
                api_base VARCHAR(500),
                model_name VARCHAR(100) NOT NULL,
                parameters TEXT,
                enabled BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建渠道配置表（用于飞书/钉钉等渠道配置）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channel_configs (
                id TEXT PRIMARY KEY,
                channel_type VARCHAR(50) NOT NULL,
                config_encrypted TEXT,
                enabled BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

        # 初始化默认角色和管理员账户
        self._init_default_data()

        # 初始化默认部门
        self._init_default_departments()

        # 初始化默认 Gateway
        self._init_default_gateways()

    def _init_default_data(self) -> None:
        """初始化默认角色和管理员账户"""
        from auth import hash_password

        conn = self._get_connection()
        cursor = conn.cursor()

        # 检查是否已有角色
        cursor.execute("SELECT COUNT(*) FROM roles")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return

        # 插入默认角色
        default_roles = [
            {
                'name': 'admin',
                'description': '系统管理员，拥有所有权限',
                'permissions': '{"agents":["read","write","delete"],"bindings":["read","write","delete"],"tools":["read","write"],"models":["read"],"status":["read"],"sessions":["read"],"logs":["read"],"config":["read","write"],"security":["read","write"],"users":["read","write","delete"],"roles":["read","write"],"gateway":["start","stop","restart","reload"],"skills":["read","write","delete"],"employees":["read","write","delete"]}'
            },
            {
                'name': 'operator',
                'description': '运维人员，可管理 Agent 和绑定',
                'permissions': '{"agents":["read","write"],"bindings":["read","write"],"tools":["read"],"models":["read"],"status":["read"],"sessions":["read"],"logs":["read"],"config":["read"],"gateway":["start","stop","restart","reload"],"skills":["read","write"],"employees":["read"]}'
            },
            {
                'name': 'viewer',
                'description': '查看者，只读权限',
                'permissions': '{"agents":["read"],"bindings":["read"],"tools":["read"],"models":["read"],"status":["read"],"sessions":["read"],"logs":["read"],"config":["read"],"skills":["read"],"employees":["read"]}'
            }
        ]

        for role in default_roles:
            cursor.execute(
                "INSERT INTO roles (name, description, permissions) VALUES (?, ?, ?)",
                (role['name'], role['description'], role['permissions'])
            )

        conn.commit()

        # 更新已有角色的权限（添加 employees 和 gateway 权限）
        role_permissions_updates = {
            'admin': '{"agents":["read","write","delete"],"bindings":["read","write","delete"],"tools":["read","write"],"models":["read"],"status":["read"],"sessions":["read"],"logs":["read"],"config":["read","write"],"security":["read","write"],"users":["read","write","delete"],"roles":["read","write"],"gateway":["start","stop","restart","reload","write","delete"],"skills":["read","write","delete"],"employees":["read","write","delete"]}',
            'operator': '{"agents":["read","write"],"bindings":["read","write"],"tools":["read"],"models":["read"],"status":["read"],"sessions":["read"],"logs":["read"],"config":["read"],"gateway":["start","stop","restart","reload"],"skills":["read","write"],"employees":["read"]}',
            'viewer': '{"agents":["read"],"bindings":["read"],"tools":["read"],"models":["read"],"status":["read"],"sessions":["read"],"logs":["read"],"config":["read"],"skills":["read"],"employees":["read"]}'
        }
        for role_name, permissions in role_permissions_updates.items():
            cursor.execute(
                "UPDATE roles SET permissions = ? WHERE name = ?",
                (permissions, role_name)
            )

        # 检查是否已有管理员
        cursor.execute("SELECT COUNT(*) FROM users WHERE role_id = 1")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return

        # 创建默认管理员账户
        admin_password_hash = hash_password('admin123')
        cursor.execute(
            """INSERT INTO users
               (username, password_hash, email, display_name, role_id, is_active)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ('admin', admin_password_hash, 'admin@openclaw.local', '系统管理员', 1, 1)
        )

        conn.commit()
        conn.close()

        print(f"[Database] 初始化完成，数据库路径: {self.db_path}")
        print(f"[Database] 默认管理员: admin / admin123")

    def _init_default_departments(self) -> None:
        """初始化默认部门"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 检查是否已有部门
        cursor.execute("SELECT COUNT(*) FROM departments")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return

        # 插入默认部门结构（三层）
        default_departments = [
            {'name': 'OpenClaw 公司', 'parent_id': None, 'sort_order': 0},
            {'name': '技术部', 'parent_id': None, 'sort_order': 1},  # 临时，后面更新
            {'name': '产品部', 'parent_id': None, 'sort_order': 2},
        ]

        for dept in default_departments:
            cursor.execute(
                "INSERT INTO departments (name, parent_id, sort_order) VALUES (?, ?, ?)",
                (dept['name'], dept['parent_id'], dept['sort_order'])
            )

        # 更新技术部和产品部的 parent_id 为公司ID
        cursor.execute("UPDATE departments SET parent_id = 1 WHERE name IN ('技术部', '产品部')")

        # 添加子部门
        sub_departments = [
            {'name': '研发一组', 'parent_name': '技术部', 'sort_order': 0},
            {'name': '研发二组', 'parent_name': '技术部', 'sort_order': 1},
            {'name': '产品一组', 'parent_name': '产品部', 'sort_order': 0},
        ]

        for dept in sub_departments:
            cursor.execute("SELECT id FROM departments WHERE name = ?", (dept['parent_name'],))
            parent = cursor.fetchone()
            if parent:
                cursor.execute(
                    "INSERT INTO departments (name, parent_id, sort_order) VALUES (?, ?, ?)",
                    (dept['name'], parent[0], dept['sort_order'])
                )

        conn.commit()
        conn.close()
        print(f"[Database] 默认部门初始化完成")

    def _init_default_gateways(self) -> None:
        """初始化默认 Gateway"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 检查是否已有 Gateway
        cursor.execute("SELECT COUNT(*) FROM gateways")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return

        # 插入默认 Gateway（本地 Gateway）
        cursor.execute(
            """INSERT INTO gateways (name, url, auth_token, is_default, status)
               VALUES (?, ?, ?, ?, ?)""",
            ('本地 Gateway', 'ws://127.0.0.1:18789', '', 1, 'unknown')
        )

        conn.commit()
        conn.close()
        print(f"[Database] 默认 Gateway 初始化完成")

    def execute(self, query: str, params: tuple = ()) -> Any:
        """执行 SQL 语句"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        result = cursor.lastrowid
        conn.close()
        return result

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """查询单条记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """查询多条记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def insert(self, table: str, data: Dict) -> int:
        """插入记录"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return self.execute(query, tuple(data.values()))

    def update(self, table: str, data: Dict, where: str, where_params: tuple = ()) -> int:
        """更新记录"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        params = tuple(data.values()) + where_params
        return self.execute(query, params)

    def delete(self, table: str, where: str, where_params: tuple = ()) -> int:
        """删除记录"""
        query = f"DELETE FROM {table} WHERE {where}"
        return self.execute(query, where_params)


# 全局数据库实例
db = Database()