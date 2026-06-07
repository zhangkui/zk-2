from datetime import timedelta
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Enum
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.config import utc_now


class UserRole(str, PyEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


class MaterialCategory(str, PyEnum):
    REAGENT = "reagent"
    CONSUMABLE = "consumable"
    STANDARD = "standard"
    OTHER = "other"


class InventoryStatus(str, PyEnum):
    NORMAL = "normal"
    OPENED = "opened"
    LOW_STOCK = "low_stock"
    NEAR_EXPIRY = "near_expiry"
    EXPIRED = "expired"
    SCRAPPED = "scrapped"
    USED_UP = "used_up"


class OperationType(str, PyEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    OPEN = "open"
    RETURN = "return"
    SCRAP = "scrap"
    INVENTORY_CHECK = "inventory_check"
    ADJUST = "adjust"
    RESERVE = "reserve"
    RELEASE_RESERVE = "release_reserve"
    APPROVE_REQUISITION = "approve_requisition"
    REJECT_REQUISITION = "reject_requisition"


class RequisitionStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class WarningType(str, PyEnum):
    NEAR_EXPIRY = "near_expiry"
    EXPIRED = "expired"
    LOW_STOCK = "low_stock"


class WarningStatus(str, PyEnum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class StocktakeTaskStatus(str, PyEnum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    CLOSED = "closed"


class StocktakeItemStatus(str, PyEnum):
    NOT_ENTERED = "not_entered"
    SAVED = "saved"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100))
    hashed_password = Column(String(200), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    operations = relationship("InventoryOperation", back_populates="operator")
    warnings_handled = relationship("Warning", back_populates="handled_by_user")


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    category = Column(Enum(MaterialCategory), default=MaterialCategory.REAGENT)
    specification = Column(String(200))
    unit = Column(String(20), nullable=False)
    manufacturer = Column(String(100))
    min_stock = Column(Float, default=0)
    open_validity_days = Column(Integer, comment="开封后有效天数")
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    inventory_items = relationship("InventoryItem", back_populates="material")


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    batch_no = Column(String(100), nullable=False)
    quantity = Column(Float, nullable=False, default=0, comment="实际数量")
    reserved_quantity = Column(Float, nullable=False, default=0, comment="预占数量")
    original_expiry_date = Column(DateTime, nullable=False, comment="原始有效期")
    open_time = Column(DateTime, comment="开封时间")
    opened = Column(Boolean, default=False)
    status = Column(Enum(InventoryStatus), default=InventoryStatus.NORMAL)
    location = Column(String(100))
    remark = Column(Text)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    material = relationship("Material", back_populates="inventory_items")
    operations = relationship("InventoryOperation", back_populates="inventory_item")
    warnings = relationship("Warning", back_populates="inventory_item")
    reservations = relationship("StockReservation", back_populates="inventory_item")

    @property
    def actual_expiry_date(self):
        if self.open_time and self.material and self.material.open_validity_days:
            open_expiry = self.open_time + timedelta(days=self.material.open_validity_days)
            return min(self.original_expiry_date, open_expiry)
        return self.original_expiry_date

    @property
    def available_quantity(self):
        return max(0, self.quantity - self.reserved_quantity)


class InventoryOperation(Base):
    __tablename__ = "inventory_operations"

    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    operation_type = Column(Enum(OperationType), nullable=False)
    quantity_change = Column(Float, default=0)
    quantity_before = Column(Float)
    quantity_after = Column(Float)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operation_time = Column(DateTime, default=utc_now)
    remark = Column(Text)
    stocktake_task_id = Column(Integer, ForeignKey("stocktake_tasks.id"), nullable=True)

    inventory_item = relationship("InventoryItem", back_populates="operations")
    operator = relationship("User", back_populates="operations")
    stocktake_task = relationship("StocktakeTask", back_populates="operations")


class Warning(Base):
    __tablename__ = "warnings"

    id = Column(Integer, primary_key=True, index=True)
    warning_type = Column(Enum(WarningType), nullable=False)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(Enum(WarningStatus), default=WarningStatus.ACTIVE)
    created_at = Column(DateTime, default=utc_now)
    handled_at = Column(DateTime)
    handled_by = Column(Integer, ForeignKey("users.id"))
    handled_remark = Column(Text)

    inventory_item = relationship("InventoryItem", back_populates="warnings")
    handled_by_user = relationship("User", back_populates="warnings_handled")


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text)
    description = Column(Text)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class StocktakeTask(Base):
    __tablename__ = "stocktake_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_no = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(Enum(StocktakeTaskStatus), default=StocktakeTaskStatus.DRAFT, nullable=False)

    category_filter = Column(Enum(MaterialCategory), nullable=True)
    location_filter = Column(String(200), nullable=True)
    material_ids_filter = Column(Text, nullable=True, comment="逗号分隔的物料ID列表")

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    closed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    closed_at = Column(DateTime, nullable=True)
    close_reason = Column(Text, nullable=True)

    items = relationship("StocktakeItem", back_populates="task", cascade="all, delete-orphan")
    operations = relationship("InventoryOperation", back_populates="stocktake_task")
    creator = relationship("User", foreign_keys=[created_by])
    submitter = relationship("User", foreign_keys=[submitted_by])
    confirmer = relationship("User", foreign_keys=[confirmed_by])
    closer = relationship("User", foreign_keys=[closed_by])


class StocktakeItem(Base):
    __tablename__ = "stocktake_items"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("stocktake_tasks.id"), nullable=False)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)

    snapshot_quantity = Column(Float, nullable=False, comment="快照账面数量")
    snapshot_status = Column(Enum(InventoryStatus), nullable=False, comment="快照库存状态")
    snapshot_original_expiry_date = Column(DateTime, nullable=False, comment="快照原始有效期")
    snapshot_actual_expiry_date = Column(DateTime, nullable=True, comment="快照实际失效日期")
    snapshot_location = Column(String(100), nullable=True, comment="快照存放位置")
    snapshot_open_time = Column(DateTime, nullable=True, comment="快照开封时间")
    snapshot_opened = Column(Boolean, default=False, comment="快照是否已开封")

    actual_quantity = Column(Float, nullable=True, comment="实盘数量")
    remark = Column(Text, nullable=True, comment="盘点备注")

    status = Column(Enum(StocktakeItemStatus), default=StocktakeItemStatus.NOT_ENTERED, nullable=False)
    saved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    saved_at = Column(DateTime, nullable=True)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)

    task = relationship("StocktakeTask", back_populates="items")
    inventory_item = relationship("InventoryItem")
    saver = relationship("User", foreign_keys=[saved_by])
    submitter = relationship("User", foreign_keys=[submitted_by])
    confirmer = relationship("User", foreign_keys=[confirmed_by])


