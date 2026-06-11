"""成果展示 + 回收物追踪 + 碳积分奖励"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import User, Submission, Batch, ReuseItem, Notification, Point, ShopOrder
from ..schemas import ShopBuyRequest

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
    """成品橱窗——仅精选成品（featured=True）"""
    done_batches = db.query(Batch).filter(Batch.status == "done").order_by(Batch.created_at.desc()).limit(30).all()
    if not done_batches:
        return {"items": []}

    batch_ids = [b.id for b in done_batches]
    batch_map = {b.id: b for b in done_batches}
    all_reuse = db.query(ReuseItem).filter(
        ReuseItem.batch_id.in_(batch_ids),
        ReuseItem.featured == True,
    ).order_by(ReuseItem.created_at.desc()).all()

    my_batch_ids = set()
    if user_id:
        my_subs = db.query(Submission).filter(
            Submission.user_id == user_id,
            Submission.status == "confirmed",
            Submission.batch_id.in_(batch_ids),
        ).all()
        my_batch_ids = set(s.batch_id for s in my_subs)

    items = []
    for r in all_reuse:
        b = batch_map.get(r.batch_id)
        if not b:
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


@router.get("/unlock-status")
def unlock_status(user_id: int, db: Session = Depends(get_db)):
    """成果页解锁 — 有自己上传的作品即解锁"""
    count = db.query(ReuseItem).filter(ReuseItem.reuser_id == user_id).count()
    return {"unlocked": count > 0, "product_count": count}


@router.get("/gallery/mine")
def my_product_gallery(user_id: int, db: Session = Depends(get_db)):
    """我的作品 — 学生查自己批次成品 / 去向端查自己上传成品"""
    user = db.query(User).get(user_id)
    if not user:
        return {"items": []}

    if user.role in ("student",):
        # 学生: 只查自己上传的活动作品
        my_items = db.query(ReuseItem).filter(
            ReuseItem.reuser_id == user_id
        ).order_by(ReuseItem.created_at.desc()).all()
    else:
        # 去向端/管理员: 自己上传的所有成品
        my_items = db.query(ReuseItem).filter(
            ReuseItem.reuser_id == user_id
        ).order_by(ReuseItem.created_at.desc()).all()

    if not my_items:
        return {"items": []}

    batch_ids = list(set(r.batch_id for r in my_items))
    batches = {b.id: b for b in db.query(Batch).filter(Batch.id.in_(batch_ids)).all()}
    reuser_cache = {}

    items = []
    for r in my_items:
        b = batches.get(r.batch_id)
        if r.reuser_id not in reuser_cache:
            reuser_cache[r.reuser_id] = db.query(User).get(r.reuser_id)
        reuser = reuser_cache.get(r.reuser_id)
        items.append({
            "reuse_id": r.id,
            "batch_id": r.batch_id,
            "category": b.category if b else "活动作品",
            "destination": b.destination if b else "",
            "product_photo": r.product_photo,
            "product_desc": r.product_desc,
            "featured": r.featured,
            "reuser_name": reuser.nickname if reuser else "去向端",
            "date": datetime.strftime(r.created_at, "%Y-%m-%d") if r.created_at else "",
            "is_mine": True,
        })
    return {"items": items}


@router.post("/gallery/feature")
def feature_product(user_id: int, reuse_id: int, db: Session = Depends(get_db)):
    """切换成品精选状态"""
    item = db.query(ReuseItem).filter(
        ReuseItem.id == reuse_id,
        ReuseItem.reuser_id == user_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="作品不存在")
    item.featured = not item.featured
    db.commit()
    return {"ok": True, "featured": item.featured, "msg": "已精选到橱窗" if item.featured else "已取消精选"}


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

    # 查是否已领取
    already_claimed = db.query(ShopOrder).filter(
        ShopOrder.user_id == user_id,
        ShopOrder.item_id.like("reward_%"),
    ).first()

    stage = min(20, total)
    progress_pct = min(100, round(stage / REWARD_THRESHOLD * 100))

    if stage == 0: phase_name = "空地"; phase_emoji = ""; phase_idx = 0
    elif stage <= 3: phase_name = "种子"; phase_emoji = "🌰"; phase_idx = 0
    elif stage <= 7: phase_name = "发芽"; phase_emoji = "🌱"; phase_idx = 1
    elif stage <= 12: phase_name = "树苗"; phase_emoji = "🌿"; phase_idx = 2
    elif stage <= 17: phase_name = "小树"; phase_emoji = "🪴"; phase_idx = 3
    else: phase_name = "大树"; phase_emoji = "🌳"; phase_idx = 4

    stage_map = {1:"acorn_sprout",2:"acorn_crack",3:"acorn_root",4:"seedling_emerge",5:"seedling_leaf",6:"seedling_grow",7:"seedling_strong",8:"sapling_young",9:"sapling_branch",10:"sapling_tall",11:"sapling_crown",12:"sapling_vigorous",13:"tree_small",14:"tree_growing",15:"tree_bloom",16:"tree_shade",17:"tree_majestic",18:"giant_mature",19:"giant_grand",20:"giant_ancient"}
    stage_image = "/image/tree/tree_stage_00_empty.png" if stage == 0 else f"/image/tree/tree_stage_{stage:02d}_{stage_map.get(stage,'acorn_sprout')}.png"

    return {
        "total_submissions": total,
        "current_stage": stage,
        "threshold": REWARD_THRESHOLD,
        "progress_pct": progress_pct,
        "phase_name": phase_name,
        "phase_emoji": phase_emoji,
        "phase_idx": phase_idx,
        "stage_image": stage_image,
        "eligible": total >= REWARD_THRESHOLD,
        "already_claimed": bool(already_claimed),
        "claimed_item": already_claimed.item_name if already_claimed else None,
        "message": f"还差 {max(0, REWARD_THRESHOLD - total)} 次投递即可获得奖励！"
        if total < REWARD_THRESHOLD
        else ("🎁 已领取奖励，新一轮回收开始！" if already_claimed else "🎉 恭喜！你已达标，可从成品橱窗中选取一件实物成品作为奖励！"),
    }


@router.post("/user/{user_id}/claim-reward")
def claim_reward(user_id: int, address: str = "", db: Session = Depends(get_db)):
    """盲盒抽奖：随机选取一件精选成品作为奖励"""
    import random as _random

    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    total = db.query(Submission).filter(
        Submission.user_id == user_id,
        Submission.status == "confirmed",
    ).count()

    if total < REWARD_THRESHOLD:
        raise HTTPException(status_code=400, detail=f"还差 {REWARD_THRESHOLD - total} 次投递，加油！")

    # 已经领过的检查
    already = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.content.like("%碳积分奖励%"),
    ).first()
    if already:
        raise HTTPException(status_code=400, detail="你已经领取过奖励了，每期只能领取一次")

    # 随机抽取一件精选成品
    pool = (
        db.query(ReuseItem)
        .join(Batch, ReuseItem.batch_id == Batch.id)
        .filter(Batch.status == "done", ReuseItem.featured == True)
        .all()
    )
    if not pool:
        raise HTTPException(status_code=404, detail="暂无可领取的成品")

    picked = _random.choice(pool)
    batch = db.query(Batch).get(picked.batch_id)
    reuser = db.query(User).get(picked.reuser_id)

    # 创建物流订单（兑换记录）
    order = ShopOrder(
        user_id=user_id,
        item_id=f"reward_{picked.id}",
        item_name=picked.product_desc or "盲盒奖励",
        price=0,  # 免费领取
        address=address or "回收点领取",
        status="pending",
    )
    db.add(order)

    notif = Notification(
        user_id=user_id,
        batch_id=picked.batch_id,
        content=f"🎁 碳积分奖励！你累计投递 {total} 次，抽中「{picked.product_desc or '环保再生物品'}」（{reuser.nickname if reuser else '去向端'}出品），请到{address or '回收点'}领取！",
        read=False,
        ts=datetime.utcnow(),
    )
    db.add(notif)

    # 重置投递计数：将所有已确认投递标记为 expired
    db.query(Submission).filter(
        Submission.user_id == user_id,
        Submission.status == "confirmed",
    ).update({Submission.status: "expired"}, synchronize_session=False)

    db.commit()

    return {
        "ok": True,
        "msg": f"🎉 恭喜抽中「{picked.product_desc or '环保再生物品'}」！",
        "product_photo": picked.product_photo,
        "product_desc": picked.product_desc,
        "reuser_name": reuser.nickname if reuser else "去向端",
        "category": batch.category if batch else "未知",
        "pool_size": len(pool),
    }


# ==================== 碳积分商城 ====================

SHOP_ITEMS = [
    {"id": "s01", "name": "再生纸书签", "icon": "🔖", "price": 0.3, "desc": "回收纸浆手工压制，每张独一无二",
     "club": "手工社", "category": "快递纸箱", "image": "/image/shop/s01_bookmark.png"},
    {"id": "s02", "name": "蚯蚓粪盆栽", "icon": "🪴", "price": 0.6, "desc": "蚯蚓粪培育的多肉植物，自带肥料",
     "club": "生物社", "category": "外卖厨余", "image": "/image/shop/s02_plant.png"},
    {"id": "s03", "name": "3D打印小挂件", "icon": "🧩", "price": 1.0, "desc": "PET瓶回收线材打印，校园LOGO定制",
     "club": "创客空间", "category": "塑料", "image": "/image/shop/s03_keychain.png"},
    {"id": "s04", "name": "手工再生纸本", "icon": "📒", "price": 1.5, "desc": "废纸重制手工纸装订，A6口袋大小",
     "club": "手工社", "category": "快递纸箱", "image": "/image/shop/s04_notebook.png"},
    {"id": "s05", "name": "蘑菇菌包DIY", "icon": "🍄", "price": 2.0, "desc": "废纸基料平菇菌包，7天出菇可食用",
     "club": "生物社", "category": "快递纸箱", "image": "/image/shop/s05_mushroom.png"},
    {"id": "s06", "name": "生态砖花盆", "icon": "🏺", "price": 2.5, "desc": "废塑封存瓶中制成花盆，碳锁定百年",
     "club": "环保社", "category": "塑料", "image": "/image/shop/s06_ecobrick.png"},
    {"id": "s07", "name": "蛋托育苗套装", "icon": "🌱", "price": 3.0, "desc": "废纸模塑蛋托+种子包，阳台种菜入门",
     "club": "园艺社", "category": "快递纸箱", "image": "/image/shop/s07_seedling.png"},
    {"id": "s08", "name": "纤维素隔热杯垫", "icon": "☕", "price": 3.5, "desc": "废纸纤维压制，隔热防烫可降解",
     "club": "手工社", "category": "快递纸箱", "image": "/image/shop/s08_coaster.png"},
    {"id": "s09", "name": "回收金属徽章", "icon": "🏅", "price": 4.0, "desc": "旧电池金属熔铸，校园环保达人限定",
     "club": "化学社", "category": "有害", "image": "/image/shop/s09_badge.png"},
    {"id": "s10", "name": "再生塑料笔筒", "icon": "✏️", "price": 4.5, "desc": "HDPE瓶盖热压成型，莫兰迪色系",
     "club": "创客空间", "category": "塑料", "image": "/image/shop/s10_penholder.png"},
    {"id": "s11", "name": "WPC手机支架", "icon": "📱", "price": 5.0, "desc": "塑木复合材料CNC雕刻，比原木更耐用",
     "club": "创客空间", "category": "塑料", "image": "/image/shop/s11_phonestand.png"},
    {"id": "s12", "name": "碳积分荣誉证书+礼盒", "icon": "📜", "price": 8.0, "desc": "年度减碳证书+随机回收物礼盒，仪式感拉满",
     "club": "环保社", "category": "混合", "image": "/image/shop/s12_certificate.png"},
]


BASE_STOCK = 3                    # 初始库存
STOCK_PER_SUBMISSION = 5           # 每投递N次，对应品类库存+1


def _get_shop_with_stock(db: Session) -> list[dict]:
    """商品列表 + 动态库存"""
    # 统计各品类 confirmed 投递总量
    cat_counts = {}
    for cat in ["外卖厨余", "快递纸箱", "塑料", "有害"]:
        cnt = db.query(Submission).filter(
            Submission.waste_type == cat,
            Submission.status == "confirmed",
        ).count()
        cat_counts[cat] = cnt
    # 混合品类取均值
    cat_counts["混合"] = sum(cat_counts.values()) // 4

    items = []
    for i in SHOP_ITEMS:
        cat = i["category"]
        bonus = cat_counts.get(cat, 0) // STOCK_PER_SUBMISSION
        stock = BASE_STOCK + bonus
        items.append({**i, "stock": stock, "bonus_stock": bonus})
    return items


@router.get("/shop")
def list_shop_items(db: Session = Depends(get_db)):
    """碳积分商城商品列表（含动态库存）"""
    return {"items": _get_shop_with_stock(db)}


def _purchased_count(db: Session, item_id: str) -> int:
    """某商品已被兑换次数"""
    return db.query(ShopOrder).filter(ShopOrder.item_id == item_id).count()


@router.post("/shop/buy")
def buy_shop_item(data: ShopBuyRequest, db: Session = Depends(get_db)):
    """碳积分兑换商品（含库存校验 + 收货地址）"""
    if not data.address.strip():
        raise HTTPException(status_code=400, detail="请填写收货地址（如：南园3舍）")

    user = db.query(User).get(data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    item = next((i for i in SHOP_ITEMS if i["id"] == data.item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 库存 = 基础 + 投递加成 - 已购买
    items_with_stock = _get_shop_with_stock(db)
    stock_item = next((i for i in items_with_stock if i["id"] == data.item_id), None)
    if stock_item:
        real_stock = stock_item["stock"] - _purchased_count(db, data.item_id)
        if real_stock <= 0:
            raise HTTPException(status_code=400, detail=f"「{item['name']}」已售罄，等社团补货吧～")

    if (user.carbon_score or 0) < item["price"]:
        raise HTTPException(
            status_code=400,
            detail=f"碳积分不足！需要 {item['price']} kg，当前 {user.carbon_score:.3f} kg",
        )

    user.carbon_score = float(user.carbon_score or 0) - item["price"]

    # 创建兑换记录
    order = ShopOrder(
        user_id=data.user_id,
        item_id=data.item_id,
        item_name=item["name"],
        price=item["price"],
        address=data.address.strip(),
        status="pending",
    )
    db.add(order)

    notif = Notification(
        user_id=data.user_id,
        batch_id="SHOP",
        content=f"🛒 你兑换了「{item['name']}」(-{item['price']} kg)，配送到 {data.address.strip()}",
        read=False,
        ts=datetime.utcnow(),
    )
    db.add(notif)
    db.commit()

    new_stock = _get_shop_with_stock(db)
    new_s = next((i for i in new_stock if i["id"] == data.item_id), None)

    return {
        "ok": True,
        "msg": f"兑换成功！{item['name']} (-{item['price']} kg)，将配送到 {data.address.strip()}",
        "remaining_score": round(user.carbon_score, 3),
        "new_stock": (new_s["stock"] if new_s else 0) - _purchased_count(db, data.item_id),
        "order_id": order.id,
    }


@router.get("/shop/orders")
def list_orders(user_id: int, db: Session = Depends(get_db)):
    """用户兑换记录"""
    orders = (
        db.query(ShopOrder)
        .filter(ShopOrder.user_id == user_id)
        .order_by(ShopOrder.created_at.desc())
        .all()
    )
    return {
        "orders": [
            {
                "id": o.id,
                "item_name": o.item_name,
                "price": o.price,
                "address": o.address,
                "status": o.status,
                "status_text": "已收货" if o.status == "received" else "配送中",
                "created_at": o.created_at.isoformat() if o.created_at else "",
            }
            for o in orders
        ]
    }


@router.post("/shop/orders/{order_id}/receive")
def mark_received(order_id: int, user_id: int, db: Session = Depends(get_db)):
    """确认收货"""
    order = db.query(ShopOrder).filter(ShopOrder.id == order_id, ShopOrder.user_id == user_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status == "received":
        raise HTTPException(status_code=400, detail="已确认过收货")
    order.status = "received"
    db.commit()
    return {"ok": True, "msg": f"已确认收货「{order.item_name}」"}
