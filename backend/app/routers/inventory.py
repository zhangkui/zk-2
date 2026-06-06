from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles, get_current_user
from app.config import utc_now
from app.models import (
    InventoryItem, Material, InventoryStatus,
    InventoryOperation, OperationType, User, UserRole
)
from app.schemas import (
    InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse,
    OpenInventoryRequest, InventoryOperationCreate, InventoryOperationResponse
)
from app.utils import (
    determine_status, is_expired, can_use,
    check_and_create_warnings, resolve_warnings_for_status_change
)

router = APIRouter(prefix="/inventory", tags=["库存管理"])


def _enrich_response(db: Session, item: InventoryItem) -> InventoryItemResponse:
    resp = InventoryItemResponse.model_validate(item)
    resp.actual_expiry_date = item.actual_expiry_date
    resp.material = item.material
    return resp


@router.get("", response_model=List[InventoryItemResponse])
def list_inventory(
    material_id: Optional[int] = Query(None),
    status: Optional[InventoryStatus] = Query(None),
    keyword: Optional[str] = Query(None),
    only_expired: Optional[bool] = Query(False),
    only_near_expiry: Optional[bool] = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(InventoryItem).join(Material)

    if material_id:
        query = query.filter(InventoryItem.material_id == material_id)
    if status:
        query = query.filter(InventoryItem.status == status)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (Material.name.like(like)) |
            (Material.code.like(like)) |
            (InventoryItem.batch_no.like(like))
        )

    items = query.order_by(InventoryItem.id.desc()).all()

    now = utc_now()
    result = []
    for item in items:
        if only_expired and not is_expired(item, now):
            continue
        if only_near_expiry:
            if is_expired(item, now):
                continue
            from app.utils import is_near_expiry
            if not is_near_expiry(item, now=now):
                continue
        result.append(_enrich_response(db, item))

    return result


@router.get("/{item_id}", response_model=InventoryItemResponse)
def get_inventory(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="库存不存在")
    return _enrich_response(db, item)


