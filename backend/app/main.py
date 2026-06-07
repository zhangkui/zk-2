from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
import time
import logging

from app.database import Base, engine, SessionLocal
from app.models import User, UserRole, SystemConfig, Material, InventoryItem
from app.auth import hash_password
from app.config import settings
from app.utils import scan_all_warnings

from app.routers import auth, admin, inventory, monitoring, stocktake

logger = logging.getLogger(__name__)


def wait_for_db(max_retries: int = 10, retry_interval: int = 3):
    """等待数据库连接就绪"""
    from sqlalchemy import text
    retries = 0
    while retries < max_retries:
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            logger.info("Database connection established successfully")
            return True
        except Exception as e:
            retries += 1
            logger.warning(f"Database connection attempt {retries}/{max_retries} failed: {e}")
            if retries < max_retries:
                time.sleep(retry_interval)
    logger.error("Failed to connect to database after multiple attempts")
    return False


def init_data():
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                full_name="系统管理员",
                email="admin@example.com",
                role=UserRole.ADMIN,
                hashed_password=hash_password("admin123")
            )
            db.add(admin_user)

        operator_user = db.query(User).filter(User.username == "operator").first()
        if not operator_user:
            operator_user = User(
                username="operator",
                full_name="操作员",
                email="operator@example.com",
                role=UserRole.OPERATOR,
                hashed_password=hash_password("operator123")
            )
            db.add(operator_user)

        viewer_user = db.query(User).filter(User.username == "viewer").first()
        if not viewer_user:
            viewer_user = User(
                username="viewer",
                full_name="查看员",
                email="viewer@example.com",
                role=UserRole.VIEWER,
                hashed_password=hash_password("viewer123")
            )
            db.add(viewer_user)

        configs = [
            {"key": "warning_days_near_expiry", "value": str(settings.WARNING_DAYS_NEAR_EXPIRY), "desc": "近效期预警天数"},
            {"key": "auto_scan_interval_minutes", "value": "60", "desc": "自动预警扫描间隔(分钟)"},
        ]
        for cfg in configs:
            existing = db.query(SystemConfig).filter(SystemConfig.config_key == cfg["key"]).first()
            if not existing:
                db.add(SystemConfig(
                    config_key=cfg["key"],
                    config_value=cfg["value"],
                    description=cfg["desc"]
                ))

        db.commit()
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: scan_all_warnings(SessionLocal()),
        'interval',
        minutes=60,
        id='warning_scan'
    )
    scheduler.start()
    return scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    init_data()
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="试剂/耗材效期追踪系统 API",
    description="实验室试剂与耗材效期管理系统后端接口",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(stocktake.router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
