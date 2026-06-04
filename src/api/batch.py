"""批次接口：列表 / 认领 / 上传成品 / 故事页"""
import random
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


def _generate_product_desc(category: str, destination: str, reuser_name: str) -> str:
    """AI 自主生成幽默成品描述（无评论时自动补全）"""
    templates = {
        "外卖厨余": {
            "厌氧消化工艺": [
                "一罐沼气正在食堂后厨燃烧，这顿饭的热量又回来了（虽然换了个形式）🔥",
                "厨余变沼气，下一秒就帮你煮下一碗面，完美循环 🍜",
            ],
            "发酵产酸工艺": [
                "你的剩饭被微生物啃成了工业级碳源，身价暴涨 💎",
            ],
            "三相分离协同焚烧": [
                "油脂炼成生物柴油，固体烧成电——连渣都没浪费 ⚡",
            ],
            "好氧堆肥工艺": [
                "剩饭变成黑金土，正在花圃里养花，比在垃圾桶里体面多了 🌸",
                "从餐桌到花坛，历经微生物的996，终成有机肥 💪",
            ],
            "直接混合焚烧": [
                "虽然烧了有点可惜，但至少发了点电，比填埋强 ⚡",
            ],
            "黑水虻厌氧集成": [
                "虫子先吃，细菌再吃，最后你吃的菜可能也靠它们——这就是生态 😋",
                "黑水虻饱餐一顿后变成了高蛋白，水产养殖业的福音 🐛",
            ],
            "蚯蚓堆肥工艺": [
                "蚯蚓们开了一场自助餐派对，产出顶级有机肥 🪱",
                "你的厨余让蚯蚓们胖了三圈，粪便是最好的花肥 🌻",
            ],
        },
        "快递纸箱": {
            "回收制浆再生": [
                "旧纸箱已投胎转世，这次可能是你的新快递盒 📦",
                "纸箱轮回：快递→回收→纸浆→新生纸箱，永动机（伪）♻️",
            ],
            "热解制生物炭": [
                "纸箱被烤成了生物炭，未来百年都在土壤里固碳，长寿冠军 🏆",
            ],
            "蛋托/育苗钵模塑工艺": [
                "纸箱变成育苗杯，正在培养下一代西红柿 🍅",
                "曾经的快递包装，现在是种子的小摇篮 🌱",
            ],
            "蘑菇培养料制备工艺": [
                "纸箱变身菌包，过两天就能收平菇了，火锅必备 🍄",
                "你的纸箱正在长蘑菇，菌丝比5G还快蔓延中 📡",
            ],
            "废纸纤维素隔热材工艺": [
                "纸箱成了墙体保温层，冬天帮你省暖气费 🔥",
            ],
        },
        "塑料": {
            "物理回收造粒": [
                "旧瓶变新瓶，塑料的轮回之路，这次少用了两吨石油 🛢️",
            ],
            "化学回收热解": [
                "塑料被高温炼成了油，穿越回成为塑料之前的样子 🔥",
            ],
            "3D打印线材再生工艺": [
                "塑料瓶变身3D打印线材，正在创客空间打印一副象棋的马 ♟️",
            ],
            "生态砖工艺": [
                "废塑料被封印在瓶中砖，碳被锁死几百年，环保界的封印术 🔒",
            ],
            "塑木复合材料工艺": [
                "塑料和木屑合体成WPC板材，比原木还耐用，变废为宝的典范 🪵",
            ],
        },
        "有害": {
            "资源化金属回收": [
                "旧电池里的金属被提炼，可能正在成为下一块手机电池 📱",
            ],
            "水泥窑协同处置": [
                "1400°C高温下有害物灰飞烟灭，剩下的帮水泥厂省了煤 🔥",
            ],
            "电池分类拆解回收工艺": [
                "锂电池拆解得明明白白，锂钴镍各回各家，一个都不浪费 🔋",
            ],
            "荧光灯管汞回收蒸馏工艺": [
                "灯管里的汞被蒸馏回收，水银遁入真空，安全归来 💡",
            ],
        },
    }
    # 通用兜底
    generic = [
        f"经过{reuser_name}的巧手，这批回收物焕发了第二春 🌟",
        f"{reuser_name}施展了化废为宝的魔法，成品即将亮相 ✨",
        f"旧物新生，{reuser_name}出品，减碳又增值 🎨",
    ]
    cat_tpl = templates.get(category, {})
    dest_tpl = cat_tpl.get(
        destination,
        cat_tpl.get(list(cat_tpl.keys())[0] if cat_tpl else "", []) or generic,
    )
    if not dest_tpl:
        dest_tpl = generic
    return random.choice(dest_tpl)


def _is_admin(user_id: int, db: Session) -> bool:
    """管理员跳过限制"""
    user = db.query(User).get(user_id)
    return user is not None and user.role == "admin"


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
    batch.claimed_by = data.reuser_id
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

    # 已认领的批次只有认领人或管理员才能上传成品
    if batch.status == "claimed" and batch.claimed_by and not _is_admin(data.reuser_id, db):
        if batch.claimed_by != data.reuser_id:
            claimer = db.query(User).get(batch.claimed_by)
            raise HTTPException(status_code=403, detail=f"该批次已被「{claimer.nickname if claimer else '其他去向端'}」认领，不可由其他去向端上传成品")

    item = ReuseItem(
        batch_id=batch.id,
        reuser_id=reuser.id,
        product_photo=data.product_photo,
        product_desc=data.product_desc or _generate_product_desc(batch.category, batch.destination or "", reuser.nickname),
    )
    db.add(item)
    batch.status = "done"
    db.commit()

    # 广播给该批次全部投递用户
    cnt = broadcast_reuse(
        db,
        batch.id,
        f"你参与的批次「{batch.id}」已完成再生：{item.product_desc}",
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
