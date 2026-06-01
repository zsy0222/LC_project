"""扫码登记接口"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Point
from ..schemas import ScanResp, PointOut

from ..config import DEMO_MODE, LOCATION_MAX_DISTANCE_M, TREATMENT_KNOWLEDGE

router = APIRouter(tags=["scan"])


@router.get("/config/demo")
def demo_config():
    """返回 Demo 模式状态，前端据此决定是否跳过定位"""
    return {"demo_mode": DEMO_MODE, "location_max_distance_m": LOCATION_MAX_DISTANCE_M}


@router.get("/knowledge/treatment/{key}")
def treatment_knowledge(key: str):
    """返回指定处理工艺的详细知识"""
    info = TREATMENT_KNOWLEDGE.get(key)
    if not info:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"未找到工艺: {key}")
    return info


@router.get("/knowledge/treatments")
def list_treatments():
    """列出所有处理工艺"""
    return {k: {"title": v["title"], "co2_per_ton": v["co2_per_ton"], "unit": v["unit"]} for k, v in TREATMENT_KNOWLEDGE.items()}


@router.post("/scan", response_model=ScanResp)
def scan(qr_code: str, db: Session = Depends(get_db)):
    """扫描回收点二维码，返回点位与服务器时间"""
    point = db.query(Point).filter(Point.qr_code == qr_code).first()
    if not point:
        raise HTTPException(status_code=404, detail=f"点位不存在: {qr_code}")
    return ScanResp(
        point=PointOut.model_validate(point),
        server_time=datetime.utcnow(),
    )


@router.get("/points")
def list_points(db: Session = Depends(get_db)):
    """列出所有回收点（演示用，省去真实扫码硬件）"""
    return [
        {"id": p.id, "qr_code": p.qr_code, "name": p.name, "location": p.location, "gps": p.gps}
        for p in db.query(Point).all()
    ]
