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
CATEGORIES = ["纸箱", "塑料", "玻璃"]
GRADES = ["完好", "轻损", "破损", "受潮"]

# 路径推荐映射
PATH_MAP = {
    "完好": "A",   # 共享 / 再利用
    "轻损": "B",   # 手工改造
    "破损": "C",   # 直接回收
    "受潮": "C",
}
PATH_DESC = {
    "A": "共享/再利用",
    "B": "手工改造",
    "C": "直接回收",
}

# 服务地址
HOST = "127.0.0.1"
PORT = 8000

# 反作弊参数
LOCATION_MAX_DISTANCE_M = 100     # GPS 定位最大允许距离（米）
COOLDOWN_SECONDS = 30            # 同点位提交冷却时间（秒）
PHOTO_SIMILARITY_THRESHOLD = 0.15  # 图片相似度阈值（≤15% 差异视为同一物品）
PHOTO_SIMILARITY_RECENT = 10     # 相似度比对范围：用户最近 N 条提交
ITEM_COUNT_MIN = 1               # 单次投递最少物品数
ITEM_COUNT_MAX = 20              # 单次投递最多物品数

# 定位参数
GPS_TIMEOUT_MS = 8000            # 浏览器定位超时（毫秒）
GPS_MAX_AGE_MS = 30000           # 浏览器定位缓存有效期（毫秒）
