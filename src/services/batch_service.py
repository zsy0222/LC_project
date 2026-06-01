"""批次归集服务

规则：按 (point_id, 日期, category, 推荐路径) 自动归入同一批次；
不同破损等级的同类回收物会进入不同批次，方便去向端按等级分流处理。

批次号格式：BATCH-{qr_code}-{YYYYMMDD}-{category}-{path}
  path: A=共享/再利用(完好), B=手工改造(轻损), C=直接回收(破损/受潮)
"""
from datetime import date

from sqlalchemy.orm import Session

from ..models import Batch, Point
from ..config import PATH_MAP


def get_or_create_batch(db: Session, point: Point, category: str, grade: str = "", destination: str = "C") -> Batch:
    """按点位+日期+品类+路径归入批次"""
    today = date.today()
    path = destination or PATH_MAP.get(grade, "C")
    batch_id = f"BATCH-{point.qr_code}-{today.strftime('%Y%m%d')}-{category}-{path}"
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if batch:
        return batch
    batch = Batch(
        id=batch_id,
        point_id=point.id,
        date=today,
        category=category,
        status="pending",
        destination=path,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch
