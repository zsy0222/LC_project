"""活动广场：社团发布回收活动 → 用户参与拍照 → 获得碳积分"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Activity, ActivityJoin, User, ReuseItem, Batch

router = APIRouter(tags=["activity"])


def _activity_card(a: Activity, joined: bool = False, db: Session = None) -> dict:
    club_avatar_map = {
        "手工社": "ico_paper", "手艺社": "ico_paper", "美术社": "ico_gallery",
        "园艺社": "ico_sprout", "生物社": "ico_lightbulb", "创客空间": "ico_box",
        "环保社": "ico_recycle", "化学社": "ico_battery", "宠保社": "ico_food",
        "食监委": "ico_coin",
    }
    return {
        "id": a.id,
        "title": a.title,
        "club_name": a.club_name,
        "category": a.category,
        "description": a.description,
        "time_slot": a.time_slot,
        "location": a.location,
        "carbon_reward": a.carbon_reward,
        "max_participants": a.max_participants,
        "current_participants": a.current_participants,
        "status": a.status,
        "joined": joined,
        "club_icon": club_avatar_map.get(a.club_name, "ico_sprout"),
        "full_text": "已满" if a.current_participants >= a.max_participants else f"{a.current_participants}/{a.max_participants}",
    }


@router.get("/activities")
def list_activities(user_id: int | None = None, db: Session = Depends(get_db)):
    """活动广场列表"""
    activities = db.query(Activity).order_by(
        Activity.status == "ended",
        Activity.created_at.desc()
    ).all()

    joined_ids = set()
    if user_id:
        joins = db.query(ActivityJoin).filter(ActivityJoin.user_id == user_id).all()
        joined_ids = {j.activity_id for j in joins}

    return {
        "activities": [_activity_card(a, a.id in joined_ids, db) for a in activities],
    }


@router.post("/activities/{activity_id}/join")
def join_activity(activity_id: int, user_id: int, db: Session = Depends(get_db)):
    """参与活动"""
    a = db.query(Activity).get(activity_id)
    if not a:
        raise HTTPException(status_code=404, detail="活动不存在")
    if a.status == "ended":
        raise HTTPException(status_code=400, detail="活动已结束")
    if a.current_participants >= a.max_participants:
        a.status = "full"
        db.commit()
        raise HTTPException(status_code=400, detail="名额已满")

    exists = db.query(ActivityJoin).filter(
        ActivityJoin.activity_id == activity_id,
        ActivityJoin.user_id == user_id,
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="已参与过该活动")

    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    j = ActivityJoin(activity_id=activity_id, user_id=user_id)
    db.add(j)

    a.current_participants += 1
    if a.current_participants >= a.max_participants:
        a.status = "full"

    user.carbon_score = float(user.carbon_score or 0) + a.carbon_reward
    db.commit()

    return {
        "ok": True,
        "msg": f"成功参与「{a.title}」，获得 +{a.carbon_reward} kg 碳积分！",
        "carbon_earned": a.carbon_reward,
        "new_score": round(user.carbon_score, 3),
    }


@router.post("/activities/{activity_id}/upload")
def upload_activity_work(activity_id: int, user_id: int, photo: str, desc: str = "", db: Session = Depends(get_db)):
    """参与者在活动中上传自己的作品照片 → 进入个人成品橱窗"""
    # Verify joined
    joined = db.query(ActivityJoin).filter(
        ActivityJoin.activity_id == activity_id,
        ActivityJoin.user_id == user_id,
    ).first()
    if not joined:
        raise HTTPException(status_code=403, detail="请先参与该活动再上传作品")

    activity = db.query(Activity).get(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")

    # Create a ReuseItem in a special batch "ACTIVITY" so it shows in the gallery
    # Find or create the special batch
    batch_id = f"ACTIVITY-{activity_id}"
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        batch = Batch(
            id=batch_id,
            point_id=1,
            category=activity.category,
            status="done",
            destination="活动作品",
            claimed_by=None,
        )
        db.add(batch)
        db.flush()

    item = ReuseItem(
        batch_id=batch.id,
        reuser_id=user_id,
        product_photo=photo,
        product_desc=desc or f"我在「{activity.title}」的作品 ✨",
    )
    db.add(item)
    db.commit()

    return {
        "ok": True,
        "msg": "作品已上传！将出现在你的成品橱窗中",
        "product_photo": photo,
        "product_desc": item.product_desc,
    }


@router.post("/activities/create")
def create_activity(title: str, club_name: str, category: str, description: str,
                    time_slot: str, location: str, carbon_reward: float,
                    max_participants: int = 3, db: Session = Depends(get_db)):
    """去向端发布活动招募"""
    a = Activity(
        title=title, club_name=club_name, category=category,
        description=description, time_slot=time_slot, location=location,
        carbon_reward=carbon_reward, max_participants=max_participants,
    )
    db.add(a)
    db.commit()
    return {"ok": True, "msg": f"活动「{title}」发布成功！", "id": a.id}
