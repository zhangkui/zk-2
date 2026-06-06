from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from app.models import (
    UserRole, MaterialCategory, InventoryStatus,
    OperationType, WarningType, WarningStatus
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


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)
