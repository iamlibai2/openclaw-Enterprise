"""
数据库迁移：添加 agent_config 字段

执行方式：
    python migrate_agent_config.py

说明：
    agent_ids 字段保持不变（绑定关系）
    agent_config 字段新增（能力配置偏好）
"""

import json
from database import engine, SessionLocal
from sqlalchemy import text


def migrate():
    session = SessionLocal()
    try:
        # 1. 检查是否已有 agent_config 列
        result = session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'employees' AND column_name = 'agent_config'
        """))

        if result.fetchone():
            print("[迁移] agent_config 列已存在，跳过创建")
            return

        # 2. 添加 agent_config 列（JSON 类型）
        print("[迁移] 添加 agent_config 列...")
        session.execute(text("""
            ALTER TABLE employees ADD COLUMN agent_config JSONB
        """))
        session.commit()
        print("[迁移] agent_config 列创建成功")

        # 3. 为现有员工设置默认配置
        print("[迁移] 设置默认配置...")
        employees = session.execute(text("""
            SELECT id, agent_ids FROM employees WHERE agent_ids IS NOT NULL
        """)).fetchall()

        for emp_id, agent_ids in employees:
            # 默认配置
            default_config = {
                "autonomy": "high",
                "report_style": {
                    "detail_level": "summary",
                    "timing": "on_complete"
                },
                "learning": {
                    "remember_feedback": True,
                    "auto_improve": True
                }
            }

            session.execute(text("""
                UPDATE employees SET agent_config = :config WHERE id = :id
            """), {'config': json.dumps(default_config), 'id': emp_id})

        session.commit()
        print(f"[迁移] 已为 {len(employees)} 个员工设置默认配置")

        print("[迁移] 完成！")

    except Exception as e:
        session.rollback()
        print(f"[迁移] 错误: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    migrate()