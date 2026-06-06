from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models import (
    InventoryOperation, OperationType, Warning,
    WarningType, WarningStatus, User, UserRole
)
from app.schemas import (
    InventoryOperationResponse, WarningResponse, WarningHandleRequest,
    DashboardStats
)
from app.utils import is_expired, is_near_expiry, is_low_stock
from app.models import InventoryItem, Material

router = APIRouter(tags=["预警与操作记录"])


@router.get("/operations", response_model=List[InventoryOperationResponse])
def list_operations(
    operation_type: Optional[OperationType] = Query(None),
    operator_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(InventoryOperation)
    if operation_type:
        query = query.filter(InventoryOperation.operation_type == operation_type)
    if operator_id:
        query = query.filter(InventoryOperation.operator_id == operator_id)
    if start_date:
        query = query.filter(InventoryOperation.operation_time >= start_date)
    if end_date:
        query = query.filter(InventoryOperation.operation_time <= end_date)

    operations = query.order_by(
        InventoryOperation.operation_time.desc()
    ).limit(limit).all()
    for op in operations:
        op.operator
    return operations


@router.get("/warnings", response_model=List[WarningResponse])
def list_warnings(
    warning_type: Optional[WarningType] = Query(None),
    status: Optional[WarningStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Warning)
    if warning_type:
        query = query.filter(Warning.warning_type == warning_type)
    if status:
        query = query.filter(Warning.status == status)
    warnings = query.order_by(Warning.created_at.desc()).all()
    for w in warnings:
        w.inventory_item
        if w.inventory_item:
            w.inventory_item.material
    return warnings


@router.put("/warnings/{warning_id}", response_model=WarningResponse)
def handle_warning(
    warning_id: int,
    data: WarningHandleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    warning = db.query(Warning).filter(Warning.id == warning_id).first()
    if not warning:
        raise HTTPException(status_code=404, detail="预警不存在")

    warning.status = data.status
    warning.handled_at = datetime.utcnow()
    warning.handled_by = current_user.id
    warning.handled_remark = data.handled_remark

    db.commit()
    db.refresh(warning)
    return warning


@router.get("/warnings/scan")
def trigger_warning_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    from app.utils import scan_all_warnings
    scan_all_warnings(db)
    return {"message": "预警扫描已完成"}


@router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_materials = db.query(Material).filter(Material.is_active == True).count()
    total_inventory = db.query(InventoryItem).filter(
        InventoryItem.status != "scrapped"
    ).count()

    items = db.query(InventoryItem).all()
    near_expiry_count = 0
    expired_count = 0
    low_stock_count = 0

    for item in items:
        if item.status == "scrapped":
            continue
        if is_expired(item, now):
            expired_count += 1
        elif is_near_expiry(item, now=now):
            near_expiry_count += 1
        if is_low_stock(item):
            low_stock_count += 1

    total_warnings = db.query(Warning).filter(
        Warning.status == WarningStatus.ACTIVE
    ).count()

    total_operations_today = db.query(InventoryOperation).filter(
        InventoryOperation.operation_time >= today_start
    ).count()

    return DashboardStats(
        total_materials=total_materials,
        total_inventory=total_inventory,
        total_warnings=total_warnings,
        near_expiry_count=near_expiry_count,
        expired_count=expired_count,
        low_stock_count=low_stock_count,
        total_operations_today=total_operations_today
    )
