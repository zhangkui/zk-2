import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, UserRole
from app.auth import hash_password


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
        admin = User(
            username="testadmin",
            full_name="测试管理员",
            role=UserRole.ADMIN,
            hashed_password=hash_password("testpass123")
        )
        db.add(admin)
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "testadmin", "password": "testpass123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAuthAPI:
    def test_login_success(self, client):
        response = client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "testpass123"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(self, client):
        response = client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "wrongpass"}
        )
        assert response.status_code == 401

    def test_get_me(self, client, auth_headers):
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["username"] == "testadmin"


class TestMaterialAPI:
    def test_create_material(self, client, auth_headers):
        response = client.post(
            "/api/admin/materials",
            json={
                "code": "MAT001",
                "name": "乙醇",
                "category": "reagent",
                "specification": "500ml",
                "unit": "瓶",
                "manufacturer": "国药集团",
                "min_stock": 5,
                "open_validity_days": 30
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["code"] == "MAT001"

    def test_list_materials(self, client, auth_headers):
        self.test_create_material(client, auth_headers)
        response = client.get("/api/admin/materials", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1


class TestInventoryAPI:
    def _create_material(self, client, auth_headers):
        response = client.post(
            "/api/admin/materials",
            json={
                "code": "INV001",
                "name": "测试试剂",
                "category": "reagent",
                "specification": "100ml",
                "unit": "瓶",
                "manufacturer": "测试厂商",
                "min_stock": 2,
                "open_validity_days": 14
            },
            headers=auth_headers
        )
        return response.json()

    def test_create_inventory(self, client, auth_headers):
        material = self._create_material(client, auth_headers)
        response = client.post(
            "/api/inventory",
            json={
                "material_id": material["id"],
                "batch_no": "BATCH20240101",
                "quantity": 10,
                "original_expiry_date": "2030-12-31T23:59:59"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["batch_no"] == "BATCH20240101"
        assert response.json()["status"] == "normal"

    def test_open_inventory(self, client, auth_headers):
        material = self._create_material(client, auth_headers)
        inv_resp = client.post(
            "/api/inventory",
            json={
                "material_id": material["id"],
                "batch_no": "BATCH20240102",
                "quantity": 10,
                "original_expiry_date": "2030-12-31T23:59:59"
            },
            headers=auth_headers
        )
        item_id = inv_resp.json()["id"]
        response = client.post(
            f"/api/inventory/{item_id}/open",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["opened"] is True
        assert response.json()["open_time"] is not None

    def test_cannot_open_twice(self, client, auth_headers):
        material = self._create_material(client, auth_headers)
        inv_resp = client.post(
            "/api/inventory",
            json={
                "material_id": material["id"],
                "batch_no": "BATCH20240103",
                "quantity": 10,
                "original_expiry_date": "2030-12-31T23:59:59"
            },
            headers=auth_headers
        )
        item_id = inv_resp.json()["id"]
        client.post(f"/api/inventory/{item_id}/open", json={}, headers=auth_headers)
        response = client.post(
            f"/api/inventory/{item_id}/open",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_outbound_inventory(self, client, auth_headers):
        material = self._create_material(client, auth_headers)
        inv_resp = client.post(
            "/api/inventory",
            json={
                "material_id": material["id"],
                "batch_no": "BATCH20240104",
                "quantity": 10,
                "original_expiry_date": "2030-12-31T23:59:59"
            },
            headers=auth_headers
        )
        item_id = inv_resp.json()["id"]
        response = client.post(
            f"/api/inventory/{item_id}/outbound",
            json={
                "inventory_item_id": item_id,
                "operation_type": "outbound",
                "quantity_change": 3,
                "remark": "测试领用"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["quantity"] == 7

    def test_cannot_outbound_expired(self, client, auth_headers):
        material = self._create_material(client, auth_headers)
        inv_resp = client.post(
            "/api/inventory",
            json={
                "material_id": material["id"],
                "batch_no": "BATCH20240105",
                "quantity": 10,
                "original_expiry_date": "2020-01-01T23:59:59"
            },
            headers=auth_headers
        )
        item_id = inv_resp.json()["id"]
        response = client.post(
            f"/api/inventory/{item_id}/outbound",
            json={
                "inventory_item_id": item_id,
                "operation_type": "outbound",
                "quantity_change": 1
            },
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_scrap_inventory(self, client, auth_headers):
        material = self._create_material(client, auth_headers)
        inv_resp = client.post(
            "/api/inventory",
            json={
                "material_id": material["id"],
                "batch_no": "BATCH20240106",
                "quantity": 10,
                "original_expiry_date": "2030-12-31T23:59:59"
            },
            headers=auth_headers
        )
        item_id = inv_resp.json()["id"]
        response = client.post(
            f"/api/inventory/{item_id}/scrap",
            json={
                "inventory_item_id": item_id,
                "operation_type": "scrap",
                "quantity_change": 10,
                "remark": "测试报废"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "scrapped"


class TestWarningAPI:
    def test_dashboard_stats(self, client, auth_headers):
        response = client.get("/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_materials" in data
        assert "total_warnings" in data
        assert "near_expiry_count" in data

    def test_list_warnings(self, client, auth_headers):
        response = client.get("/api/warnings", headers=auth_headers)
        assert response.status_code == 200
