"""碳因子计算服务"""
from sqlalchemy.orm import Session

from ..models import CarbonFactor
from ..config import WEIGHT_ESTIMATE


def calc_co2(db: Session, category: str, recommend: str) -> float:
    """计算单次投递减碳量。

    seed.py 碳因子为每吨减排量 (kg CO₂e/吨)，
    本函数按品类单次投递重量折算为单次减碳量 (kg CO₂e/次)。

    公式: co2 = factor_per_ton × weight_kg / 1000
    """
    # 先尝试直接匹配路径名
    cf = (
        db.query(CarbonFactor)
        .filter(CarbonFactor.category == category, CarbonFactor.path == recommend)
        .first()
    )
    # 找不到则降级匹配 Reuse/Recycle
    if cf is None:
        path = "Recycle" if recommend in ("C", "直接回收") else "Reuse"
        cf = (
            db.query(CarbonFactor)
            .filter(CarbonFactor.category == category, CarbonFactor.path == path)
            .first()
        )
    if cf is None:
        # 兜底默认值（每吨）
        default_per_ton = {"外卖厨余": 80.0, "快递纸箱": 1200.0, "塑料": 2000.0, "有害": 700.0}.get(category, 100.0)
        weight = WEIGHT_ESTIMATE.get(category, 0.2)
        return round(default_per_ton * weight / 1000, 4)

    weight = WEIGHT_ESTIMATE.get(category, 0.2)
    return round(cf.factor * weight / 1000, 4)
