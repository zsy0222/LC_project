"""成果展示 + 回收物追踪 + 碳积分奖励"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import User, Submission, Batch, ReuseItem, Notification, Point

router = APIRouter(tags=["reward"])

REWARD_THRESHOLD = 20  # 累计投递多少次触发实物奖励


@router.get("/user/{user_id}/tracking")
def user_tracking(user_id: int, db: Session = Depends(get_db)):
    """用户参与的批次追踪——物流进度条数据"""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 获取用户所有已确认的投递，按批次分组
    subs = (
        db.query(Submission)
        .filter(Submission.user_id == user_id, Submission.status == "confirmed")
        .order_by(Submission.ts.desc())
        .limit(30)
        .all()
    )

    if not subs:
        return {"items": [], "stats": {"total_submissions": 0, "batches_claimed": 0, "batches_done": 0}}

    # 按批次分组
    batch_ids = list(set(s.batch_id for s in subs if s.batch_id and s.batch_id != "PENDING"))
    batches = {b.id: b for b in db.query(Batch).filter(Batch.id.in_(batch_ids)).all()} if batch_ids else {}

    # 获取成品
    done_batch_ids = [bid for bid, b in batches.items() if b.status == "done"]
    reuse_items = {}
    if done_batch_ids:
        items = db.query(ReuseItem).filter(ReuseItem.batch_id.in_(done_batch_ids)).all()
        for item in items:
            if item.batch_id not in reuse_items:
                reuse_items[item.batch_id] = item

    items_out = []
    seen_batches = set()
    for s in subs:
        bid = s.batch_id
        if not bid or bid == "PENDING" or bid in seen_batches:
            continue
        seen_batches.add(bid)

        batch = batches.get(bid)
        if not batch:
            continue

        # 计算进度阶段: 1=投递 2=归入批次 3=被认领 4=成品反馈
        stages = [
            {"key": "submitted", "label": "📸 投递", "done": True,
             "detail": f"{s.ai_category or s.waste_type} · {datetime.strftime(s.ts, '%m-%d %H:%M') if s.ts else ''}"},
            {"key": "batched", "label": "📦 归入批次", "done": True,
             "detail": f"批次 {bid}"},
            {"key": "claimed", "label": "🤝 被认领", "done": batch.status in ("claimed", "done"),
             "detail": f"去向: {batch.destination or '待认领'}"},
            {"key": "done", "label": "🎁 成品反馈", "done": batch.status == "done",
             "detail": ""},
        ]

        # 成品详情
        reuse = reuse_items.get(bid)
        if reuse:
            stages[-1]["detail"] = reuse.product_desc or "已生成成品"
            stages[-1]["photo"] = reuse.product_photo

        current_stage = 1
        if batch.status == "pending":
            current_stage = 2
        elif batch.status == "claimed":
            current_stage = 3
        elif batch.status == "done":
            current_stage = 4

        items_out.append({
            "batch_id": bid,
            "category": batch.category,
            "destination": batch.destination,
            "current_stage": current_stage,
            "stages": stages,
            "has_product": bool(reuse),
            "product_photo": reuse.product_photo if reuse else None,
            "product_desc": reuse.product_desc if reuse else None,
        })

    # 统计
    done_count = sum(1 for b in batches.values() if b.status == "done")
    claimed_count = sum(1 for b in batches.values() if b.status == "claimed")

    return {
        "items": items_out,
        "stats": {
            "total_submissions": len(subs),
            "batches_total": len(batches),
            "batches_claimed": claimed_count,
            "batches_done": done_count,
        },
    }


@router.get("/gallery")
def product_gallery(user_id: int | None = None, db: Session = Depends(get_db)):
    """成品橱窗——所有已完成的成品照片"""
    done_batches = db.query(Batch).filter(Batch.status == "done").order_by(Batch.created_at.desc()).limit(30).all()
    if not done_batches:
        return {"items": []}

    batch_ids = [b.id for b in done_batches]
    reuse_items = {
        r.batch_id: r
        for r in db.query(ReuseItem).filter(ReuseItem.batch_id.in_(batch_ids)).all()
    }

    # 查找当前用户投递过的批次
    my_batch_ids = set()
    if user_id:
        my_subs = db.query(Submission).filter(
            Submission.user_id == user_id,
            Submission.status == "confirmed",
            Submission.batch_id.in_(batch_ids),
        ).all()
        my_batch_ids = set(s.batch_id for s in my_subs)

    items = []
    for b in done_batches:
        r = reuse_items.get(b.id)
        if not r:
            continue
        reuser = db.query(User).get(r.reuser_id) if r.reuser_id else None
        items.append({
            "batch_id": b.id,
            "category": b.category,
            "destination": b.destination,
            "product_photo": r.product_photo,
            "product_desc": r.product_desc,
            "reuser_name": reuser.nickname if reuser else "去向端",
            "date": datetime.strftime(r.created_at, "%Y-%m-%d") if r.created_at else "",
            "is_mine": b.id in my_batch_ids,
        })

    return {"items": items}


@router.get("/user/{user_id}/reward-status")
def reward_status(user_id: int, db: Session = Depends(get_db)):
    """碳积分奖励进度——累计投递满 N 次可领实体成品"""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    total = db.query(Submission).filter(
        Submission.user_id == user_id,
        Submission.status == "confirmed",
    ).count()

    # 查已有未读奖励通知
    existing = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.content.like("%奖励%"),
        Notification.read == False,
    ).first()

    stage = min(20, total)
    progress_pct = min(100, round(stage / REWARD_THRESHOLD * 100))

    # 20阶段命名：种子→发芽→树苗→小树→大树
    if stage == 0:
        phase_name = "种子"; phase_emoji = "🌰"; phase_idx = 0
    elif stage <= 3:
        phase_name = "种子"; phase_emoji = "🌰"; phase_idx = 0
    elif stage <= 7:
        phase_name = "发芽"; phase_emoji = "🌱"; phase_idx = 1
    elif stage <= 12:
        phase_name = "树苗"; phase_emoji = "🌿"; phase_idx = 2
    elif stage <= 17:
        phase_name = "小树"; phase_emoji = "🪴"; phase_idx = 3
    else:
        phase_name = "大树"; phase_emoji = "🌳"; phase_idx = 4

    return {
        "total_submissions": total,
        "current_stage": stage,
        "threshold": REWARD_THRESHOLD,
        "progress_pct": progress_pct,
        "phase_name": phase_name,
        "phase_emoji": phase_emoji,
        "phase_idx": phase_idx,
        "stage_image": f"/checkin/tree_stage_{stage:02d}_" + {
            1: "seed_01", 2: "seed_02", 3: "seed_03",
            4: "sprout_01", 5: "sprout_02", 6: "sprout_03", 7: "sprout_04",
            8: "sapling_01", 9: "sapling_02", 10: "sapling_03", 11: "sapling_04", 12: "sapling_05",
            13: "small_tree_01", 14: "small_tree_02", 15: "small_tree_03", 16: "small_tree_04", 17: "small_tree_05",
            18: "big_tree_01", 19: "big_tree_02", 20: "big_tree_03",
        }.get(stage, "seed_01") + ".png",
        "eligible": total >= REWARD_THRESHOLD,
        "has_notification": bool(existing),
        "message": f"还差 {max(0, REWARD_THRESHOLD - total)} 次投递即可获得实物回收成品奖励！"
        if total < REWARD_THRESHOLD
        else "🎉 恭喜！你已达标，可从成品橱窗中选取一件实物成品作为奖励！",
    }


@router.post("/user/{user_id}/claim-reward")
def claim_reward(user_id: int, db: Session = Depends(get_db)):
    """领取奖励：在成品橱窗选一件成品，发通知"""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    total = db.query(Submission).filter(
        Submission.user_id == user_id,
        Submission.status == "confirmed",
    ).count()

    if total < REWARD_THRESHOLD:
        raise HTTPException(status_code=400, detail=f"还需投递 {REWARD_THRESHOLD - total} 次才能领取")

    # 获取最新完成的成品
    latest = (
        db.query(ReuseItem)
        .join(Batch, ReuseItem.batch_id == Batch.id)
        .filter(Batch.status == "done")
        .order_by(ReuseItem.created_at.desc())
        .first()
    )

    if not latest:
        raise HTTPException(status_code=404, detail="暂无可领取的成品")

    # 发通知
    notif = Notification(
        user_id=user_id,
        batch_id=latest.batch_id,
        content=f"🎁 碳积分奖励！你累计投递 {total} 次，获得实物成品「{latest.product_desc or '环保再生物品'}」一件，请到回收点领取！",
        read=False,
        ts=datetime.utcnow(),
    )
    db.add(notif)
    db.commit()

    return {
        "ok": True,
        "msg": f"奖励已发放！请查收通知，前往领取「{latest.product_desc or '环保再生物品'}」",
        "product_photo": latest.product_photo,
        "product_desc": latest.product_desc,
    }
