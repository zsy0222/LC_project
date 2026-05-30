"""用户接口：资料、通知、徽章"""
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
