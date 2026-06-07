from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles, get_current_user
from app.config import utc_now
from app.models import (
    InventoryItem, Material, InventoryStatus,
    InventoryOperation, OperationType, User, UserRole,
    StockReservation, Requisition, RequisitionItem,
    RequisitionStatus
)
from app.schemas import (
    RequisitionCreate, RequisitionResponse,
    RequisitionApproveRequest, RequisitionRejectRequest,
    RequisitionCancelRequest
)
from app.utils import (
    determine_status, is_expired, can_reserve, can_use,
    check_and_create_warnings, resolve_warnings_for_status_change
)

router = APIRouter(prefix="/requisitions", tags=["领用申请"])


def _generate_requisition_no(db: Session) -> str:
    now = utc_now()
    prefix = now.strftime("RQ%Y%m%d")
    count = db.query(Requisition).filter(
        Requisition.requisition_no.like(f"{prefix}%")
    ).count() + 1
    return f"{prefix}{count:04d}"


def _enrich_requisition(req: Requisition) -> dict:
    from app.schemas import InventoryItemResponse, MaterialResponse

    items_data = []
    for item in req.items:
        item_dict = {
            "id": item.id,
            "requisition_id": item.requisition_id,
            "inventory_item_id": item.inventory_item_id,
            "material_id": item.material_id,
            "quantity": item.quantity,
            "remark": item.remark,
        }
        if item.inventory_item:
            inv = item.inventory_item
            item_dict["inventory_item"] = InventoryItemResponse(
                id=inv.id,
                material_id=inv.material_id,
                material=MaterialResponse.model_validate(inv.material) if inv.material else None,
                batch_no=inv.batch_no,
                quantity=inv.quantity,
                reserved_quantity=inv.reserved_quantity,
                available_quantity=inv.available_quantity,
                original_expiry_date=inv.original_expiry_date,
                open_time=inv.open_time,
                opened=inv.opened,
                status=inv.status,
                actual_expiry_date=inv.actual_expiry_date,
                location=inv.location,
                remark=inv.remark,
                created_at=inv.created_at,
                updated_at=inv.updated_at,
            )
        else:
            item_dict["inventory_item"] = None
        if item.material:
            item_dict["material"] = MaterialResponse.model_validate(item.material)
        else:
            item_dict["material"] = None
        items_data.append(item_dict)

    return {
        "id": req.id,
        "requisition_no": req.requisition_no,
        "title": req.title,
        "status": req.status,
        "applicant_id": req.applicant_id,
        "applicant": req.applicant,
        "apply_remark": req.apply_remark,
        "created_at": req.created_at,
        "approved_by": req.approved_by,
        "approved_at": req.approved_at,
        "approve_remark": req.approve_remark,
        "approver": req.approver,
        "rejected_by": req.rejected_by,
        "rejected_at": req.rejected_at,
        "reject_remark": req.reject_remark,
        "rejecter": req.rejecter,
        "cancelled_by": req.cancelled_by,
        "cancelled_at": req.cancelled_at,
        "cancel_remark": req.cancel_remark,
        "canceller": req.canceller,
        "items": items_data,
    }


@router.get("", response_model=List[RequisitionResponse])
def list_requisitions(
    status: Optional[RequisitionStatus] = Query(None),
    applicant_id: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Requisition)
    if status:
        query = query.filter(Requisition.status == status)
    if applicant_id:
        query = query.filter(Requisition.applicant_id == applicant_id)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (Requisition.title.like(like)) |
            (Requisition.requisition_no.like(like))
        )
    requisitions = query.order_by(Requisition.created_at.desc()).all()
    for req in requisitions:
        req.applicant
        req.approver
        req.rejecter
        req.canceller
    return [_enrich_requisition(r) for r in requisitions]


