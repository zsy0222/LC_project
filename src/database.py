"""数据库连接与会话"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import DB_URL

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依赖：提供数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化所有表，并执行轻量迁移（新增列）"""
    from . import models  # noqa: F401 触发表注册
    Base.metadata.create_all(bind=engine)

    # 轻量迁移：为已有数据库补充新增列
    from sqlalchemy import text, inspect
    insp = inspect(engine)
    if insp.has_table("users"):
        cols = {c["name"] for c in insp.get_columns("users")}
        with engine.connect() as conn:
            if "password_hash" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(128)"))
            conn.commit()
    if insp.has_table("reuse_items"):
        cols = {c["name"] for c in insp.get_columns("reuse_items")}
        with engine.connect() as conn:
            if "featured" not in cols:
                conn.execute(text("ALTER TABLE reuse_items ADD COLUMN featured BOOLEAN DEFAULT 0"))
            conn.commit()
    if insp.has_table("submissions"):
        cols = {c["name"] for c in insp.get_columns("submissions")}
        with engine.connect() as conn:
            if "photo_hash" not in cols:
                conn.execute(text("ALTER TABLE submissions ADD COLUMN photo_hash VARCHAR(64) DEFAULT ''"))
            if "item_count" not in cols:
                conn.execute(text("ALTER TABLE submissions ADD COLUMN item_count INTEGER DEFAULT 1"))
            if "status" not in cols:
                conn.execute(text("ALTER TABLE submissions ADD COLUMN status VARCHAR(16) DEFAULT 'confirmed'"))
            if "waste_type" not in cols:
                conn.execute(text("ALTER TABLE submissions ADD COLUMN waste_type VARCHAR(16) DEFAULT '快递纸箱'"))
            conn.commit()
