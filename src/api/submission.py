"""投递记录接口（含反作弊：定位校验 / 30s 冷却 / 图片相似度去重 / 多物品计数）"""
import math
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import (
    LOCATION_MAX_DISTANCE_M, COOLDOWN_SECONDS,
    PHOTO_SIMILARITY_THRESHOLD, PHOTO_SIMILARITY_RECENT,
    ITEM_COUNT_MIN, ITEM_COUNT_MAX,
)
from ..database import get_db
from ..models import Point, User, Submission
from ..schemas import SubmissionCreate, SubmissionOut
from ..services.batch_service import get_or_create_batch
from ..services.carbon_service import calc_co2
from ..services.ai_service import compute_photo_hash, is_similar_to_recent

router = APIRouter(tags=["submission"])


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两点间距离（米），使用 Haversine 公式"""
    r = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_gps(gps_str: str | None) -> tuple[float, float]:
    """解析点位 GPS 字符串 'lat,lng' → (lat, lng)"""
    if not gps_str:
        return 0.0, 0.0
    try:
        parts = gps_str.split(",")
        return float(parts[0]), float(parts[1])
    except (ValueError, IndexError):
        return 0.0, 0.0


@router.post("/submission", response_model=SubmissionOut)
def create_submission(data: SubmissionCreate, db: Session = Depends(get_db)):
    """提交一次投递：含定位校验 + 冷却检查 + 图片去重 + 多物品减碳"""

    # ---- 1. 基础校验 ----
    point = db.query(Point).filter(Point.qr_code == data.qr_code).first()
    if not point:
        raise HTTPException(status_code=404, detail="点位不存在")
    user = db.query(User).get(data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # ---- 2. 定位校验 ----
    point_lat, point_lng = _parse_gps(point.gps)
    if point_lat and point_lng and data.user_lat and data.user_lng:
        dist = _haversine(data.user_lat, data.user_lng, point_lat, point_lng)
        if dist > LOCATION_MAX_DISTANCE_M:
            raise HTTPException(
                status_code=400,
                detail=f"定位校验失败：您距回收点约 {dist:.0f} 米（最大允许 {LOCATION_MAX_DISTANCE_M} 米），请到达点位后再投递",
            )

    # ---- 3. 30s 冷却检查（同点位） ----
    cutoff = datetime.utcnow() - timedelta(seconds=COOLDOWN_SECONDS)
    recent_at_point = (
        db.query(Submission)
        .filter(
            Submission.user_id == user.id,
            Submission.batch_id.like(f"%{point.qr_code}%"),
            Submission.ts >= cutoff,
        )
        .first()
    )
    if recent_at_point:
        remain = COOLDOWN_SECONDS - max(0, (datetime.utcnow() - recent_at_point.ts).total_seconds())
        raise HTTPException(
            status_code=429,
            detail=f"请勿频繁投递：同一回收点需间隔 {COOLDOWN_SECONDS} 秒（剩余 {remain:.0f} 秒）",
        )

    # ---- 4. 图片相似度去重 ----
    # 获取用户最近 10 条提交的 photo_hash
    recent_subs = (
        db.query(Submission)
        .filter(Submission.user_id == user.id)
        .order_by(Submission.ts.desc())
        .limit(PHOTO_SIMILARITY_RECENT)
        .all()
    )
    recent_hashes = [s.photo_hash for s in recent_subs if s.photo_hash]

    # 如果前端未传 hash，后端计算
    photo_hash = data.photo_hash
    if not photo_hash and data.photo:
        try:
            import requests
            resp = requests.get(f"http://127.0.0.1:8000{data.photo}", timeout=5)
            photo_hash = compute_photo_hash(resp.content)
        except Exception:
            photo_hash = ""

    if photo_hash:
        too_similar, sim_pct = is_similar_to_recent(photo_hash, recent_hashes, PHOTO_SIMILARITY_THRESHOLD)
        if too_similar:
            raise HTTPException(
                status_code=400,
                detail=f"疑似重复投递：与您近期提交的回收物相似度达 {sim_pct * 100:.0f}%，请拍摄不同角度的回收物或更换物品",
            )

    # ---- 5. 归入批次 + 计算碳减排 ----
    item_count = max(ITEM_COUNT_MIN, min(data.item_count, ITEM_COUNT_MAX))
    batch = get_or_create_batch(db, point, data.category, data.grade)
    co2_per_item = calc_co2(db, data.category, batch.destination or "C")
    total_co2 = round(co2_per_item * item_count, 3)

    sub = Submission(
        user_id=user.id,
        batch_id=batch.id,
        photo=data.photo,
        ai_category=data.category,
        ai_grade=data.grade,
        ai_score=data.score,
        co2_saved=total_co2,
        photo_hash=photo_hash,
        item_count=item_count,
    )
    db.add(sub)
    user.carbon_score = float(user.carbon_score or 0) + total_co2
    db.commit()
    db.refresh(sub)
    return sub


@router.get("/user/{user_id}/submissions")
def list_user_submissions(user_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(Submission)
        .filter(Submission.user_id == user_id)
        .order_by(Submission.ts.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "batch_id": s.batch_id,
            "photo": s.photo,
            "category": s.ai_category,
            "grade": s.ai_grade,
            "score": s.ai_score,
            "co2_saved": s.co2_saved,
            "item_count": s.item_count,
            "ts": s.ts.isoformat(),
        }
        for s in rows
    ]


@router.get("/submission/cooldown")
def check_cooldown(user_id: int, qr_code: str, db: Session = Depends(get_db)):
    """查询用户在某点位的冷却剩余时间"""
    point = db.query(Point).filter(Point.qr_code == qr_code).first()
    if not point:
        raise HTTPException(status_code=404, detail="点位不存在")
    cutoff = datetime.utcnow() - timedelta(seconds=COOLDOWN_SECONDS)
    recent = (
        db.query(Submission)
        .filter(
            Submission.user_id == user_id,
            Submission.batch_id.like(f"%{qr_code}%"),
            Submission.ts >= cutoff,
        )
        .order_by(Submission.ts.desc())
        .first()
    )
    if not recent:
        return {"cooldown": False, "remain_seconds": 0}
    elapsed = (datetime.utcnow() - recent.ts).total_seconds()
    remain = max(0, COOLDOWN_SECONDS - elapsed)
    return {"cooldown": True if remain > 0 else False, "remain_seconds": round(remain, 1)}
