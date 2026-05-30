"""AI 识别服务

策略：
1) 优先使用 torchvision 预训练 MobileNetV3 提取 ImageNet 类别概率
   - 用 ImageNet 中与「纸箱 / 塑料瓶 / 玻璃瓶」相关的类别索引聚合得到品类概率
   - 用图像清晰度/对比度/纹理统计估计完整度
2) 若 torch 不可用 / AI_MOCK_MODE=True，降级为基于图像统计的 mock
3) 所有输出均给出置信度与是否需要重拍提示

输出统一为 dict：
    {category, grade, score, recommend, recommend_desc, co2_estimate, need_recheck}
"""
from __future__ import annotations

import io
import random
import math
from typing import Tuple

from PIL import Image, ImageFilter, ImageStat

from ..config import (
    AI_MOCK_MODE, AI_CONFIDENCE_THRESHOLD,
    CATEGORIES, GRADES, PATH_MAP, PATH_DESC,
)

# ---------- 尝试加载 torch ----------
_TORCH_OK = False
_model = None
_transform = None
_imagenet_idx_to_cat: dict[int, str] = {}

if not AI_MOCK_MODE:
    try:
        import torch
        from torchvision import models, transforms

        # ImageNet 中可关联到三类的代表索引（来自 ImageNet 1000 类）
        # 纸箱 carton(478)、packet(692)、cardboard(无单独类，用 carton 兜底)
        # 塑料 water_bottle(898)、plastic_bag(728)、pop_bottle(737)
        # 玻璃 beer_bottle(440)、wine_bottle(907)、beer_glass(441)
        _imagenet_idx_to_cat = {
            478: "纸箱", 692: "纸箱", 720: "纸箱",
            898: "塑料", 728: "塑料", 737: "塑料",
            440: "玻璃", 907: "玻璃", 441: "玻璃",
        }

        _model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
        _model.eval()
        _transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])
        _TORCH_OK = True
    except Exception as e:  # noqa: BLE001
        print(f"[ai_service] torch 加载失败，降级为 mock 模式: {e}")
        _TORCH_OK = False


# ---------- 图像统计：估计完整度 ----------
def _grade_by_stats(img: Image.Image) -> Tuple[str, float]:
    """根据图像的亮度/对比度/边缘密度估计完整度

    返回 (grade, sub_score 0~1)
    经验启发式：
        - 边缘密度越高（破损边缘多）→ 越倾向 破损
        - 颜色方差极低（受潮变深均匀）→ 受潮
        - 中等清晰、对比正常 → 轻损
        - 高清晰、低边缘噪声 → 完好
    """
    gray = img.convert("L").resize((128, 128))
    stat = ImageStat.Stat(gray)
    mean = stat.mean[0]
    stddev = stat.stddev[0]

    edge = gray.filter(ImageFilter.FIND_EDGES)
    edge_stat = ImageStat.Stat(edge)
    edge_mean = edge_stat.mean[0]

    # 启发评分（0~1）
    if mean < 70 and stddev < 35:
        return "受潮", 0.75
    if edge_mean > 35:
        return "破损", 0.78
    if edge_mean > 22:
        return "轻损", 0.80
    return "完好", 0.88


# ---------- 主分类：torch 路径 ----------
def _predict_with_torch(img: Image.Image) -> Tuple[str, float]:
    import torch
    x = _transform(img.convert("RGB")).unsqueeze(0)
    with torch.no_grad():
        logits = _model(x)
        probs = torch.softmax(logits, dim=1)[0]

    # 聚合到三品类
    cat_scores = {c: 0.0 for c in CATEGORIES}
    for idx, cat in _imagenet_idx_to_cat.items():
        cat_scores[cat] += float(probs[idx])

    total = sum(cat_scores.values())

    # 如果三类总分极低，说明图片不是回收物 → 拒绝识别
    if total < 0.02:
        return "unknown", round(total, 4)

    # 归一化，保留真实置信度（不再人为抬高）
    best = max(cat_scores, key=cat_scores.get)
    score = cat_scores[best] / max(total, 1e-6)
    return best, round(min(score, 0.99), 3)