@router.get("/{requisition_id}", response_model=RequisitionResponse)
def get_requisition(
    requisition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    req = db.query(Requisition).filter(Requisition.id == requisition_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="领用申请不存在")
    for item in req.items:
        item.inventory_item
        if item.inventory_item:
            item.inventory_item.material
        item.material
    return _enrich_requisition(req)


@router.post("", response_model=RequisitionResponse)
def create_requisition(
    data: RequisitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    now = utc_now()
    items = []
    for item_data in data.items:
        inv = db.query(InventoryItem).filter(InventoryItem.id == item_data.inventory_item_id).first()
        if not inv:
            raise HTTPException(status_code=400, detail=f"库存ID {item_data.inventory_item_id} 不存在")
        if not can_reserve(inv, now):
            if is_expired(inv, now):
                raise HTTPException(status_code=400, detail=f"批次 [{inv.batch_no}] 已过期，不可申请")
            if inv.status == InventoryStatus.SCRAPPED:
                raise HTTPException(status_code=400, detail=f"批次 [{inv.batch_no}] 已报废，不可申请")
            if inv.status == InventoryStatus.USED_UP:
                raise HTTPException(status_code=400, detail=f"批次 [{inv.batch_no}] 已用完，不可申请")
            raise HTTPException(status_code=400, detail=f"批次 [{inv.batch_no}] 不可申请")
        if item_data.quantity > inv.available_quantity:
            raise HTTPException(
                status_code=400,
                detail=f"批次 [{inv.batch_no}] 申请数量超出可用数量，可用：{inv.available_quantity}"
            )
        items.append((inv, item_data))

    requisition_no = _generate_requisition_no(db)
    req = Requisition(
        requisition_no=requisition_no,
        title=data.title,
        applicant_id=current_user.id,
        apply_remark=data.apply_remark,
        status=RequisitionStatus.PENDING
    )
    db.add(req)
    db.flush()

    for inv, item_data in items:
        ri = RequisitionItem(
            requisition_id=req.id,
            inventory_item_id=inv.id,
            material_id=inv.material_id,
            quantity=item_data.quantity,
            remark=item_data.remark
        )
        db.add(ri)
        db.flush()

        reserved_before = inv.reserved_quantity
        inv.reserved_quantity += item_data.quantity

        reservation = StockReservation(
            inventory_item_id=inv.id,
            quantity=item_data.quantity,
            requisition_id=req.id,
            operator_id=current_user.id,
            remark=item_data.remark or f"申请单 {requisition_no} 预占"
        )
        db.add(reservation)
        db.flush()

        operation = InventoryOperation(
            inventory_item_id=inv.id,
            operation_type=OperationType.RESERVE,
            quantity_change=0,
            quantity_before=inv.quantity,
            quantity_after=inv.quantity,
            operator_id=current_user.id,
            remark=f"申请单 {requisition_no} 预占 {item_data.quantity} {inv.material.unit}（预占: {reserved_before} → {inv.reserved_quantity}）"
        )
        db.add(operation)

    db.commit()
    db.refresh(req)
    for item in req.items:
        item.inventory_item
        if item.inventory_item:
            item.inventory_item.material
        item.material
    return _enrich_requisition(req)


@router.post("/{requisition_id}/approve", response_model=RequisitionResponse)
def approve_requisition(
    requisition_id: int,
    data: RequisitionApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    now = utc_now()
    req = db.query(Requisition).filter(Requisition.id == requisition_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="领用申请不存在")
    if req.status != RequisitionStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"当前状态为 [{req.status.value}]，不可审批")

    for item in req.items:
        inv = db.query(InventoryItem).filter(InventoryItem.id == item.inventory_item_id).first()
        if not inv:
            raise HTTPException(status_code=400, detail=f"库存ID {item.inventory_item_id} 不存在")
        if not can_use(inv, now):
            if is_expired(inv, now):
                raise HTTPException(status_code=400, detail=f"批次 [{inv.batch_no}] 已过期，无法审批通过")
            if inv.status == InventoryStatus.SCRAPPED:
                raise HTTPException(status_code=400, detail=f"批次 [{inv.batch_no}] 已报废，无法审批通过")
        actual_qty = min(item.quantity, inv.quantity)
        if actual_qty <= 0:
            raise HTTPException(status_code=400, detail=f"批次 [{inv.batch_no}] 库存不足")
        if actual_qty < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"批次 [{inv.batch_no}] 库存不足（当前：{inv.quantity}，申请：{item.quantity}）"
            )

    req.status = RequisitionStatus.APPROVED
    req.approved_by = current_user.id
    req.approved_at = now
    req.approve_remark = data.approve_remark

    for item in req.items:
        inv = db.query(InventoryItem).filter(InventoryItem.id == item.inventory_item_id).first()
        qty_before = inv.quantity
        reserved_before = inv.reserved_quantity

        actual_qty = min(item.quantity, inv.quantity)
        item.actual_outbound_quantity = actual_qty
        inv.quantity -= actual_qty
        inv.reserved_quantity = max(0, inv.reserved_quantity - actual_qty)

        inv.status = determine_status(inv, now)
        resolve_warnings_for_status_change(db, inv, now)
        check_and_create_warnings(db, inv, now)

        for res in req.reservations:
            if res.inventory_item_id == inv.id and not res.is_released:
                res.is_released = True
                res.released_at = now
                res.released_by = current_user.id
                res.release_remark = "审批通过自动转为领用出库"

        operation = InventoryOperation(
            inventory_item_id=inv.id,
            operation_type=OperationType.OUTBOUND,
            quantity_change=-actual_qty,
            quantity_before=qty_before,
            quantity_after=inv.quantity,
            operator_id=current_user.id,
            remark=f"审批通过 申请单[{req.requisition_no}] 领用 {actual_qty} {inv.material.unit}（{data.approve_remark or ''}）"
        )
        db.add(operation)

        approve_op = InventoryOperation(
            inventory_item_id=inv.id,
            operation_type=OperationType.APPROVE_REQUISITION,
            quantity_change=0,
            quantity_before=qty_before,
            quantity_after=inv.quantity,
            operator_id=current_user.id,
            remark=f"审批领用 申请单[{req.requisition_no}]，领用 {actual_qty} {inv.material.unit}，预占: {reserved_before} → {inv.reserved_quantity}"
        )
        db.add(approve_op)

    db.commit()
    db.refresh(req)
    for item in req.items:
        item.inventory_item
        if item.inventory_item:
            item.inventory_item.material
        item.material
    return _enrich_requisition(req)


@router.post("/{requisition_id}/reject", response_model=RequisitionResponse)
def reject_requisition(
    requisition_id: int,
    data: RequisitionRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    now = utc_now()
    req = db.query(Requisition).filter(Requisition.id == requisition_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="领用申请不存在")
    if req.status != RequisitionStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"当前状态为 [{req.status.value}]，不可驳回")

    req.status = RequisitionStatus.REJECTED
    req.rejected_by = current_user.id
    req.rejected_at = now
    req.reject_remark = data.reject_remark

    for item in req.items:
        inv = db.query(InventoryItem).filter(InventoryItem.id == item.inventory_item_id).first()
        if inv:
            reserved_before = inv.reserved_quantity
            release_qty = min(item.quantity, inv.reserved_quantity)
            inv.reserved_quantity = max(0, inv.reserved_quantity - release_qty)

            reject_op = InventoryOperation(
                inventory_item_id=inv.id,
                operation_type=OperationType.REJECT_REQUISITION,
                quantity_change=0,
                quantity_before=inv.quantity,
                quantity_after=inv.quantity,
                operator_id=current_user.id,
                remark=f"驳回申请 申请单[{req.requisition_no}]，释放预占 {release_qty} {inv.material.unit}，预占: {reserved_before} → {inv.reserved_quantity}（{data.reject_remark}）"
            )
            db.add(reject_op)

    for res in req.reservations:
        if not res.is_released:
            res.is_released = True
            res.released_at = now
            res.released_by = current_user.id
            res.release_remark = f"申请驳回自动释放：{data.reject_remark}"

    db.commit()
    db.refresh(req)
    for item in req.items:
        item.inventory_item
        if item.inventory_item:
            item.inventory_item.material
        item.material
    return _enrich_requisition(req)


@router.post("/{requisition_id}/cancel", response_model=RequisitionResponse)
def cancel_requisition(
    requisition_id: int,
    data: RequisitionCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
):
    now = utc_now()
    req = db.query(Requisition).filter(Requisition.id == requisition_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="领用申请不存在")
    if req.status != RequisitionStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"当前状态为 [{req.status.value}]，不可取消")
    if req.applicant_id != current_user.id and current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="仅申请人或管理员可取消")

    req.status = RequisitionStatus.CANCELLED
    req.cancelled_by = current_user.id
    req.cancelled_at = now
    req.cancel_remark = data.cancel_remark

    for item in req.items:
        inv = db.query(InventoryItem).filter(InventoryItem.id == item.inventory_item_id).first()
        if inv:
            reserved_before = inv.reserved_quantity
            release_qty = min(item.quantity, inv.reserved_quantity)
            inv.reserved_quantity = max(0, inv.reserved_quantity - release_qty)

            release_op = InventoryOperation(
                inventory_item_id=inv.id,
                operation_type=OperationType.RELEASE_RESERVE,
                quantity_change=0,
                quantity_before=inv.quantity,
                quantity_after=inv.quantity,
                operator_id=current_user.id,
                remark=f"取消申请 申请单[{req.requisition_no}]，释放预占 {release_qty} {inv.material.unit}，预占: {reserved_before} → {inv.reserved_quantity}"
            )
            db.add(release_op)

    for res in req.reservations:
        if not res.is_released:
            res.is_released = True
            res.released_at = now
            res.released_by = current_user.id
            res.release_remark = f"申请取消自动释放：{data.cancel_remark or ''}"

    db.commit()
    db.refresh(req)
    for item in req.items:
        item.inventory_item
        if item.inventory_item:
            item.inventory_item.material
        item.material
    return _enrich_requisition(req)
