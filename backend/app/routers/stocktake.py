from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import csv
from io import StringIO
from fastapi.responses import StreamingResponse

from app.database import get_db
from app.deps import require_roles, get_current_user
from app.config import utc_now
from app.models import (
    StocktakeTask, StocktakeTaskStatus, StocktakeItem, StocktakeItemStatus,
    InventoryItem, Material, InventoryStatus,
    InventoryOperation, OperationType, User, UserRole
)
from app.schemas import (
    StocktakeTaskCreate, StocktakeTaskResponse, StocktakeItemResponse,
    StocktakeItemUpdate, StocktakeTaskCloseRequest, StocktakeBatchUpdateRequest,
    InventoryItemResponse
)
from app.utils import (
    determine_status, check_and_create_warnings, resolve_warnings_for_status_change,
    calculate_actual_expiry
)

router = APIRouter(prefix="/stocktake", tags=["盘点任务管理"])


def _generate_task_no(db: Session) -> str:
    now = utc_now()
    prefix = f"PD{now.strftime('%Y%m%d')}"
    last = db.query(StocktakeTask).filter(
        StocktakeTask.task_no.like(f"{prefix}%")
    ).order_by(StocktakeTask.task_no.desc()).first()
    if last:
        seq = int(last.task_no[-4:]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def _enrich_stocktake_item(db: Session, item: StocktakeItem) -> StocktakeItemResponse:
    resp = StocktakeItemResponse.model_validate(item)
    if item.inventory_item:
        resp.current_quantity = item.inventory_item.quantity
        resp.current_status = item.inventory_item.status
        inv_resp = InventoryItemResponse.model_validate(item.inventory_item)
        inv_resp.actual_expiry_date = item.inventory_item.actual_expiry_date
        inv_resp.material = item.inventory_item.material
        resp.inventory_item = inv_resp
    if resp.actual_quantity is not None:
        resp.diff_quantity = resp.actual_quantity - item.snapshot_quantity
    return resp


def _enrich_task_response(db: Session, task: StocktakeTask, include_items: bool = True) -> StocktakeTaskResponse:
    resp = StocktakeTaskResponse.model_validate(task)
    resp.creator = task.creator
    resp.submitter = task.submitter
    resp.confirmer = task.confirmer
    if include_items:
        resp.items = [_enrich_stocktake_item(db, it) for it in task.items]
    return resp


@router.get("", response_model=List[StocktakeTaskResponse])
def list_stocktake_tasks(
    status: Optional[StocktakeTaskStatus] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(StocktakeTask)
    if status:
        query = query.filter(StocktakeTask.status == status)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (StocktakeTask.title.like(like)) |
            (StocktakeTask.task_no.like(like))
        )
    tasks = query.order_by(StocktakeTask.id.desc()).all()
    return [_enrich_task_response(db, t, include_items=False) for t in tasks]


@router.get("/{task_id}", response_model=StocktakeTaskResponse)
def get_stocktake_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(StocktakeTask).filter(StocktakeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="盘点任务不存在")
    return _enrich_task_response(db, task, include_items=True)


@router.post("", response_model=StocktakeTaskResponse)
def create_stocktake_task(
    task_in: StocktakeTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    if not task_in.category_filter and not task_in.location_filter and not task_in.material_ids:
        raise HTTPException(status_code=400, detail="请至少指定一种盘点范围筛选条件")

    query = db.query(InventoryItem).join(Material).filter(
        InventoryItem.status != InventoryStatus.SCRAPPED
    )

    if task_in.category_filter:
        query = query.filter(Material.category == task_in.category_filter)
    if task_in.location_filter:
        query = query.filter(InventoryItem.location == task_in.location_filter)
    if task_in.material_ids:
        query = query.filter(Material.id.in_(task_in.material_ids))

    inventory_items = query.all()
    if not inventory_items:
        raise HTTPException(status_code=400, detail="指定的筛选条件下没有可盘点的库存")

    task = StocktakeTask(
        task_no=_generate_task_no(db),
        title=task_in.title,
        description=task_in.description,
        status=StocktakeTaskStatus.IN_PROGRESS,
        category_filter=task_in.category_filter,
        location_filter=task_in.location_filter,
        material_ids_filter=",".join(str(mid) for mid in task_in.material_ids) if task_in.material_ids else None,
        created_by=current_user.id
    )
    db.add(task)
    db.flush()

    now = utc_now()
    for inv in inventory_items:
        item = StocktakeItem(
            task_id=task.id,
            inventory_item_id=inv.id,
            snapshot_quantity=inv.quantity,
            snapshot_status=inv.status,
            snapshot_original_expiry_date=inv.original_expiry_date,
            snapshot_actual_expiry_date=inv.actual_expiry_date,
            snapshot_location=inv.location,
            snapshot_open_time=inv.open_time,
            snapshot_opened=inv.opened,
            status=StocktakeItemStatus.NOT_ENTERED
        )
        db.add(item)

    db.commit()
    db.refresh(task)
    return _enrich_task_response(db, task, include_items=True)


@router.post("/{task_id}/save", response_model=StocktakeTaskResponse)
def save_stocktake_items(
    task_id: int,
    request: StocktakeBatchUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    task = db.query(StocktakeTask).filter(StocktakeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="盘点任务不存在")
    if task.status in (StocktakeTaskStatus.CONFIRMED, StocktakeTaskStatus.CLOSED):
        raise HTTPException(status_code=400, detail="该任务状态不允许修改数据")
    if task.status == StocktakeTaskStatus.PENDING_REVIEW:
        raise HTTPException(status_code=400, detail="任务已提交复核，暂存前请先撤回")

    if len(request.item_ids) != len(request.items):
        raise HTTPException(status_code=400, detail="条目ID与数据数量不一致")

    now = utc_now()
    for item_id, item_data in zip(request.item_ids, request.items):
        st_item = db.query(StocktakeItem).filter(
            StocktakeItem.id == item_id,
            StocktakeItem.task_id == task_id
        ).first()
        if not st_item:
            continue
        if st_item.status == StocktakeItemStatus.CONFIRMED:
            continue
        if item_data.actual_quantity is not None:
            st_item.actual_quantity = item_data.actual_quantity
        if item_data.remark is not None:
            st_item.remark = item_data.remark
        st_item.status = StocktakeItemStatus.SAVED
        st_item.saved_by = current_user.id
        st_item.saved_at = now

    db.commit()
    db.refresh(task)
    return _enrich_task_response(db, task, include_items=True)


@router.post("/{task_id}/submit", response_model=StocktakeTaskResponse)
def submit_stocktake_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    task = db.query(StocktakeTask).filter(StocktakeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="盘点任务不存在")
    if task.status == StocktakeTaskStatus.PENDING_REVIEW:
        raise HTTPException(status_code=400, detail="任务已在待复核状态")
    if task.status in (StocktakeTaskStatus.CONFIRMED, StocktakeTaskStatus.CLOSED):
        raise HTTPException(status_code=400, detail="该任务状态不允许提交")

    unentered = db.query(StocktakeItem).filter(
        StocktakeItem.task_id == task_id,
        StocktakeItem.status == StocktakeItemStatus.NOT_ENTERED
    ).count()
    if unentered > 0:
        raise HTTPException(status_code=400, detail=f"还有 {unentered} 条未录入的盘点项，请全部填写后提交")

    now = utc_now()
    task.status = StocktakeTaskStatus.PENDING_REVIEW
    task.submitted_by = current_user.id
    task.submitted_at = now

    for st_item in task.items:
        if st_item.status != StocktakeItemStatus.CONFIRMED:
            st_item.status = StocktakeItemStatus.SUBMITTED
            st_item.submitted_by = current_user.id
            st_item.submitted_at = now

    db.commit()
    db.refresh(task)
    return _enrich_task_response(db, task, include_items=True)


@router.post("/{task_id}/confirm", response_model=StocktakeTaskResponse)
def confirm_stocktake_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    task = db.query(StocktakeTask).filter(StocktakeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="盘点任务不存在")
    if task.status == StocktakeTaskStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail="该任务已确认落账，不可重复操作")
    if task.status == StocktakeTaskStatus.CLOSED:
        raise HTTPException(status_code=400, detail="该任务已关闭，不可确认")
    if task.status != StocktakeTaskStatus.PENDING_REVIEW:
        raise HTTPException(status_code=400, detail="请先提交盘点任务后再确认")

    now = utc_now()
    task.status = StocktakeTaskStatus.CONFIRMED
    task.confirmed_by = current_user.id
    task.confirmed_at = now

    for st_item in task.items:
        if st_item.actual_quantity is None:
            continue
        inv = db.query(InventoryItem).filter(InventoryItem.id == st_item.inventory_item_id).first()
        if not inv:
            continue
        if inv.status == InventoryStatus.SCRAPPED:
            continue

        qty_before = inv.quantity
        qty_after = st_item.actual_quantity
        qty_diff = qty_after - qty_before

        inv.quantity = qty_after
        inv.status = determine_status(inv, now)
        resolve_warnings_for_status_change(db, inv, now)
        check_and_create_warnings(db, inv, now)

        st_item.status = StocktakeItemStatus.CONFIRMED
        st_item.confirmed_by = current_user.id
        st_item.confirmed_at = now

        operation = InventoryOperation(
            inventory_item_id=inv.id,
            operation_type=OperationType.INVENTORY_CHECK,
            quantity_change=qty_diff,
            quantity_before=qty_before,
            quantity_after=qty_after,
            operator_id=current_user.id,
            operation_time=now,
            remark=f"盘点任务[{task.task_no}]确认落账，实盘：{qty_after}，原账面：{qty_before}，差异：{qty_diff}",
            stocktake_task_id=task.id
        )
        db.add(operation)

    db.commit()
    db.refresh(task)
    return _enrich_task_response(db, task, include_items=True)


@router.post("/{task_id}/close", response_model=StocktakeTaskResponse)
def close_stocktake_task(
    task_id: int,
    request: StocktakeTaskCloseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    task = db.query(StocktakeTask).filter(StocktakeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="盘点任务不存在")
    if task.status == StocktakeTaskStatus.CLOSED:
        raise HTTPException(status_code=400, detail="该任务已关闭")
    if task.status == StocktakeTaskStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail="该任务已确认落账，不可关闭")

    now = utc_now()
    task.status = StocktakeTaskStatus.CLOSED
    task.closed_by = current_user.id
    task.closed_at = now
    task.close_reason = request.close_reason

    db.commit()
    db.refresh(task)
    return _enrich_task_response(db, task, include_items=True)


@router.get("/{task_id}/export-diff")
def export_stocktake_diff(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    task = db.query(StocktakeTask).filter(StocktakeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="盘点任务不存在")

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "物料编码", "物料名称", "规格型号", "批次号", "单位",
        "快照数量", "当前数量", "实盘数量", "差异数量",
        "快照状态", "当前状态", "快照存放位置", "当前存放位置",
        "快照原始有效期", "快照实际失效日期",
        "盘点备注", "盘点状态"
    ])

    for st_item in task.items:
        inv = st_item.inventory_item
        if not inv:
            continue
        mat = inv.material
        actual_qty = st_item.actual_quantity if st_item.actual_quantity is not None else ""
        diff = (st_item.actual_quantity - st_item.snapshot_quantity) if st_item.actual_quantity is not None else ""
        writer.writerow([
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
            st_item.snapshot_location or "",
            inv.location or "",
            st_item.snapshot_original_expiry_date.strftime("%Y-%m-%d") if st_item.snapshot_original_expiry_date else "",
            st_item.snapshot_actual_expiry_date.strftime("%Y-%m-%d") if st_item.snapshot_actual_expiry_date else "",
            st_item.remark or "",
            st_item.status.value
        ])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f"attachment; filename=stocktake_diff_{task.task_no}.csv"
        }
    )
