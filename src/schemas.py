"""Pydantic 请求/响应模型"""
from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


# ---------- 通用 ----------
class OkResp(BaseModel):
    ok: bool = True
    msg: str = "success"


# ---------- 用户 ----------
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nickname: str
    role: str
    carbon_score: float


# ---------- 点位 ----------
class PointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    qr_code: str
    name: str
    location: str


class ScanResp(BaseModel):
    point: PointOut
    server_time: datetime


# ---------- AI ----------
class PredictResp(BaseModel):
    category: str          # 外卖厨余 / 快递纸箱 / 塑料 / 有害
    grade: str = ""        # 纸箱用：完好/轻损/破损/受潮；厨余用：空
    score: float           # 置信度
    recommend: str = ""    # A / B / C
    recommend_desc: str = ""
    co2_estimate: float    # 减碳预估
    box_count: int = 1     # AI 识别的回收物数量（仅纸箱）
    need_recheck: bool     # 置信度过低时提示重拍


# ---------- 投递 ----------
class SubmissionCreate(BaseModel):
    user_id: int
    qr_code: str           # 点位二维码
    waste_type: str = "快递纸箱"  # 品类
    category: str = ""     # AI 识别结果
    grade: str = ""        # 完整度（纸箱）/ 空（其他）
    score: float = 0.0
    photo: str             # 已上传的照片 URL
    photo_hash: str = ""   # 感知哈希
    item_count: int = 1    # 物品数量
    user_lat: float = 0.0
    user_lng: float = 0.0

class SubmissionPending(BaseModel):
    """两步分离第一步：仅拍照，不校验GPS"""
    user_id: int
    waste_type: str        # 品类
    category: str = ""     # AI 识别结果
    score: float = 0.0
    photo: str             # 照片 URL
    photo_hash: str = ""
    item_count: int = 1

class SubmissionConfirm(BaseModel):
    """两步分离第二步：到达分类点，GPS校验"""
    user_id: int
    user_lat: float        # 用户经度
    user_lng: float        # 用户纬度
    qr_code: str           # 点位二维码
    confirmed: bool = True  # 用户勾选确认


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    batch_id: str
    photo: str
    ai_category: str
    ai_grade: Optional[str] = ""
    ai_score: float
    co2_saved: float
    photo_hash: str = ""
    item_count: int = 1
    status: str = "confirmed"
    waste_type: str = "快递纸箱"
    streak: int = 0
    streak_multiplier: float = 1.0
    streak_badge: Optional[str] = None
    is_today_first: bool = False
    ts: datetime


# ---------- 批次 ----------
class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    point_id: int
    date: date
    category: str
    status: str
    destination: Optional[str] = None


class BatchClaim(BaseModel):
    batch_id: str
    reuser_id: int
    destination: str       # A / B / C


class BatchReuse(BaseModel):
    batch_id: str
    reuser_id: int
    product_photo: str
    product_desc: str


# ---------- 故事页 ----------
class StoryFlow(BaseModel):
    ts: datetime
    title: str
    detail: str


class BatchStory(BaseModel):
    batch: BatchOut
    submissions_count: int
    total_co2: float
    flows: List[StoryFlow]
    reuse_photo: Optional[str] = None
    reuse_desc: Optional[str] = None


# ---------- 排行榜 ----------
class RankItem(BaseModel):
    rank: int
    user_id: int
    nickname: str
    carbon_score: float
    submission_count: int
