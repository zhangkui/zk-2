from datetime import datetime, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import Material, InventoryItem, InventoryStatus, MaterialCategory
from app.utils import (
    calculate_actual_expiry, is_expired, is_near_expiry,
    is_low_stock, determine_status, can_use
)


SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def create_test_material(
    db,
    code="MAT001",
    name="测试试剂",
    min_stock=5,
    open_validity_days=30
):
    material = Material(
        code=code,
        name=name,
        category=MaterialCategory.REAGENT,
        specification="500ml",
        unit="瓶",
        manufacturer="测试厂商",
        min_stock=min_stock,
        open_validity_days=open_validity_days
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def create_test_inventory(
    db,
    material,
    batch_no="BATCH001",
    quantity=10,
    original_expiry_days=180,
    open_time=None,
    opened=False
):
    item = InventoryItem(
        material_id=material.id,
        material=material,
        batch_no=batch_no,
        quantity=quantity,
        original_expiry_date=datetime.utcnow() + timedelta(days=original_expiry_days),
        open_time=open_time,
        opened=opened,
        status=InventoryStatus.NORMAL
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


class TestExpiryCalculation:
    """测试效期计算逻辑"""

    def test_actual_expiry_without_open(self, db):
        """未开封时，实际有效期等于原始有效期"""
        material = create_test_material(db, open_validity_days=30)
        item = create_test_inventory(db, material, original_expiry_days=180)
        actual = calculate_actual_expiry(item)
        assert actual == item.original_expiry_date

    def test_actual_expiry_with_open_validity_longer(self, db):
        """开封后有效期长于原始有效期时，取原始有效期"""
        material = create_test_material(db, open_validity_days=90)
        now = datetime.utcnow()
        item = create_test_inventory(
            db, material,
            original_expiry_days=30,
            open_time=now,
            opened=True
        )
        actual = calculate_actual_expiry(item)
        assert actual == item.original_expiry_date

    def test_actual_expiry_with_open_validity_shorter(self, db):
        """开封后有效期短于原始有效期时，取开封后有效期"""
        material = create_test_material(db, open_validity_days=7)
        now = datetime.utcnow()
        item = create_test_inventory(
            db, material,
            original_expiry_days=180,
            open_time=now,
            opened=True
        )
        actual = calculate_actual_expiry(item)
        expected = now + timedelta(days=7)
        assert abs((actual - expected).total_seconds()) < 1

    def test_is_expired_true(self, db):
        """已过期判断"""
        material = create_test_material(db)
        item = create_test_inventory(db, material, original_expiry_days=-1)
        assert is_expired(item) is True

    def test_is_expired_false(self, db):
        """未过期判断"""
        material = create_test_material(db)
        item = create_test_inventory(db, material, original_expiry_days=30)
        assert is_expired(item) is False

    def test_is_near_expiry_true(self, db):
        """近效期判断（30天内）"""
        material = create_test_material(db)
        item = create_test_inventory(db, material, original_expiry_days=15)
        assert is_near_expiry(item, days=30) is True

    def test_is_near_expiry_false(self, db):
        """非近效期判断"""
        material = create_test_material(db)
        item = create_test_inventory(db, material, original_expiry_days=90)
        assert is_near_expiry(item, days=30) is False

    def test_is_near_expiry_already_expired(self, db):
        """已过期的不应算作近效期"""
        material = create_test_material(db)
        item = create_test_inventory(db, material, original_expiry_days=-1)
        now = datetime.utcnow()
        assert is_near_expiry(item, days=30, now=now) is False


class TestAfterOpenExpiry:
    """测试开封后有效期计算"""

    def test_open_validity_calculation(self, db):
        """开封后有效期计算：开封时间 + 开封有效天数"""
        material = create_test_material(db, open_validity_days=14)
        open_time = datetime(2024, 1, 1, 12, 0, 0)
        item = create_test_inventory(
            db, material,
            original_expiry_days=365,
            open_time=open_time,
            opened=True
        )
        actual = calculate_actual_expiry(item)
        expected = open_time + timedelta(days=14)
        assert actual == expected

    def test_open_validity_vs_original_min(self, db):
        """实际失效时间取更早值"""
        material = create_test_material(db, open_validity_days=60)
        open_time = datetime(2024, 1, 1, 12, 0, 0)
        original_expiry = datetime(2024, 2, 1, 12, 0, 0)
        item = InventoryItem(
            material_id=material.id,
            material=material,
            batch_no="TEST",
            quantity=10,
            original_expiry_date=original_expiry,
            open_time=open_time,
            opened=True
        )
        actual = calculate_actual_expiry(item)
        assert actual == original_expiry
        assert actual < open_time + timedelta(days=60)


class TestLowStockWarning:
    """测试低库存预警"""

    def test_is_low_stock_true(self, db):
        """低于阈值触发低库存预警"""
        material = create_test_material(db, min_stock=10)
        item = create_test_inventory(db, material, quantity=5)
        assert is_low_stock(item) is True

    def test_is_low_stock_equal(self, db):
        """等于阈值触发低库存预警"""
        material = create_test_material(db, min_stock=10)
        item = create_test_inventory(db, material, quantity=10)
        assert is_low_stock(item) is True

    def test_is_low_stock_false(self, db):
        """高于阈值不触发低库存预警"""
        material = create_test_material(db, min_stock=5)
        item = create_test_inventory(db, material, quantity=10)
        assert is_low_stock(item) is False

    def test_is_low_stock_zero_quantity(self, db):
        """零库存触发低库存预警"""
        material = create_test_material(db, min_stock=1)
        item = create_test_inventory(db, material, quantity=0)
        assert is_low_stock(item) is True


class TestInventoryStatus:
    """测试库存状态判定"""

    def test_status_normal(self, db):
        """正常状态"""
        material = create_test_material(db, min_stock=5, open_validity_days=30)
        item = create_test_inventory(db, material, quantity=10, original_expiry_days=180)
        status = determine_status(item)
        assert status == InventoryStatus.NORMAL

    def test_status_opened(self, db):
        """已开封状态"""
        material = create_test_material(db, min_stock=5, open_validity_days=30)
        now = datetime.utcnow()
        item = create_test_inventory(
            db, material,
            quantity=10,
            original_expiry_days=180,
            open_time=now,
            opened=True
        )
        status = determine_status(item, now)
        assert status == InventoryStatus.OPENED

    def test_status_expired(self, db):
        """已过期状态"""
        material = create_test_material(db)
        item = create_test_inventory(db, material, quantity=10, original_expiry_days=-1)
        status = determine_status(item)
        assert status == InventoryStatus.EXPIRED

    def test_status_near_expiry(self, db):
        """近效期状态"""
        material = create_test_material(db)
        item = create_test_inventory(db, material, quantity=10, original_expiry_days=15)
        status = determine_status(item)
        assert status == InventoryStatus.NEAR_EXPIRY

    def test_status_low_stock(self, db):
        """低库存状态"""
        material = create_test_material(db, min_stock=10)
        item = create_test_inventory(db, material, quantity=3, original_expiry_days=180)
        status = determine_status(item)
        assert status == InventoryStatus.LOW_STOCK

    def test_status_used_up(self, db):
        """用完状态"""
        material = create_test_material(db)
        item = create_test_inventory(db, material, quantity=0, original_expiry_days=180)
        status = determine_status(item)
        assert status == InventoryStatus.USED_UP

    def test_status_scrapped_preserved(self, db):
        """已报废状态保持"""
        material = create_test_material(db)
        item = create_test_inventory(db, material, quantity=0, original_expiry_days=180)
        item.status = InventoryStatus.SCRAPPED
        status = determine_status(item)
        assert status == InventoryStatus.SCRAPPED


class TestUsageConstraints:
    """测试使用约束"""

    def test_can_use_normal(self, db):
        """正常库存可领用"""
        material = create_test_material(db)
        item = create_test_inventory(db, material, quantity=10, original_expiry_days=180)
        assert can_use(item) is True

    def test_cannot_use_expired(self, db):
        """已过期禁止领用"""
        material = create_test_material(db)
        item = create_test_inventory(db, material, quantity=10, original_expiry_days=-1)
        assert can_use(item) is False

    def test_cannot_use_scrapped(self, db):
        """已报废禁止领用"""
        material = create_test_material(db)
        item = create_test_inventory(db, material, quantity=10, original_expiry_days=180)
        item.status = InventoryStatus.SCRAPPED
        assert can_use(item) is False

    def test_cannot_use_zero_quantity(self, db):
        """零库存禁止领用"""
        material = create_test_material(db)
        item = create_test_inventory(db, material, quantity=0, original_expiry_days=180)
        assert can_use(item) is False
