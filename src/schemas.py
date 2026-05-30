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
    category: str          # 纸箱 / 塑料 / 玻璃
    grade: str             # 完好 / 轻损 / 破损 / 受潮
    score: float           # 置信度
    recommend: str         # A / B / C
    recommend_desc: str
    co2_estimate: float    # 减碳预估（已含数量叠加）
    box_count: int = 1     # AI 识别的回收物数量
    need_recheck: bool     # 置信度过低时提示重拍


# ---------- 投递 ----------
class SubmissionCreate(BaseModel):
    user_id: int
    qr_code: str           # 点位二维码
    category: str
    grade: str
    score: float
    photo: str             # 已上传的照片 URL
    photo_hash: str = ""   # 感知哈希（前端计算）
    item_count: int = 1    # 照片中回收物数量
    user_lat: float = 0.0  # 用户当前纬度
    user_lng: float = 0.0  # 用户当前经度


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    batch_id: str
    photo: str
    ai_category: str
    ai_grade: str
    ai_score: float
    co2_saved: float
    photo_hash: str = ""
    item_count: int = 1
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