class StockReservation(Base):
    __tablename__ = "stock_reservations"

    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    quantity = Column(Float, nullable=False, comment="预占数量")
    requisition_id = Column(Integer, ForeignKey("requisitions.id"), nullable=True, comment="关联的领用申请单")
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    released_at = Column(DateTime, nullable=True, comment="释放时间")
    released_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    release_remark = Column(Text, nullable=True)
    is_released = Column(Boolean, default=False, comment="是否已释放")

    inventory_item = relationship("InventoryItem", back_populates="reservations")
    requisition = relationship("Requisition", back_populates="reservations")
    operator = relationship("User", foreign_keys=[operator_id])
    releaser = relationship("User", foreign_keys=[released_by])


class Requisition(Base):
    __tablename__ = "requisitions"

    id = Column(Integer, primary_key=True, index=True)
    requisition_no = Column(String(50), unique=True, index=True, nullable=False, comment="申请单号")
    title = Column(String(200), nullable=False, comment="申请标题")
    status = Column(Enum(RequisitionStatus), default=RequisitionStatus.PENDING, nullable=False)
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    apply_remark = Column(Text, nullable=True, comment="申请说明")
    created_at = Column(DateTime, default=utc_now)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approve_remark = Column(Text, nullable=True, comment="审批意见")
    rejected_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    reject_remark = Column(Text, nullable=True, comment="驳回意见")
    cancelled_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancel_remark = Column(Text, nullable=True, comment="取消说明")

    items = relationship("RequisitionItem", back_populates="requisition", cascade="all, delete-orphan")
    reservations = relationship("StockReservation", back_populates="requisition")
    applicant = relationship("User", foreign_keys=[applicant_id])
    approver = relationship("User", foreign_keys=[approved_by])
    rejecter = relationship("User", foreign_keys=[rejected_by])
    canceller = relationship("User", foreign_keys=[cancelled_by])


class RequisitionItem(Base):
    __tablename__ = "requisition_items"

    id = Column(Integer, primary_key=True, index=True)
    requisition_id = Column(Integer, ForeignKey("requisitions.id"), nullable=False)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    quantity = Column(Float, nullable=False, comment="申请领用数量")
    actual_outbound_quantity = Column(Float, nullable=True, comment="实际出库数量")
    remark = Column(Text, nullable=True)

    requisition = relationship("Requisition", back_populates="items")
    inventory_item = relationship("InventoryItem")
    material = relationship("Material")
