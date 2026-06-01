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
    {"qr_code": "PT-A03", "name": "软件学院",   "location": "南京大学鼓楼校区软件学院",           "gps": "32.058357,118.778438"},
    {"qr_code": "PT-B07", "name": "鼓楼图书馆", "location": "南京大学鼓楼校区图书馆",             "gps": "32.056447,118.775293"},
    {"qr_code": "PT-C01", "name": "南园3舍",    "location": "南京大学鼓楼校区南园3舍分类回收点",   "gps": "32.0571,118.7758"},
]

# 碳因子表（kg CO2e / 件 或 /kg），简化值
SEED_FACTORS = [
    # 外卖厨余（按每吨处理减排量，kg CO₂e/吨）
    {"category": "外卖厨余", "path": "厌氧消化工艺",     "factor": 90.82, "source": "避免填埋甲烷+沼气发电+有机肥替代化肥，净减排-90.82kg/吨"},
    {"category": "外卖厨余", "path": "发酵产酸工艺",     "factor": 81.04, "source": "发酵产酸替代传统碳源生产，净减排-81.04kg/吨"},
    {"category": "外卖厨余", "path": "三相分离协同焚烧",  "factor": 80.96, "source": "油脂制生物柴油+固渣焚烧发电，净减排-80.96kg/吨"},
    {"category": "外卖厨余", "path": "黑水虻生物转化",   "factor": 41.78, "source": "虫体蛋白+虫粪有机肥替代，净减排-41.78kg/吨"},
    {"category": "外卖厨余", "path": "直接混合焚烧",     "factor": 3.01,  "source": "焚烧发电替代化石能源(热值低)，净减排-3.01kg/吨"},
    # 快递纸箱（沿用）
    {"category": "快递纸箱", "path": "Reuse",   "factor": 0.35, "source": "中国造纸协会 / IPCC AR6"},
    {"category": "快递纸箱", "path": "Recycle", "factor": 0.15, "source": "中国造纸协会"},
    # 塑料
    {"category": "塑料", "path": "Reuse",   "factor": 0.10, "source": "PAS 2050 简化"},
    {"category": "塑料", "path": "Recycle", "factor": 0.06, "source": "PAS 2050 简化"},
    # 有害（暂不计减碳）
    {"category": "有害", "path": "Recycle", "factor": 0.0, "source": "仅记录分类行为"},
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
