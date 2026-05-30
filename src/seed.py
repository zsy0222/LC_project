"""种子数据初始化"""
from .database import SessionLocal
from .models import User, Point, CarbonFactor


SEED_USERS = [
    {"openid": "stu001", "nickname": "小南", "role": "student"},
    {"openid": "stu002", "nickname": "小京", "role": "student"},
    {"openid": "stu003", "nickname": "小苏", "role": "student"},
    {"openid": "reuser01", "nickname": "美术社", "role": "reuser"},
    {"openid": "reuser02", "nickname": "回收站", "role": "reuser"},
    {"openid": "admin01", "nickname": "管理员", "role": "admin"},
]

SEED_POINTS = [
    {"qr_code": "PT-A03", "name": "软件学院",   "location": "南京大学鼓楼校区软件学院",     "gps": "32.058357,118.778438"},
    {"qr_code": "PT-B07", "name": "鼓楼图书馆", "location": "南京大学鼓楼校区图书馆",       "gps": "32.056447,118.775293"},
    {"qr_code": "PT-C01", "name": "南园3舍",    "location": "南京大学鼓楼校区南园3舍回收点", "gps": "32.052431,118.781579"},
]

# 碳因子表（kg CO2e / 件），简化值，可由环保专业成员完善
SEED_FACTORS = [
    {"category": "纸箱", "path": "Reuse",   "factor": 0.35, "source": "中国造纸协会 / IPCC AR6"},
    {"category": "纸箱", "path": "Recycle", "factor": 0.15, "source": "中国造纸协会"},
    {"category": "塑料", "path": "Reuse",   "factor": 0.10, "source": "PAS 2050 简化"},
    {"category": "塑料", "path": "Recycle", "factor": 0.06, "source": "PAS 2050 简化"},
    {"category": "玻璃", "path": "Reuse",   "factor": 0.30, "source": "PAS 2050 简化"},
    {"category": "玻璃", "path": "Recycle", "factor": 0.12, "source": "PAS 2050 简化"},
]


def seed_all():
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add_all([User(**u) for u in SEED_USERS])
        if db.query(Point).count() == 0:
            db.add_all([Point(**p) for p in SEED_POINTS])
        if db.query(CarbonFactor).count() == 0:
            db.add_all([CarbonFactor(**c) for c in SEED_FACTORS])
        db.commit()
    finally:
        db.close()
