"""清理残留预占数据并修复数据库"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from sqlalchemy import text


def fix_data():
    db = SessionLocal()
    try:
        print("清理孤立的预占记录...")
        # 找出没有关联申请单且未释放的预占记录
        orphan_reservations = db.execute(text("""
            SELECT r.id, r.inventory_item_id, r.quantity 
            FROM stock_reservations r 
            WHERE r.requisition_id IS NULL AND r.is_released = 0
        """)).fetchall()

        for res in orphan_reservations:
            print(f"  清理预占记录 ID={res[0]}, 库存ID={res[1]}, 数量={res[2]}")
            # 释放库存的预占数量
            db.execute(text(f"""
                UPDATE inventory_items 
                SET reserved_quantity = MAX(0, reserved_quantity - {res[2]})
                WHERE id = {res[1]}
            """))
            # 标记预占记录为已释放
            db.execute(text(f"""
                UPDATE stock_reservations 
                SET is_released = 1, released_at = CURRENT_TIMESTAMP, release_remark = '清理孤立数据'
                WHERE id = {res[0]}
            """))

        db.commit()

        print("\n验证修复结果:")
        items = db.execute(text("SELECT id, batch_no, quantity, reserved_quantity FROM inventory_items")).fetchall()
        for item in items:
            print(f"  库存 {item[1]}: 实际={item[2]}, 预占={item[3]}, 可用={item[2] - item[3]}")

        print("\n数据修复完成！")

    except Exception as e:
        print(f"修复失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    fix_data()