@router.post("", response_model=InventoryItemResponse)
def create_inventory(
    item_in: InventoryItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    material = db.query(Material).filter(Material.id == item_in.material_id).first()
    if not material:
        raise HTTPException(status_code=400, detail="物料不存在")

    item = InventoryItem(**item_in.model_dump())
    db.add(item)
    db.flush()

    now = utc_now()
    item.status = determine_status(item, now)
    check_and_create_warnings(db, item, now)

    operation = InventoryOperation(
        inventory_item_id=item.id,
        operation_type=OperationType.INBOUND,
        quantity_change=item.quantity,
        quantity_before=0,
        quantity_after=item.quantity,
        operator_id=current_user.id,
        remark=f"入库，批次号: {item.batch_no}"
    )
    db.add(operation)

    db.commit()
    db.refresh(item)
    return _enrich_response(db, item)


@router.post("/{item_id}/open", response_model=InventoryItemResponse)
def open_inventory(
    item_id: int,
    request: OpenInventoryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="库存不存在")

    if item.status == InventoryStatus.SCRAPPED:
        raise HTTPException(status_code=400, detail="已报废库存无法开封")

    if item.opened:
        raise HTTPException(status_code=400, detail="该库存已开封，不可重复开封")

    now = utc_now()
    item.opened = True
    item.open_time = now
    item.status = determine_status(item, now)

    resolve_warnings_for_status_change(db, item, now)
    check_and_create_warnings(db, item, now)

    operation = InventoryOperation(
        inventory_item_id=item.id,
        operation_type=OperationType.OPEN,
        quantity_change=0,
        quantity_before=item.quantity,
        quantity_after=item.quantity,
        operator_id=current_user.id,
        remark=request.remark or "开封"
    )
    db.add(operation)
    db.commit()
    db.refresh(item)
    return _enrich_response(db, item)


@router.post("/{item_id}/outbound", response_model=InventoryItemResponse)
def outbound_inventory(
    item_id: int,
    request: InventoryOperationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="库存不存在")

    now = utc_now()
    if not can_use(item, now):
        if is_expired(item, now):
            raise HTTPException(status_code=400, detail="该库存已过期，禁止领用")
        if item.status == InventoryStatus.SCRAPPED:
            raise HTTPException(status_code=400, detail="该库存已报废，禁止领用")
        raise HTTPException(status_code=400, detail="该库存不可领用")

    if request.quantity_change <= 0:
        raise HTTPException(status_code=400, detail="领用数量必须大于0")
    if request.quantity_change > item.quantity:
        raise HTTPException(status_code=400, detail="领用数量超出库存")

    qty_before = item.quantity
    item.quantity -= request.quantity_change

    item.status = determine_status(item, now)
    resolve_warnings_for_status_change(db, item, now)
    check_and_create_warnings(db, item, now)

    operation = InventoryOperation(
        inventory_item_id=item.id,
        operation_type=OperationType.OUTBOUND,
        quantity_change=-request.quantity_change,
        quantity_before=qty_before,
        quantity_after=item.quantity,
        operator_id=current_user.id,
        remark=request.remark or f"领用 {request.quantity_change} {item.material.unit}"
    )
    db.add(operation)
    db.commit()
    db.refresh(item)
    return _enrich_response(db, item)


@router.post("/{item_id}/return", response_model=InventoryItemResponse)
def return_inventory(
    item_id: int,
    request: InventoryOperationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="库存不存在")

    if item.status == InventoryStatus.SCRAPPED:
        raise HTTPException(status_code=400, detail="已报废库存不可归还")

    if request.quantity_change <= 0:
        raise HTTPException(status_code=400, detail="归还数量必须大于0")

    now = utc_now()
    qty_before = item.quantity
    item.quantity += request.quantity_change

    item.status = determine_status(item, now)
    resolve_warnings_for_status_change(db, item, now)
    check_and_create_warnings(db, item, now)

    operation = InventoryOperation(
        inventory_item_id=item.id,
        operation_type=OperationType.RETURN,
        quantity_change=request.quantity_change,
        quantity_before=qty_before,
        quantity_after=item.quantity,
        operator_id=current_user.id,
        remark=request.remark or f"归还 {request.quantity_change} {item.material.unit}"
    )
    db.add(operation)
    db.commit()
    db.refresh(item)
    return _enrich_response(db, item)


@router.post("/{item_id}/scrap", response_model=InventoryItemResponse)
def scrap_inventory(
    item_id: int,
    request: InventoryOperationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="库存不存在")

    if item.status == InventoryStatus.SCRAPPED:
        raise HTTPException(status_code=400, detail="该库存已报废")

    qty_before = item.quantity
    qty_change = request.quantity_change if request.quantity_change > 0 else item.quantity
    item.quantity = max(0, item.quantity - qty_change)

    now = utc_now()
    if item.quantity == 0 and qty_change == qty_before:
        item.status = InventoryStatus.SCRAPPED
    else:
        item.status = determine_status(item, now)

    resolve_warnings_for_status_change(db, item, now)
    check_and_create_warnings(db, item, now)

    operation = InventoryOperation(
        inventory_item_id=item.id,
        operation_type=OperationType.SCRAP,
        quantity_change=-qty_change,
        quantity_before=qty_before,
        quantity_after=item.quantity,
        operator_id=current_user.id,
        remark=request.remark or f"报废 {qty_change} {item.material.unit}"
    )
    db.add(operation)
    db.commit()
    db.refresh(item)
    return _enrich_response(db, item)


@router.post("/{item_id}/inventory-check", response_model=InventoryItemResponse)
def inventory_check(
    item_id: int,
    request: InventoryOperationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="库存不存在")

    if item.status == InventoryStatus.SCRAPPED:
        raise HTTPException(status_code=400, detail="已报废库存不可盘点")

    qty_before = item.quantity
    actual_qty = request.quantity_change
    if actual_qty < 0:
        raise HTTPException(status_code=400, detail="盘点数量不能为负数")

    qty_diff = actual_qty - qty_before
    item.quantity = actual_qty

    now = utc_now()
    item.status = determine_status(item, now)
    resolve_warnings_for_status_change(db, item, now)
    check_and_create_warnings(db, item, now)

    operation = InventoryOperation(
        inventory_item_id=item.id,
        operation_type=OperationType.INVENTORY_CHECK,
        quantity_change=qty_diff,
        quantity_before=qty_before,
        quantity_after=item.quantity,
        operator_id=current_user.id,
        remark=request.remark or f"盘点，实际数量：{actual_qty}，差异：{qty_diff}"
    )
    db.add(operation)
    db.commit()
    db.refresh(item)
    return _enrich_response(db, item)


@router.get("/{item_id}/operations", response_model=List[InventoryOperationResponse])
def get_inventory_operations(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="库存不存在")
    operations = db.query(InventoryOperation).filter(
        InventoryOperation.inventory_item_id == item_id
    ).order_by(InventoryOperation.operation_time.desc()).all()
    for op in operations:
        op.operator
    return operations
