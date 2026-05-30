"""排行榜接口"""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Submission
from ..schemas import RankItem

router = APIRouter(tags=["rank"])


@router.get("/rank", response_model=list[RankItem])
def rank(top: int = 20, db: Session = Depends(get_db)):
    """按累计减碳量降序"""
    sub_cnt = dict(
        db.query(Submission.user_id, func.count(Submission.id))
        .group_by(Submission.user_id)
        .all()
    )
    rows = (
        db.query(User)
        .filter(User.role == "student")
        .order_by(User.carbon_score.desc())
        .limit(top)
        .all()
    )
    return [
        RankItem(
            rank=i + 1,
            user_id=u.id,
            nickname=u.nickname,
            carbon_score=round(u.carbon_score or 0, 3),
            submission_count=sub_cnt.get(u.id, 0),
        )
        for i, u in enumerate(rows)
    ]
