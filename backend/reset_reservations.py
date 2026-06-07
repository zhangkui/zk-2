"""强制重置所有预占数据"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print("重置所有库存的 reserved_quantity = 0")
    db.execute(text("UPDATE inventory_items SET reserved_quantity = 0"))
    print("删除所有 stock_reservations 记录")
    db.execute(text("DELETE FROM stock_reservations"))
    print("删除所有 requisition_items 记录")
    db.execute(text("DELETE FROM requisition_items"))
    print("删除所有 requisitions 记录")
    db.execute(text("DELETE FROM requisitions"))
    print("删除相关操作记录 (reserve/release_reserve/approve_requisition/reject_requisition)")
    db.execute(text("""
        DELETE FROM inventory_operations 
        WHERE operation_type IN ('reserve', 'release_reserve', 'approve_requisition', 'reject_requisition')
    """))
    db.commit()
    print("\n数据已完全重置！")

    items = db.execute(text("SELECT id, batch_no, quantity, reserved_quantity FROM inventory_items")).fetchall()
    for item in items:
        print(f"  库存 {item[1]}: 实际={item[2]}, 预占={item[3]}, 可用={item[2] - item[3]}")
except Exception as e:
    print(f"错误: {e}")
    db.rollback()
finally:
    db.close()
