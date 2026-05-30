"""广播通知服务：批次完成后向所有投递用户推送反馈"""
from sqlalchemy.orm import Session

from ..models import Notification, Submission


def broadcast_reuse(db: Session, batch_id: str, content: str) -> int:
    """向该批次所有投递用户群发通知；返回推送条数"""
    user_ids = (
        db.query(Submission.user_id)
        .filter(Submission.batch_id == batch_id)
        .distinct()
        .all()
    )
    cnt = 0
    for (uid,) in user_ids:
        n = Notification(user_id=uid, batch_id=batch_id, content=content)
        db.add(n)
        cnt += 1
    db.commit()
    return cnt
