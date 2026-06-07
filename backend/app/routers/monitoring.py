from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import csv
from io import StringIO
from fastapi.responses import StreamingResponse

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.config import utc_now
from app.models import (
    InventoryOperation, OperationType, Warning,
    WarningType, WarningStatus, User, UserRole,
    StocktakeTask, StocktakeTaskStatus, StocktakeItem, StocktakeItemStatus,
    Requisition, RequisitionStatus, InventoryItem
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
    stocktake_task_id: Optional[int] = Query(None),
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
    if stocktake_task_id:
        query = query.filter(InventoryOperation.stocktake_task_id == stocktake_task_id)

    operations = query.order_by(
        InventoryOperation.operation_time.desc()
    ).limit(limit).all()
    for op in operations:
        op.operator
    return operations


@router.get("/operations/export-diff")
def export_operations_diff(
    stocktake_task_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    if not stocktake_task_id:
        raise HTTPException(status_code=400, detail="请指定盘点任务ID")

    task = db.query(StocktakeTask).filter(StocktakeTask.id == stocktake_task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="盘点任务不存在")

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "盘点任务编号", "盘点任务名称",
        "物料编码", "物料名称", "规格型号", "批次号", "单位",
        "快照数量", "当前数量", "实盘数量", "差异数量",
        "快照状态", "当前状态",
        "盘点执行人", "盘点执行时间",
        "复核确认人", "复核确认时间",
        "盘点备注"
    ])

    for st_item in task.items:
        inv = st_item.inventory_item
        if not inv:
            continue
        mat = inv.material
        actual_qty = st_item.actual_quantity if st_item.actual_quantity is not None else ""
        diff = (st_item.actual_quantity - st_item.snapshot_quantity) if st_item.actual_quantity is not None else ""

        submitter_name = ""
        if st_item.submitter:
            submitter_name = st_item.submitter.full_name
        confirmer_name = ""
        if st_item.confirmer:
            confirmer_name = st_item.confirmer.full_name

        writer.writerow([
            task.task_no,
            task.title,
            mat.code if mat else "",
            mat.name if mat else "",
            mat.specification if mat else "",
            inv.batch_no,
            mat.unit if mat else "",
            st_item.snapshot_quantity,
            inv.quantity,
            actual_qty,
            diff,
            st_item.snapshot_status.value,
            inv.status.value,
            submitter_name,
            st_item.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if st_item.submitted_at else "",
            confirmer_name,
            st_item.confirmed_at.strftime("%Y-%m-%d %H:%M:%S") if st_item.confirmed_at else "",
            st_item.remark or ""
        ])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f"attachment; filename=stocktake_diff_details_{task.task_no}.csv"
        }
    )


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
    warning.handled_at = utc_now()
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
    now = utc_now()
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

    ongoing_stocktake_tasks = db.query(StocktakeTask).filter(
        StocktakeTask.status.in_([
            StocktakeTaskStatus.DRAFT,
            StocktakeTaskStatus.IN_PROGRESS,
            StocktakeTaskStatus.PENDING_REVIEW
        ])
    ).count()

    pending_tasks = db.query(StocktakeTask).filter(
        StocktakeTask.status == StocktakeTaskStatus.PENDING_REVIEW
    ).all()
    pending_review_diffs = 0
    for task in pending_tasks:
        for st_item in task.items:
            if st_item.actual_quantity is not None and st_item.actual_quantity != st_item.snapshot_quantity:
                pending_review_diffs += 1

    pending_requisitions = db.query(Requisition).filter(
        Requisition.status == RequisitionStatus.PENDING
    ).count()

    total_reserved_qty = db.query(InventoryItem).filter(
        InventoryItem.reserved_quantity > 0
    ).all()
    total_reserved_quantity = sum(item.reserved_quantity for item in total_reserved_qty)

    return DashboardStats(
        total_materials=total_materials,
        total_inventory=total_inventory,
        total_warnings=total_warnings,
        near_expiry_count=near_expiry_count,
        expired_count=expired_count,
        low_stock_count=low_stock_count,
        total_operations_today=total_operations_today,
        ongoing_stocktake_tasks=ongoing_stocktake_tasks,
        pending_review_diffs=pending_review_diffs,
        pending_requisitions=pending_requisitions,
        total_reserved_quantity=total_reserved_quantity
    )