# ---------- 主分类：mock 路径 ----------
def _predict_mock(img: Image.Image) -> Tuple[str, float]:
    r, g, b = ImageStat.Stat(img.convert("RGB").resize((64, 64))).mean
    # 若 RGB 三个通道均值非常接近（灰度图/非回收物），拒绝识别
    if max(r, g, b) - min(r, g, b) < 10:
        return "unknown", round(random.uniform(0.05, 0.15), 3)
    if r > g + 5 and r > b + 5:
        return "纸箱", round(random.uniform(0.65, 0.85), 3)
    if b > r:
        return "塑料", round(random.uniform(0.60, 0.82), 3)
    return "玻璃", round(random.uniform(0.58, 0.80), 3)


# ---------- 对外主函数 ----------
def predict_image(image_bytes: bytes) -> dict:
    """主入口：输入图片字节，返回识别结果 dict"""
    img = Image.open(io.BytesIO(image_bytes))

    if _TORCH_OK:
        category, cat_score = _predict_with_torch(img)
    else:
        category, cat_score = _predict_mock(img)

    # 非回收物：直接返回低置信度，提示重拍
    if category == "unknown":
        return {
            "category": "无法识别",
            "grade": "未知",
            "score": cat_score,
            "recommend": "C",
            "recommend_desc": "无法识别，请重新拍摄回收物照片",
            "co2_estimate": 0.0,
            "need_recheck": True,
        }

    grade, grade_score = _grade_by_stats(img)
    score = round((cat_score * 0.6 + grade_score * 0.4), 3)

    recommend = PATH_MAP[grade]
    co2_estimate = _estimate_co2(category, recommend)

    return {
        "category": category,
        "grade": grade,
        "score": score,
        "recommend": recommend,
        "recommend_desc": PATH_DESC[recommend],
        "co2_estimate": co2_estimate,
        "need_recheck": score < AI_CONFIDENCE_THRESHOLD,
    }


def _estimate_co2(category: str, recommend: str) -> float:
    """根据品类与推荐路径估算单次减碳量（粗略，真实计算见 carbon_service）"""
    base = {"纸箱": 0.35, "塑料": 0.10, "玻璃": 0.30}.get(category, 0.20)
    factor = 1.0 if recommend in ("A", "B") else 0.43
    return round(base * factor, 3)


def ai_status() -> dict:
    """暴露当前 AI 模式，便于前端展示"""
    return {
        "mode": "torch-mobilenetv3" if _TORCH_OK else "mock-heuristic",
        "categories": CATEGORIES,
        "grades": GRADES,
    }


# ---------- 感知哈希：用于图片相似度去重 ----------
def compute_photo_hash(image_bytes: bytes) -> str:
    """
    计算平均哈希（aHash），用于快速判断两张图是否同一回收物。
    算法：缩放到 32×32 灰度 → 计算像素均值 → 每像素与均值比较 → 得到 1024-bit 哈希
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("L").resize((32, 32))
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = ["1" if p > avg else "0" for p in pixels]
    # 每 4 位转十六进制，得到 256 字符的 hex 串
    hex_str = ""
    for i in range(0, len(bits), 4):
        nibble = bits[i:i + 4]
        hex_str += hex(int("".join(nibble), 2))[2:]
    return hex_str


def hamming_distance(h1: str, h2: str) -> int:
    """计算两个十六进制哈希串的汉明距离"""
    if len(h1) != len(h2):
        return 999999
    # 转回 bit 串
    b1 = bin(int(h1, 16))[2:].zfill(len(h1) * 4)
    b2 = bin(int(h2, 16))[2:].zfill(len(h2) * 4)
    return sum(c1 != c2 for c1, c2 in zip(b1, b2))


def is_similar_to_recent(photo_hash: str, recent_hashes: list[str], threshold: float = 0.15) -> tuple[bool, float]:
    """
    判断新照片是否与近期提交过于相似。
    threshold=0.15 表示允许最大 15% 的位差异（即汉明距离 ≤ 1024*0.15 ≈ 154）。
    返回 (is_similar, max_similarity_pct)
    """
    if not photo_hash or not recent_hashes:
        return False, 0.0
    max_bits = 1024
    best = 1.0  # 最小差异比例
    for h in recent_hashes:
        if not h:
            continue
        dist = hamming_distance(photo_hash, h)
        diff_pct = dist / max_bits
        if diff_pct < best:
            best = diff_pct
    similarity = 1.0 - best
    return similarity > (1.0 - threshold), round(similarity, 3)
