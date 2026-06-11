"""ORM 模型：对应设计文档 7 张表"""
from datetime import datetime, date

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    """用户：投递者 / 去向端 / 管理员"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    openid = Column(String(64), unique=True, index=True)
    nickname = Column(String(64))
    role = Column(String(16), default="student")  # student / reuser / admin
    carbon_score = Column(Float, default=0.0)     # 累计减碳量 kg CO2e
    password_hash = Column(String(128), nullable=True)  # NULL=NPC游客
    created_at = Column(DateTime, default=datetime.utcnow)

    submissions = relationship("Submission", back_populates="user")
    notifications = relationship("Notification", back_populates="user")


class Point(Base):
    """回收点位"""
    __tablename__ = "points"

    id = Column(Integer, primary_key=True)
    qr_code = Column(String(64), unique=True, index=True)
    name = Column(String(64))
    location = Column(String(128))
    gps = Column(String(64))

    batches = relationship("Batch", back_populates="point")


class Batch(Base):
    """批次：按 点位 + 日期 + 品类 归集"""
    __tablename__ = "batches"

    id = Column(String(64), primary_key=True)          # BATCH-A03-20260528-纸箱
    point_id = Column(Integer, ForeignKey("points.id"))
    date = Column(Date, default=date.today)
    category = Column(String(16))                       # 纸箱 / 塑料 / 玻璃
    status = Column(String(16), default="pending")      # pending / claimed / done
    destination = Column(String(32))                    # 处理路径
    claimed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 认领人
    created_at = Column(DateTime, default=datetime.utcnow)

    point = relationship("Point", back_populates="batches")
    submissions = relationship("Submission", back_populates="batch")
    reuse_items = relationship("ReuseItem", back_populates="batch")


class Submission(Base):
    """单次投递记录"""
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    batch_id = Column(String(64), ForeignKey("batches.id"))
    photo = Column(String(256))
    ai_category = Column(String(16))
    ai_grade = Column(String(16))
    ai_score = Column(Float)
    co2_saved = Column(Float, default=0.0)
    photo_hash = Column(String(64), default="")     # 感知哈希，用于相似度去重
    item_count = Column(Integer, default=1)          # 照片中回收物数量
    status = Column(String(16), default="confirmed")  # pending / confirmed / expired
    waste_type = Column(String(16), default="快递纸箱")  # 外卖厨余 / 快递纸箱 / 塑料 / 有害
    ts = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="submissions")
    batch = relationship("Batch", back_populates="submissions")


class ReuseItem(Base):
    """成品反馈（去向端上传）"""
    __tablename__ = "reuse_items"

    id = Column(Integer, primary_key=True)
    batch_id = Column(String(64), ForeignKey("batches.id"))
    reuser_id = Column(Integer, ForeignKey("users.id"))
    product_photo = Column(String(256))
    product_desc = Column(String(256))
    featured = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("Batch", back_populates="reuse_items")


class Notification(Base):
    """成品反馈推送"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    batch_id = Column(String(64), ForeignKey("batches.id"))
    content = Column(String(256))
    read = Column(Boolean, default=False)
    ts = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")


class CarbonFactor(Base):
    """碳因子表（环保专业维护）"""
    __tablename__ = "carbon_factors"

    id = Column(Integer, primary_key=True)
    category = Column(String(16))
    path = Column(String(16))         # Reuse / Recycle
    factor = Column(Float)            # kg CO2e / 件
    source = Column(String(128))


class ShopOrder(Base):
    """商城兑换记录"""
    __tablename__ = "shop_orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    item_id = Column(String(16))
    item_name = Column(String(64))
    price = Column(Float)
    address = Column(String(128))
    status = Column(String(16), default="pending")   # pending / received
    created_at = Column(DateTime, default=datetime.utcnow)


class Activity(Base):
    """社团回收活动"""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True)
    title = Column(String(128))
    club_name = Column(String(64))
    category = Column(String(16))
    description = Column(String(256))
    time_slot = Column(String(64))          # e.g. "6/8 14:00-16:00"
    location = Column(String(128))
    carbon_reward = Column(Float, default=0.3)  # kg CO₂ per join
    max_participants = Column(Integer, default=20)
    current_participants = Column(Integer, default=0)
    status = Column(String(16), default="open")  # open / full / ended
    created_at = Column(DateTime, default=datetime.utcnow)


class ActivityJoin(Base):
    """用户参与活动记录"""
    __tablename__ = "activity_joins"

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey("activities.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    uploaded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
