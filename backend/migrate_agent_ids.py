"""
数据库迁移：agent_id -> agent_ids (支持多选)

运行方式：
    python migrate_agent_ids.py
"""
import json
from database import SessionLocal, engine
from sqlalchemy import text

def migrate():
    """执行迁移"""
    session = SessionLocal()

    try:
        # 1. 检查是否已有 agent_ids 列
        result = session.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'employees' AND column_name = 'agent_ids'
        """))
        if result.fetchone():
            print("[迁移] agent_ids 列已存在，跳过创建")
        else:
            # 2. 添加 agent_ids 列
            print("[迁移] 添加 agent_ids 列...")
            session.execute(text("""
                ALTER TABLE employees ADD COLUMN agent_ids TEXT
            """))
            session.commit()
            print("[迁移] agent_ids 列创建成功")

        # 3. 迁移数据：agent_id -> agent_ids
        print("[迁移] 迁移数据...")
        employees = session.execute(text("""
            SELECT id, agent_id, agent_ids FROM employees
        """)).fetchall()

        for emp in employees:
            emp_id = emp[0]
            old_agent_id = emp[1]
            new_agent_ids = emp[2]

            # 如果 agent_ids 为空但 agent_id 有值，则迁移
            if not new_agent_ids and old_agent_id:
                agent_ids_json = json.dumps([old_agent_id])
                session.execute(text("""
                    UPDATE employees SET agent_ids = :agent_ids WHERE id = :id
                """), {'agent_ids': agent_ids_json, 'id': emp_id})
                print(f"  - 员工 {emp_id}: {old_agent_id} -> {agent_ids_json}")

        session.commit()
        print("[迁移] 数据迁移完成")

        # 4. 删除旧列（可选，保留兼容）
        # session.execute(text("ALTER TABLE employees DROP COLUMN agent_id"))
        # session.commit()
        # print("[迁移] 已删除旧 agent_id 列")

        print("\n[迁移] 全部完成！")

    except Exception as e:
        session.rollback()
        print(f"[迁移] 错误: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    migrate()