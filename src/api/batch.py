"""批次接口：列表 / 认领 / 上传成品 / 故事页"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Batch, User, ReuseItem, Submission
from ..schemas import (
    BatchOut, BatchClaim, BatchReuse, OkResp,
    BatchStory, StoryFlow,
)
from ..config import PATH_DESC
from ..services.notify_service import broadcast_reuse

router = APIRouter(tags=["batch"])


@router.get("/batches")
def list_batches(status: str | None = None, category: str | None = None,
                 db: Session = Depends(get_db)):
    q = db.query(Batch)
    if status:
        q = q.filter(Batch.status == status)
    if category:
        q = q.filter(Batch.category == category)
    return [
        BatchOut.model_validate(b).model_dump(mode="json")
        for b in q.order_by(Batch.created_at.desc()).all()
    ]


@router.post("/batch/claim", response_model=OkResp)
def claim_batch(data: BatchClaim, db: Session = Depends(get_db)):
    """去向端认领批次"""
    batch = db.query(Batch).get(data.batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    if batch.status != "pending":
        raise HTTPException(status_code=400, detail=f"批次当前状态: {batch.status}，不可认领")

    reuser = db.query(User).get(data.reuser_id)
    if not reuser or reuser.role not in ("reuser", "admin"):
        raise HTTPException(status_code=403, detail="仅去向端/管理员可认领")

    batch.status = "claimed"
    batch.destination = data.destination
    db.commit()
    return OkResp(msg=f"批次 {batch.id} 已认领，去向 {PATH_DESC.get(data.destination, data.destination)}")


@router.post("/batch/reuse", response_model=OkResp)
def reuse_batch(data: BatchReuse, db: Session = Depends(get_db)):
    """去向端上传成品照片，触发反馈广播"""
    batch = db.query(Batch).get(data.batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    if batch.status not in ("claimed", "pending"):
        raise HTTPException(status_code=400, detail=f"批次状态 {batch.status} 不可上传成品")

    reuser = db.query(User).get(data.reuser_id)
    if not reuser or reuser.role not in ("reuser", "admin"):
        raise HTTPException(status_code=403, detail="仅去向端/管理员可上传成品")

    item = ReuseItem(
        batch_id=batch.id,
        reuser_id=reuser.id,
        product_photo=data.product_photo,
        product_desc=data.product_desc,
    )
    db.add(item)
    batch.status = "done"
    db.commit()

    # 广播给该批次全部投递用户
    cnt = broadcast_reuse(
        db,
        batch.id,
        f"你参与的批次「{batch.id}」已完成再生：{data.product_desc}",
    )
    return OkResp(msg=f"成品上传成功，已通知 {cnt} 位投递用户")


@router.get("/batch/{batch_id}/story", response_model=BatchStory)
def batch_story(batch_id: str, db: Session = Depends(get_db)):
    """批次故事时间轴"""
    batch = db.query(Batch).get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    subs = db.query(Submission).filter(Submission.batch_id == batch_id).all()
    total_co2 = round(sum(s.co2_saved or 0 for s in subs), 3)

    flows: list[StoryFlow] = [
        StoryFlow(
            ts=batch.created_at,
            title="批次创建",
            detail=f"在「{batch.point.name}」归集 {batch.category}",
        )
    ]
    for s in subs:
        flows.append(StoryFlow(
            ts=s.ts,
            title="用户投递",
            detail=f"{s.user.nickname} 投入 {s.ai_category}（{s.ai_grade}，置信度 {s.ai_score}）",
        ))

    if batch.status in ("claimed", "done"):
        flows.append(StoryFlow(
            ts=batch.created_at,
            title="批次被认领",
            detail=f"去向：{PATH_DESC.get(batch.destination or '', batch.destination or '')}",
        ))

    reuse_photo = None
    reuse_desc = None
    item = (
        db.query(ReuseItem)
        .filter(ReuseItem.batch_id == batch_id)
        .order_by(ReuseItem.created_at.desc())
        .first()
    )
    if item:
        reuse_photo = item.product_photo
        reuse_desc = item.product_desc
        flows.append(StoryFlow(
            ts=item.created_at,
            title="成品反馈",
            detail=item.product_desc,
        ))

    flows.sort(key=lambda x: x.ts)
    return BatchStory(
        batch=BatchOut.model_validate(batch),
        submissions_count=len(subs),
        total_co2=total_co2,
        flows=flows,
        reuse_photo=reuse_photo,
        reuse_desc=reuse_desc,
    )
