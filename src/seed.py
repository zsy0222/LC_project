"""种子数据初始化"""
from .database import SessionLocal
from .models import User, Point, CarbonFactor


SEED_USERS = [
    {"openid": "stu001", "nickname": "小南", "role": "student"},
    {"openid": "stu002", "nickname": "小京", "role": "student"},
    {"openid": "stu003", "nickname": "小苏", "role": "student"},
    {"openid": "reuser01", "nickname": "美术社", "role": "reuser"},
    {"openid": "reuser02", "nickname": "回收站", "role": "reuser"},
    {"openid": "reuser03", "nickname": "园艺社", "role": "reuser"},
    {"openid": "reuser04", "nickname": "创客空间", "role": "reuser"},
    {"openid": "reuser05", "nickname": "生物社", "role": "reuser"},
    {"openid": "reuser06", "nickname": "环保社", "role": "reuser"},
    {"openid": "reuser07", "nickname": "化学社", "role": "reuser"},
    {"openid": "reuser08", "nickname": "宠保社", "role": "reuser"},
    {"openid": "reuser09", "nickname": "手工社", "role": "reuser"},
    {"openid": "reuser10", "nickname": "食监委", "role": "reuser"},
    {"openid": "admin01", "nickname": "管理员", "role": "admin"},
]

SEED_POINTS = [
    {"qr_code": "PT-A03", "name": "软件学院",   "location": "南京大学鼓楼校区软件学院",           "gps": "32.058357,118.778438"},
    {"qr_code": "PT-B07", "name": "鼓楼图书馆", "location": "南京大学鼓楼校区图书馆",             "gps": "32.056447,118.775293"},
    {"qr_code": "PT-C01", "name": "南园3舍",    "location": "南京大学鼓楼校区南园3舍分类回收点",   "gps": "32.053925,118.777592"},
]

# 碳因子表（kg CO2e / 件 或 /kg），简化值
SEED_FACTORS = [
    # 外卖厨余（按每吨处理减排量，kg CO₂e/吨）
    {"category": "外卖厨余", "path": "厌氧消化工艺",     "factor": 90.82, "source": "避免填埋甲烷+沼气发电+有机肥替代化肥，净减排-90.82kg/吨"},
    {"category": "外卖厨余", "path": "发酵产酸工艺",     "factor": 81.04, "source": "发酵产酸替代传统碳源生产，净减排-81.04kg/吨"},
    {"category": "外卖厨余", "path": "三相分离协同焚烧",  "factor": 80.96, "source": "油脂制生物柴油+固渣焚烧发电，净减排-80.96kg/吨"},
    {"category": "外卖厨余", "path": "好氧堆肥工艺",     "factor": 35.0,  "source": "中科院生态中心(2021)——好氧堆肥替代化肥"},
    {"category": "外卖厨余", "path": "直接混合焚烧",     "factor": 3.01,  "source": "焚烧发电替代化石能源(热值低)，净减排-3.01kg/吨"},
    {"category": "外卖厨余", "path": "黑水虻厌氧集成",   "factor": 135.0, "source": "清华(2025)——黑水虻+厌氧集成，碳足迹降低34%"},
    {"category": "外卖厨余", "path": "蚯蚓堆肥工艺",     "factor": 40.0,  "source": "《现代农业科技》2023/21期——蚯蚓粪+虫体蛋白"},
    # 快递纸箱（废纸）处理工艺
    {"category": "快递纸箱", "path": "回收制浆再生",   "factor": 1580.0, "source": "中国造纸协会《造纸工业碳排放核算指南》(2022)——再生瓦楞纸"},
    {"category": "快递纸箱", "path": "热解制生物炭",   "factor": 427.0,  "source": "《环境工程技术学报》废纸热解碳封存(2024)"},
    {"category": "快递纸箱", "path": "蛋托/育苗钵模塑工艺",  "factor": 800.0,  "source": "大连工大《包装学报》(2021)——纸浆模塑LCA"},
    {"category": "快递纸箱", "path": "蘑菇培养料制备工艺",  "factor": 600.0,  "source": "烟台大学《环境与发展》2024/1期——废纸栽培多脂鳞伞"},
    {"category": "快递纸箱", "path": "废纸纤维素隔热材工艺","factor": 1400.0, "source": "WANG & WANG, Sustainability 2023——纤维素隔热材LCA"},
    {"category": "快递纸箱", "path": "Reuse",           "factor": 1580.0, "source": "降级兼容"},
    {"category": "快递纸箱", "path": "Recycle",         "factor": 427.0,  "source": "降级兼容"},
    # 塑料处理工艺
    {"category": "塑料", "path": "物理回收造粒",   "factor": 2100.0, "source": "中国循环经济协会(2024)——再生PE替代原生塑料"},
    {"category": "塑料", "path": "化学回收热解",   "factor": 2500.0, "source": "中国循环经济协会(2025)——热解制油全循环"},
    {"category": "塑料", "path": "3D打印线材再生工艺", "factor": 1800.0, "source": "Al Rashid & Koç 2024——PET瓶→打印线材"},
    {"category": "塑料", "path": "生态砖工艺",     "factor": 1400.0, "source": "GEA ecobricks.org——物理碳封存"},
    {"category": "塑料", "path": "塑木复合材料工艺", "factor": 1800.0, "source": "Brunnhuber et al. 2023——WPC全生命周期"},
    {"category": "塑料", "path": "Reuse",           "factor": 2100.0, "source": "降级兼容"},
    {"category": "塑料", "path": "Recycle",         "factor": 2100.0, "source": "降级兼容"},
    # 有害垃圾处理工艺
    {"category": "有害", "path": "资源化金属回收", "factor": 2000.0, "source": "中国信通院(2026)——金属回收替代原生冶炼"},
    {"category": "有害", "path": "水泥窑协同处置", "factor": 750.0,  "source": "生态环境部环境发展中心(2026)"},
    {"category": "有害", "path": "电池分类拆解回收工艺", "factor": 2800.0, "source": "西交大/山科大——锂电池拆解回收"},
    {"category": "有害", "path": "荧光灯管汞回收蒸馏工艺","factor": 750.0,  "source": "LI Tong et al. Energy Reports 2023——真空蒸馏汞回收"},
    {"category": "有害", "path": "Recycle",         "factor": 750.0,  "source": "降级兼容"},
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
