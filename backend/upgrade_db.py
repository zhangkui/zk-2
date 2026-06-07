"""
数据库升级脚本
为已存在的数据库添加库存预占和领用申请相关的字段和表
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal
from app.config import settings
from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade_database():
    print(f"正在升级数据库: {settings.DATABASE_URL}")
    db = SessionLocal()
    try:
        print("1. 检查并添加 inventory_items.reserved_quantity 字段...")
        result = db.execute(text("PRAGMA table_info(inventory_items)")).fetchall()
        columns = [row[1] for row in result]
        if 'reserved_quantity' not in columns:
            db.execute(text("ALTER TABLE inventory_items ADD COLUMN reserved_quantity FLOAT NOT NULL DEFAULT 0"))
            db.commit()
            print("   -> reserved_quantity 字段已添加")
        else:
            print("   -> reserved_quantity 字段已存在，跳过")

        print("2. 检查并创建 stock_reservations 表...")
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='stock_reservations'")).fetchone()
        if not result:
            db.execute(text("""
                CREATE TABLE stock_reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inventory_item_id INTEGER NOT NULL,
                    quantity FLOAT NOT NULL,
                    requisition_id INTEGER,
                    operator_id INTEGER NOT NULL,
                    remark TEXT,
                    created_at DATETIME,
                    released_at DATETIME,
                    released_by INTEGER,
                    release_remark TEXT,
                    is_released BOOLEAN NOT NULL DEFAULT 0,
                    FOREIGN KEY (inventory_item_id) REFERENCES inventory_items (id),
                    FOREIGN KEY (requisition_id) REFERENCES requisitions (id),
                    FOREIGN KEY (operator_id) REFERENCES users (id),
                    FOREIGN KEY (released_by) REFERENCES users (id)
                )
            """))
            db.commit()
            print("   -> stock_reservations 表已创建")
        else:
            print("   -> stock_reservations 表已存在，跳过")

        print("3. 检查并创建 requisitions 表...")
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='requisitions'")).fetchone()
        if not result:
            db.execute(text("""
                CREATE TABLE requisitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    requisition_no VARCHAR(50) NOT NULL UNIQUE,
                    title VARCHAR(200) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    applicant_id INTEGER NOT NULL,
                    apply_remark TEXT,
                    created_at DATETIME,
                    approved_by INTEGER,
                    approved_at DATETIME,
                    approve_remark TEXT,
                    rejected_by INTEGER,
                    rejected_at DATETIME,
                    reject_remark TEXT,
                    cancelled_by INTEGER,
                    cancelled_at DATETIME,
                    cancel_remark TEXT,
                    FOREIGN KEY (applicant_id) REFERENCES users (id),
                    FOREIGN KEY (approved_by) REFERENCES users (id),
                    FOREIGN KEY (rejected_by) REFERENCES users (id),
                    FOREIGN KEY (cancelled_by) REFERENCES users (id)
                )
            """))
            db.commit()
            print("   -> requisitions 表已创建")
        else:
            print("   -> requisitions 表已存在，跳过")

        print("4. 检查并创建 requisition_items 表...")
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='requisition_items'")).fetchone()
        if not result:
            db.execute(text("""
                CREATE TABLE requisition_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    requisition_id INTEGER NOT NULL,
                    inventory_item_id INTEGER NOT NULL,
                    material_id INTEGER NOT NULL,
                    quantity FLOAT NOT NULL,
                    actual_outbound_quantity FLOAT,
                    remark TEXT,
                    FOREIGN KEY (requisition_id) REFERENCES requisitions (id),
                    FOREIGN KEY (inventory_item_id) REFERENCES inventory_items (id),
                    FOREIGN KEY (material_id) REFERENCES materials (id)
                )
            """))
            db.commit()
            print("   -> requisition_items 表已创建")
        else:
            print("   -> requisition_items 表已存在，跳过")

        print("5. 为 requisitions 表创建索引...")
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_requisitions_no ON requisitions(requisition_no)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_requisitions_status ON requisitions(status)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_requisitions_applicant ON requisitions(applicant_id)"))
        db.commit()

        print("\n数据库升级完成！")

    except Exception as e:
        print(f"\n升级失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    upgrade_database()
