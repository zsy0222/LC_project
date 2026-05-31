"""投递记录接口（含反作弊：定位校验 / 30s 冷却 / 图片相似度去重 / 多物品计数）"""
import math
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import (
    LOCATION_MAX_DISTANCE_M, COOLDOWN_SECONDS,
    PHOTO_SIMILARITY_THRESHOLD, PHOTO_SIMILARITY_RECENT_HOURS,
    ITEM_COUNT_MIN, ITEM_COUNT_MAX, DEMO_MODE,
)
from datetime import date as date_type
from ..database import get_db
from ..models import Point, User, Submission
from ..schemas import SubmissionCreate, SubmissionOut, SubmissionPending, SubmissionConfirm
from ..services.batch_service import get_or_create_batch
from ..services.carbon_service import calc_co2
from ..services.ai_service import compute_photo_hash, is_similar_to_recent
from ..api.user import _compute_streak, _streak_multiplier, _streak_badge

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

    # ---- 2. 定位校验（Demo 模式跳过） ----
    if not DEMO_MODE:
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
    # 仅比对同品类的近期提交（不同品类不可能相似）
    similarity_cutoff = datetime.utcnow() - timedelta(hours=PHOTO_SIMILARITY_RECENT_HOURS)
    recent_subs = (
        db.query(Submission)
        .filter(
            Submission.user_id == user.id,
            Submission.waste_type == data.waste_type,
            Submission.ts >= similarity_cutoff,
        )
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
                detail=f"疑似重复投递：与您近期提交的回收物相似度达 {sim_pct * 100:.0f}%，请投放新的回收物品",
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
    # 打卡倍率
    streak, is_today_first = _compute_streak(user.id, date_type.today(), db)
    multiplier = _streak_multiplier(streak) if is_today_first else _streak_multiplier(max(0, streak - 1) if not is_today_first else streak)
    if is_today_first: streak += 1  # 今天首次，计入新一天
    final_multiplier = _streak_multiplier(streak)
    bonus_co2 = round(total_co2 * (final_multiplier - 1.0), 3)
    badge = _streak_badge(streak)
    db.add(sub)
    user.carbon_score = float(user.carbon_score or 0) + total_co2 + bonus_co2
    db.commit()
    db.refresh(sub)
    # 注入打卡信息到响应
    sub.streak = streak
    sub.streak_multiplier = final_multiplier
    sub.streak_badge = badge["title"] if badge else None
    sub.is_today_first = is_today_first
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


@router.post("/submission/pending", response_model=SubmissionOut)
def create_pending(data: SubmissionPending, db: Session = Depends(get_db)):
    """两步分离第一步：外卖厨余拍照，不限地点，只创建 pending 记录"""
    user = db.query(User).get(data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    sub = Submission(
        user_id=user.id,
        batch_id="PENDING",
        photo=data.photo,
        ai_category=data.category,
        ai_grade="",
        ai_score=data.score,
        photo_hash=data.photo_hash,
        item_count=max(1, data.item_count),
        status="pending",
        waste_type=data.waste_type,
        co2_saved=0.0,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.post("/submission/{sub_id}/confirm", response_model=SubmissionOut)
def confirm_submission(sub_id: int, data: SubmissionConfirm, db: Session = Depends(get_db)):
    """两步分离第二步：到达分类点，GPS校验通过后确认投递"""
    sub = db.query(Submission).get(sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="记录不存在")
    if sub.user_id != data.user_id:
        raise HTTPException(status_code=403, detail="无权操作他人记录")
    if sub.status != "pending":
        raise HTTPException(status_code=400, detail=f"记录状态为 {sub.status}，不可确认")

    # 此处定位逻辑与 create_submission 相同，不重复校验
    point = db.query(Point).filter(Point.qr_code == data.qr_code).first()
    if not point:
        raise HTTPException(status_code=404, detail="点位不存在")

    if not DEMO_MODE:
        point_lat, point_lng = _parse_gps(point.gps)
        if point_lat and point_lng and data.user_lat and data.user_lng:
            dist = _haversine(data.user_lat, data.user_lng, point_lat, point_lng)
            if dist > LOCATION_MAX_DISTANCE_M:
                raise HTTPException(
                    status_code=400,
                    detail=f"定位校验失败：距回收点 {dist:.0f} 米（限制 {LOCATION_MAX_DISTANCE_M} 米）",
                )

    # 归入批次
    batch = get_or_create_batch(db, point, sub.ai_category or sub.waste_type, "")
    co2 = calc_co2(db, sub.ai_category or sub.waste_type, batch.destination or "C")
    total_co2 = round(co2 * sub.item_count, 3)

    sub.batch_id = batch.id
    sub.co2_saved = total_co2
    sub.status = "confirmed"
    user = db.query(User).get(data.user_id)
    # 打卡倍率
    streak, is_today_first = _compute_streak(user.id, date_type.today(), db) if user else (0, True)
    if is_today_first: streak += 1
    final_multiplier = _streak_multiplier(streak)
    bonus_co2 = round(total_co2 * (final_multiplier - 1.0), 3)
    badge = _streak_badge(streak)
    if user:
        user.carbon_score = float(user.carbon_score or 0) + total_co2 + bonus_co2
    db.commit()
    db.refresh(sub)
    # 注入打卡信息
    sub.streak = streak
    sub.streak_multiplier = final_multiplier
    sub.streak_badge = badge["title"] if badge else None
    sub.is_today_first = is_today_first
    return sub


@router.get("/submission/pending/{user_id}")
def list_pending(user_id: int, db: Session = Depends(get_db)):
    """查询用户待确认列表，超过24小时自动过期"""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    rows = (
        db.query(Submission)
        .filter(
            Submission.user_id == user_id,
            Submission.status == "pending",
            Submission.ts >= cutoff,
        )
        .order_by(Submission.ts.desc())
        .all()
    )
    # 过期处理
    expired = (
        db.query(Submission)
        .filter(
            Submission.user_id == user_id,
            Submission.status == "pending",
            Submission.ts < cutoff,
        )
        .all()
    )
    for s in expired:
        s.status = "expired"
    if expired:
        db.commit()

    return [
        {
            "id": s.id, "waste_type": s.waste_type, "category": s.ai_category,
            "photo": s.photo, "item_count": s.item_count,
            "ts": s.ts.isoformat(), "status": s.status,
        }
        for s in rows
    ]
