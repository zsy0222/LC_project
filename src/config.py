"""全局配置"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
WEB_DIR = SRC_DIR / "web"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

DB_PATH = BASE_DIR / "lc_project.db"
DB_URL = f"sqlite:///{DB_PATH}"

# AI 配置
AI_MOCK_MODE = False           # True: 强制使用 mock；False: 优先用 torch，失败再降级
AI_CONFIDENCE_THRESHOLD = 0.6  # 低于该置信度提示重拍

# 品类列表
WASTE_TYPES = ["外卖厨余", "快递纸箱", "塑料", "有害"]  # 四大回收品类

# 旧版兼容（纸箱系统）
CATEGORIES = WASTE_TYPES
GRADES = ["完好", "轻损", "破损", "受潮"]  # 仅纸箱品类使用
PATH_MAP = {
    "完好": "A",
    "轻损": "B",
    "破损": "C",
    "受潮": "C",
}
PATH_DESC = {
    # 旧版兼容
    "A": "共享/再利用",
    "B": "手工改造",
    "C": "直接回收",
    # 新品类去向
    "厌氧消化": "厌氧消化（产沼气）",
    "好氧堆肥": "好氧堆肥（产有机肥）",
    "饲料化": "饲料化（黑水虻/蚯蚓）",
    "共享再利用": "共享/再利用",
    "直接回收": "直接回收",
    "塑料再生": "塑料再生",
    "无害化处理": "无害化处理",
    # 厨余垃圾五种处理工艺
    "厌氧消化工艺": "厌氧消化工艺",
    "发酵产酸工艺": "发酵产酸工艺",
    "三相分离协同焚烧": "三相分离协同焚烧工艺",
    "黑水虻生物转化": "黑水虻生物转化工艺",
    "直接混合焚烧": "直接混合焚烧工艺",
}
# 厨余处理工艺知识库（用于前端弹窗展示）
TREATMENT_KNOWLEDGE = {
    "厌氧消化工艺": {
        "title": "厌氧消化工艺",
        "co2_per_ton": -90.82,
        "unit": "kg CO₂e / 吨",
        "principle": "避免填埋产生的甲烷排放（甲烷温室效应是CO₂的28倍），同时沼气发电替代化石能源，有机肥替代化肥。",
        "process": "厨余垃圾 → 预处理（破碎/除杂） → 厌氧发酵罐（产沼气） → 沼气发电/提纯 → 沼渣制成有机肥",
        "output": "沼气（可发电/提纯天然气）、有机肥",
    },
    "发酵产酸工艺": {
        "title": "发酵产酸工艺",
        "co2_per_ton": -81.04,
        "unit": "kg CO₂e / 吨",
        "principle": "通过发酵将有机质转化为生物碳源，替代传统碳源生产，减少碳排放。",
        "process": "厨余垃圾 → 水解酸化 → 产酸发酵 → 分离提纯 → 生物碳源产品",
        "output": "生物碳源（替代工业碳源用于污水处理等）",
    },
    "三相分离协同焚烧": {
        "title": "三相分离协同焚烧工艺",
        "co2_per_ton": -80.96,
        "unit": "kg CO₂e / 吨",
        "principle": "分离油脂制生物柴油，固渣焚烧发电，减少填埋和化石能源使用。",
        "process": "厨余垃圾 → 三相分离（油/水/固） → 油脂→生物柴油 | 固渣→焚烧发电 | 废水→厌氧处理",
        "output": "生物柴油、电力、再生水",
    },
    "黑水虻生物转化": {
        "title": "黑水虻生物转化工艺",
        "co2_per_ton": -41.78,
        "unit": "kg CO₂e / 吨",
        "principle": "黑水虻幼虫取食厨余垃圾，转化为高蛋白虫体和虫粪有机肥，减少废弃物处理碳排放。",
        "process": "厨余垃圾 → 粉碎预处理 → 黑水虻幼虫养殖（7-10天） → 分离 → 虫体蛋白饲料 + 虫粪有机肥",
        "output": "昆虫蛋白饲料、有机肥",
    },
    "直接混合焚烧": {
        "title": "直接混合焚烧工艺",
        "co2_per_ton": -3.01,
        "unit": "kg CO₂e / 吨",
        "principle": "焚烧发电替代部分化石能源，但厨余含水率高导致热值低，减排效果较弱，未充分利用资源化潜力。",
        "process": "厨余垃圾 → 混合其他垃圾 → 焚烧炉 → 余热发电 → 炉渣填埋",
        "output": "电力（热值较低）",
    },
}
# 外卖厨余处理路径
FOOD_TREATMENT = {
    "A": "厌氧消化（产沼气）",
    "B": "好氧堆肥（产有机肥）",
    "C": "饲料化（黑水虻/蚯蚓）",
}

# 服务地址
HOST = "127.0.0.1"
PORT = 8000

# 反作弊参数
LOCATION_MAX_DISTANCE_M = 100     # GPS 定位最大允许距离（米）
COOLDOWN_SECONDS = 30            # 同点位提交冷却时间（秒）
PHOTO_SIMILARITY_THRESHOLD = 0.15  # 图片相似度阈值（≤15% 差异视为同一物品）
PHOTO_SIMILARITY_RECENT_HOURS = 24  # 图片相似度比对时间范围（小时）
ITEM_COUNT_MIN = 1               # 单次投递最少物品数
ITEM_COUNT_MAX = 20              # 单次投递最多物品数

# Demo 模式：跳过 GPS 定位校验（答辩演示时设为 True）
DEMO_MODE = False

# 定位参数
GPS_TIMEOUT_MS = 8000            # 浏览器定位超时（毫秒）
GPS_MAX_AGE_MS = 30000           # 浏览器定位缓存有效期（毫秒）
