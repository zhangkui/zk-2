from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.config import settings, utc_now
from app.models import (
    InventoryItem, Material, InventoryStatus,
    Warning, WarningType, WarningStatus
)


def calculate_actual_expiry(inventory_item: InventoryItem) -> datetime:
    """计算实际失效时间 = min(原始有效期, 开封时间 + 开封后有效期)"""
    if (
        inventory_item.open_time
        and inventory_item.material
        and inventory_item.material.open_validity_days
    ):
        open_expiry = inventory_item.open_time + timedelta(
            days=inventory_item.material.open_validity_days
        )
        return min(inventory_item.original_expiry_date, open_expiry)
    return inventory_item.original_expiry_date


def is_expired(inventory_item: InventoryItem, now: datetime = None) -> bool:
    """判断是否已过期"""
    now = now or utc_now()
    return calculate_actual_expiry(inventory_item) <= now


def is_near_expiry(
    inventory_item: InventoryItem,
    days: int = None,
    now: datetime = None
) -> bool:
    """判断是否近效期"""
    days = days or settings.WARNING_DAYS_NEAR_EXPIRY
    now = now or utc_now()
    expiry = calculate_actual_expiry(inventory_item)
    return now < expiry <= now + timedelta(days=days)


def is_low_stock(inventory_item: InventoryItem) -> bool:
    """判断是否低库存"""
    if not inventory_item.material:
        return False
    return inventory_item.quantity <= inventory_item.material.min_stock


def can_use(inventory_item: InventoryItem, now: datetime = None) -> bool:
    """判断库存是否可以领用"""
    now = now or utc_now()
    if inventory_item.status in (InventoryStatus.SCRAPPED, InventoryStatus.USED_UP):
        return False
    if is_expired(inventory_item, now):
        return False
    if inventory_item.quantity <= 0:
        return False
    return True


def determine_status(inventory_item: InventoryItem, now: datetime = None) -> InventoryStatus:
    """根据当前状态和条件确定库存状态"""
    now = now or utc_now()

    if inventory_item.status == InventoryStatus.SCRAPPED:
        return InventoryStatus.SCRAPPED

    if inventory_item.quantity <= 0:
        return InventoryStatus.USED_UP

    if is_expired(inventory_item, now):
        return InventoryStatus.EXPIRED

    if is_near_expiry(inventory_item, now=now):
        if inventory_item.opened:
            return InventoryStatus.OPENED
        return InventoryStatus.NEAR_EXPIRY

    if is_low_stock(inventory_item):
        if inventory_item.opened:
            return InventoryStatus.OPENED
        return InventoryStatus.LOW_STOCK

    if inventory_item.opened:
        return InventoryStatus.OPENED

    return InventoryStatus.NORMAL


def check_and_create_warnings(db: Session, inventory_item: InventoryItem, now: datetime = None):
    """检查并创建预警"""
    now = now or utc_now()
    material = inventory_item.material

    if is_expired(inventory_item, now):
        _create_warning_if_not_exists(
            db, inventory_item, WarningType.EXPIRED,
            f"物料 [{material.name}] 批次 [{inventory_item.batch_no}] 已过期，失效日期：{calculate_actual_expiry(inventory_item)}"
        )
    elif is_near_expiry(inventory_item, now=now):
        _create_warning_if_not_exists(
            db, inventory_item, WarningType.NEAR_EXPIRY,
            f"物料 [{material.name}] 批次 [{inventory_item.batch_no}] 即将过期，失效日期：{calculate_actual_expiry(inventory_item)}"
        )

    if is_low_stock(inventory_item):
        _create_warning_if_not_exists(
            db, inventory_item, WarningType.LOW_STOCK,
            f"物料 [{material.name}] 批次 [{inventory_item.batch_no}] 库存不足，当前数量：{inventory_item.quantity} {material.unit}"
        )


def _create_warning_if_not_exists(
    db: Session,
    inventory_item: InventoryItem,
    warning_type: WarningType,
    message: str
):
    existing = db.query(Warning).filter(
        Warning.inventory_item_id == inventory_item.id,
        Warning.warning_type == warning_type,
        Warning.status == WarningStatus.ACTIVE
    ).first()

    if not existing:
        warning = Warning(
            warning_type=warning_type,
            inventory_item_id=inventory_item.id,
            message=message,
            status=WarningStatus.ACTIVE
        )
        db.add(warning)


def resolve_warnings_for_status_change(
    db: Session,
    inventory_item: InventoryItem,
    now: datetime = None
):
    """当状态改变时，解除不再需要的预警"""
    now = now or utc_now()

    warnings = db.query(Warning).filter(
        Warning.inventory_item_id == inventory_item.id,
        Warning.status == WarningStatus.ACTIVE
    ).all()

    for warning in warnings:
        should_resolve = False
        if warning.warning_type == WarningType.EXPIRED and not is_expired(inventory_item, now):
            should_resolve = True
        elif warning.warning_type == WarningType.NEAR_EXPIRY and not is_near_expiry(inventory_item, now=now):
            should_resolve = True
        elif warning.warning_type == WarningType.LOW_STOCK and not is_low_stock(inventory_item):
            should_resolve = True

        if should_resolve:
            warning.status = WarningStatus.RESOLVED
            warning.handled_at = now
            warning.handled_remark = "状态自动解除"


def scan_all_warnings(db: Session):
    """定时扫描所有库存，更新状态并创建预警"""
    now = utc_now()
    items = db.query(InventoryItem).filter(
        InventoryItem.status != InventoryStatus.SCRAPPED
    ).all()

    for item in items:
        item.status = determine_status(item, now)
        resolve_warnings_for_status_change(db, item, now)
        check_and_create_warnings(db, item, now)

    db.commit()
