"""碳因子计算服务"""
from sqlalchemy.orm import Session

from ..models import CarbonFactor


def calc_co2(db: Session, category: str, recommend: str) -> float:
    """根据品类与处理路径，从因子表查表计算单次减碳量。

    优先按具体处理路径名匹配，找不到则降级匹配 Reuse/Recycle。
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
        # 兜底默认值
        default = {"外卖厨余": 80.0, "快递纸箱": 0.30, "塑料": 0.08, "有害": 0.0}.get(category, 0.15)
        return round(default, 3)
    return round(cf.factor, 3)
