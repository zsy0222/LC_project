"""用户接口：资料、通知、徽章"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Submission, Notification

router = APIRouter(tags=["user"])


@router.get("/users")
def list_users(role: str | None = None, db: Session = Depends(get_db)):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    return [
        {"id": u.id, "nickname": u.nickname, "role": u.role,
         "carbon_score": round(u.carbon_score or 0, 3)}
        for u in q.all()
    ]


@router.get("/user/{user_id}/profile")
def profile(user_id: int, db: Session = Depends(get_db)):
    """个人主页：碳积分、投递数、徽章、近期通知"""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    sub_cnt = db.query(Submission).filter(Submission.user_id == user_id).count()
    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.ts.desc())
        .limit(20)
        .all()
    )

    # 徽章规则（演示）
    badges = []
    if sub_cnt >= 1:
        badges.append({"key": "first_box", "name": "环保萌新", "desc": "完成第一次投递"})
    if sub_cnt >= 5:
        badges.append({"key": "five_box", "name": "回收能手", "desc": "累计投递 5 次"})
    if (user.carbon_score or 0) >= 1.0:
        badges.append({"key": "co2_1kg", "name": "减碳 1kg", "desc": "累计减碳 ≥ 1 kg CO₂e"})

    return {
        "user": {
            "id": user.id, "nickname": user.nickname, "role": user.role,
            "carbon_score": round(user.carbon_score or 0, 3),
        },
        "submission_count": sub_cnt,
        "badges": badges,
        "notifications": [
            {"id": n.id, "batch_id": n.batch_id, "content": n.content,
             "read": n.read, "ts": n.ts.isoformat()}
            for n in notifs
        ],
    }


@router.post("/user/{user_id}/notifications/read_all")
def mark_all_read(user_id: int, db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.user_id == user_id, Notification.read.is_(False)
    ).update({Notification.read: True})
    db.commit()
    return {"ok": True}


def _compute_streak(user_id: int, today: date, db: Session) -> tuple[int, bool]:
    """统计连续打卡天数"""
    from sqlalchemy import func as sa_func
    from datetime import datetime as dt
    rows = (
        db.query(sa_func.date(Submission.ts))
        .filter(Submission.user_id == user_id, Submission.status == "confirmed")
        .distinct()
        .order_by(sa_func.date(Submission.ts).desc())
        .all()
    )
    dates = []
    for r in rows:
        v = r[0]
        if isinstance(v, str):
            dates.append(date.fromisoformat(v))
        elif isinstance(v, dt):
            dates.append(v.date())
        elif isinstance(v, date):
            dates.append(v)
    if not dates:
        return 0, True
    streak = 1
    for i in range(1, len(dates)):
        if (dates[i-1] - dates[i]).days == 1:
            streak += 1
        else:
            break
    if dates[0] == today:
        is_today_first = False
    else:
        if (today - dates[0]).days > 1:
            streak = 0
        is_today_first = True
    return streak, is_today_first


def _streak_multiplier(streak: int) -> float:
    if streak >= 30: return 1.5
    if streak >= 14: return 1.3
    if streak >= 7: return 1.2
    if streak >= 3: return 1.1
    return 1.0


def _streak_badge(streak: int) -> dict | None:
    if streak >= 30: return {"title": "零废弃大师", "multiplier": 1.5}
    if streak >= 14: return {"title": "分类高手", "multiplier": 1.3}
    if streak >= 7: return {"title": "分类达人", "multiplier": 1.2}
    if streak >= 3: return {"title": "分类新手", "multiplier": 1.1}
    if streak >= 1: return {"title": "初试分类", "multiplier": 1.0}
    return None


@router.get("/user/{user_id}/streak")
def get_streak(user_id: int, db: Session = Depends(get_db)):
    """查询用户连续打卡天数和倍率"""
    from datetime import date
    streak, is_first = _compute_streak(user_id, date.today(), db)
    return {
        "streak": streak,
        "multiplier": _streak_multiplier(streak),
        "badge": _streak_badge(streak),
        "is_today_first": is_first,
    }
