"""碳因子计算服务"""
from sqlalchemy.orm import Session

from ..models import CarbonFactor


def calc_co2(db: Session, category: str, recommend: str) -> float:
    """根据品类与推荐路径，从因子表查表计算单次减碳量

    推荐路径 → 碳因子表 path:
        A 共享/再利用  → Reuse
        B 手工改造     → Reuse
        C 直接回收     → Recycle
    """
    path = "Recycle" if recommend == "C" else "Reuse"
    cf = (
        db.query(CarbonFactor)
        .filter(CarbonFactor.category == category, CarbonFactor.path == path)
        .first()
    )
    if cf is None:
        # 兜底默认值
        default = {"纸箱": 0.30, "塑料": 0.08, "玻璃": 0.25}.get(category, 0.15)
        return round(default, 3)
    return round(cf.factor, 3)
