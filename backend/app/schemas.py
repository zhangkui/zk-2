from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from app.models import (
    UserRole, MaterialCategory, InventoryStatus,
    OperationType, WarningType, WarningStatus,
    StocktakeTaskStatus, StocktakeItemStatus,
    RequisitionStatus
)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBase(BaseModel):
    username: str
    full_name: str
    email: Optional[str] = None
    role: UserRole = UserRole.VIEWER


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: datetime


class MaterialBase(BaseModel):
    code: str
    name: str
    category: MaterialCategory = MaterialCategory.REAGENT
    specification: Optional[str] = None
    unit: str
    manufacturer: Optional[str] = None
    min_stock: float = 0
    open_validity_days: Optional[int] = None
    description: Optional[str] = None


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[MaterialCategory] = None
    specification: Optional[str] = None
    unit: Optional[str] = None
    manufacturer: Optional[str] = None
    min_stock: Optional[float] = None
    open_validity_days: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class MaterialResponse(MaterialBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class InventoryItemBase(BaseModel):
    material_id: int
    batch_no: str
    quantity: float
    original_expiry_date: datetime
    location: Optional[str] = None
    remark: Optional[str] = None


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemUpdate(BaseModel):
    quantity: Optional[float] = None
    location: Optional[str] = None
    remark: Optional[str] = None


class OpenInventoryRequest(BaseModel):
    remark: Optional[str] = None


class InventoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    material_id: int
    material: Optional[MaterialResponse] = None
    batch_no: str
    quantity: float
    reserved_quantity: float = 0
    available_quantity: Optional[float] = None
    original_expiry_date: datetime
    open_time: Optional[datetime] = None
    opened: bool
    status: InventoryStatus
    actual_expiry_date: Optional[datetime] = None
    location: Optional[str] = None
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class InventoryOperationBase(BaseModel):
    inventory_item_id: int
    operation_type: OperationType
    quantity_change: float = 0
    remark: Optional[str] = None


class InventoryOperationCreate(InventoryOperationBase):
    pass


class InventoryOperationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    inventory_item_id: int
    operation_type: OperationType
    quantity_change: float
    quantity_before: Optional[float] = None
    quantity_after: Optional[float] = None
    operator_id: int
    operator: Optional[UserResponse] = None
    operation_time: datetime
    remark: Optional[str] = None
    stocktake_task_id: Optional[int] = None


class WarningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    warning_type: WarningType
    inventory_item_id: int
    inventory_item: Optional[InventoryItemResponse] = None
    message: str
    status: WarningStatus
    created_at: datetime
    handled_at: Optional[datetime] = None
    handled_by: Optional[int] = None
    handled_remark: Optional[str] = None


class WarningHandleRequest(BaseModel):
    status: WarningStatus = WarningStatus.ACKNOWLEDGED
    handled_remark: Optional[str] = None


class DashboardStats(BaseModel):
    total_materials: int
    total_inventory: int
    total_warnings: int
    near_expiry_count: int
    expired_count: int
    low_stock_count: int
    total_operations_today: int
    ongoing_stocktake_tasks: int
    pending_review_diffs: int
    pending_requisitions: int = 0
    total_reserved_quantity: float = 0.0


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


class StocktakeTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category_filter: Optional[MaterialCategory] = None
    location_filter: Optional[str] = None
    material_ids: Optional[List[int]] = None


class StocktakeItemUpdate(BaseModel):
    actual_quantity: Optional[float] = None
    remark: Optional[str] = None


class StocktakeItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    inventory_item_id: int
    snapshot_quantity: float
    snapshot_status: InventoryStatus
    snapshot_original_expiry_date: datetime
    snapshot_actual_expiry_date: Optional[datetime] = None
    snapshot_location: Optional[str] = None
    snapshot_open_time: Optional[datetime] = None
    snapshot_opened: bool
    actual_quantity: Optional[float] = None
    remark: Optional[str] = None
    status: StocktakeItemStatus
    saved_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    current_quantity: Optional[float] = None
    current_status: Optional[InventoryStatus] = None
    diff_quantity: Optional[float] = None
    inventory_item: Optional[InventoryItemResponse] = None


class StocktakeTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_no: str
    title: str
    description: Optional[str] = None
    status: StocktakeTaskStatus
    category_filter: Optional[MaterialCategory] = None
    location_filter: Optional[str] = None
    material_ids_filter: Optional[str] = None
    created_by: int
    created_at: datetime
    submitted_by: Optional[int] = None
    submitted_at: Optional[datetime] = None
    confirmed_by: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    closed_by: Optional[int] = None
    closed_at: Optional[datetime] = None
    close_reason: Optional[str] = None
    items: Optional[List[StocktakeItemResponse]] = None
    creator: Optional[UserResponse] = None
    submitter: Optional[UserResponse] = None
    confirmer: Optional[UserResponse] = None


class StocktakeTaskCloseRequest(BaseModel):
    close_reason: Optional[str] = None


class StocktakeBatchUpdateRequest(BaseModel):
    items: List[StocktakeItemUpdate]
    item_ids: List[int]


class ReserveRequest(BaseModel):
    quantity: float = Field(..., gt=0)
    remark: Optional[str] = None


class ReleaseReserveRequest(BaseModel):
    remark: Optional[str] = None


class StockReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    inventory_item_id: int
    inventory_item: Optional[InventoryItemResponse] = None
    quantity: float
    requisition_id: Optional[int] = None
    requisition_no: Optional[str] = None
    operator_id: int
    operator: Optional[UserResponse] = None
    remark: Optional[str] = None
    created_at: datetime
    released_at: Optional[datetime] = None
    released_by: Optional[int] = None
    releaser: Optional[UserResponse] = None
    release_remark: Optional[str] = None
    is_released: bool


class RequisitionItemCreate(BaseModel):
    inventory_item_id: int
    quantity: float = Field(..., gt=0)
    remark: Optional[str] = None


class RequisitionCreate(BaseModel):
    title: str
    apply_remark: Optional[str] = None
    items: List[RequisitionItemCreate] = Field(..., min_length=1)


class RequisitionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    requisition_id: int
    inventory_item_id: int
    inventory_item: Optional[InventoryItemResponse] = None
    material_id: int
    material: Optional[MaterialResponse] = None
    quantity: float
    actual_outbound_quantity: Optional[float] = None
    remark: Optional[str] = None


class RequisitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    requisition_no: str
    title: str
    status: RequisitionStatus
    applicant_id: int
    applicant: Optional[UserResponse] = None
    apply_remark: Optional[str] = None
    created_at: datetime
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    approve_remark: Optional[str] = None
    approver: Optional[UserResponse] = None
    rejected_by: Optional[int] = None
    rejected_at: Optional[datetime] = None
    reject_remark: Optional[str] = None
    rejecter: Optional[UserResponse] = None
    cancelled_by: Optional[int] = None
    cancelled_at: Optional[datetime] = None
    cancel_remark: Optional[str] = None
    canceller: Optional[UserResponse] = None
    items: Optional[List[RequisitionItemResponse]] = None


class RequisitionApproveRequest(BaseModel):
    approve_remark: Optional[str] = None


class RequisitionRejectRequest(BaseModel):
    reject_remark: str = Field(..., min_length=1)


class RequisitionCancelRequest(BaseModel):
    cancel_remark: Optional[str] = None
