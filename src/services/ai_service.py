"""AI 识别服务

加载优先级：
  1) 微调 MobileNetV3 四分类模型（model/recycle_classifier.pth）→ 精准分类
  2) ImageNet 预训练 MobileNetV3 + 索引聚合 → 粗糙但可用
  3) 图像统计启发式 mock → 纯降级

输出统一为 dict：
    {category, grade, score, recommend, recommend_desc, co2_estimate, need_recheck}
"""
from __future__ import annotations

import io
import json
import random
import math
from datetime import datetime
from typing import Tuple, Optional

from PIL import Image, ImageFilter, ImageStat

from ..config import (
    AI_MOCK_MODE, AI_CONFIDENCE_THRESHOLD, AI_NON_RECYCLABLE_THRESHOLD, AI_NON_RECYCLABLE_THRESHOLD_HAZARDOUS,
    CATEGORIES, GRADES, PATH_MAP, PATH_DESC,
    AI_MODEL_PATH, AI_CLASS_LABELS_PATH,
)

# ---------- 层级 1：尝试加载微调四分类模型 ----------
_FINETUNED_OK = False
_finetuned_model = None
_finetuned_transform = None
_finetuned_classes: list[str] = []

if not AI_MOCK_MODE:
    try:
        import torch
        from torchvision import models, transforms

        checkpoint = torch.load(str(AI_MODEL_PATH), map_location="cpu", weights_only=False)
        num_classes = checkpoint.get("num_classes", 4)
        _finetuned_classes = checkpoint.get("classes", CATEGORIES)

        _finetuned_model = models.mobilenet_v3_small(weights=None)
        in_features = _finetuned_model.classifier[-1].in_features
        _finetuned_model.classifier[-1] = torch.nn.Sequential(
            torch.nn.Dropout(0.3),
            torch.nn.Linear(in_features, num_classes),
        )
        _finetuned_model.load_state_dict(checkpoint["model_state_dict"])
        _finetuned_model.eval()

        _finetuned_transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        _FINETUNED_OK = True
        print(f"[ai_service] [OK] 加载微调模型 (val_acc={checkpoint.get('val_acc', '?')}, classes={_finetuned_classes})")
    except FileNotFoundError:
        print(f"[ai_service] [warn] 微调模型不存在 ({AI_MODEL_PATH})，降级到 ImageNet 聚合")
    except Exception as e:
        print(f"[ai_service] [warn] 微调模型加载失败: {e}，降级到 ImageNet 聚合")

# ---------- 层级 2：ImageNet 预训练 + 索引聚合 ----------
_IMAGENET_OK = False
_imagenet_model = None
_imagenet_transform = None
_imagenet_idx_to_cat: dict[int, str] = {}

if not _FINETUNED_OK and not AI_MOCK_MODE:
    try:
        import torch
        from torchvision import models, transforms

        _imagenet_idx_to_cat = {
            930: "外卖厨余", 416: "外卖厨余", 964: "外卖厨余",
            489: "外卖厨余", 497: "外卖厨余", 965: "外卖厨余",
            101: "外卖厨余", 937: "外卖厨余", 943: "外卖厨余",
            925: "外卖厨余", 587: "外卖厨余", 967: "外卖厨余",
            933: "外卖厨余", 934: "外卖厨余", 745: "外卖厨余",
            478: "快递纸箱", 692: "快递纸箱", 720: "快递纸箱",
            898: "塑料", 728: "塑料", 737: "塑料",
            617: "有害", 660: "有害",
        }

        _imagenet_model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
        _imagenet_model.eval()
        _imagenet_transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        _IMAGENET_OK = True
    except Exception as e:
        print(f"[ai_service] torch 加载失败，降级为 mock: {e}")
        _IMAGENET_OK = False


# ---------- 图像统计：估计完整度 ----------
def _grade_by_stats(img: Image.Image) -> Tuple[str, float]:
    gray = img.convert("L").resize((128, 128))
    stat = ImageStat.Stat(gray)
    mean = stat.mean[0]
    stddev = stat.stddev[0]

    edge = gray.filter(ImageFilter.FIND_EDGES)
    edge_stat = ImageStat.Stat(edge)
    edge_mean = edge_stat.mean[0]

    if mean < 70 and stddev < 35:
        return "受潮", 0.75
    if edge_mean > 35:
        return "破损", 0.78
    if edge_mean > 22:
        return "轻损", 0.80
    return "完好", 0.88


# ---------- 层级 1：微调四分类模型 ----------
def _predict_finetuned(img: Image.Image) -> Tuple[str, float]:
    import torch
    x = _finetuned_transform(img.convert("RGB")).unsqueeze(0)
    with torch.no_grad():
        logits = _finetuned_model(x)
        probs = torch.softmax(logits, dim=1)[0]
    best_idx = int(torch.argmax(probs))
    score = round(float(probs[best_idx]), 3)
    category = _finetuned_classes[best_idx] if best_idx < len(_finetuned_classes) else "无法识别"
    # 有害垃圾分类更严格，需要 ≥85% 才放行
    threshold = AI_NON_RECYCLABLE_THRESHOLD_HAZARDOUS if category == "有害" else AI_NON_RECYCLABLE_THRESHOLD
    if score < threshold:
        return "非回收物", score
    return category, score


# ---------- 层级 2：ImageNet 聚合 ----------
def _predict_imagenet(img: Image.Image) -> Tuple[str, float]:
    import torch
    x = _imagenet_transform(img.convert("RGB")).unsqueeze(0)
    with torch.no_grad():
        logits = _imagenet_model(x)
        probs = torch.softmax(logits, dim=1)[0]

    cat_scores = {c: 0.0 for c in CATEGORIES}
    for idx, cat in _imagenet_idx_to_cat.items():
        cat_scores[cat] += float(probs[idx])

    total = sum(cat_scores.values())
    if total < 0.02:
        return "unknown", round(total, 4)

    best = max(cat_scores, key=cat_scores.get)
    score = cat_scores[best] / max(total, 1e-6)
    return best, round(min(score, 0.99), 3)


# ---------- 层级 3：mock ----------
def _predict_mock(img: Image.Image) -> Tuple[str, float]:
    r, g, b = ImageStat.Stat(img.convert("RGB").resize((64, 64))).mean
    brightness = (r + g + b) / 3
    if max(r, g, b) - min(r, g, b) < 10:
        return "unknown", round(random.uniform(0.05, 0.15), 3)
    if r > g and g > b and brightness < 180:
        return "外卖厨余", round(random.uniform(0.65, 0.85), 3)
    if r > g + 5 and r > b + 5:
        return "快递纸箱", round(random.uniform(0.65, 0.85), 3)
    if b > r:
        return "塑料", round(random.uniform(0.60, 0.82), 3)
    return "快递纸箱", round(random.uniform(0.58, 0.80), 3)


# ---------- 对外主函数 ----------
def predict_image(image_bytes: bytes) -> dict:
    img = Image.open(io.BytesIO(image_bytes))

    if _FINETUNED_OK:
        category, cat_score = _predict_finetuned(img)
    elif _IMAGENET_OK:
        category, cat_score = _predict_imagenet(img)
    else:
        category, cat_score = _predict_mock(img)

    if category == "unknown" or category == "非回收物":
        return {
            "category": "非回收物",
            "grade": "未知",
            "score": cat_score,
            "recommend": "C",
            "recommend_desc": "当前检测非回收物，请确认是否投递",
            "co2_estimate": 0.0,
            "need_recheck": True,
        }

    grade, grade_score = _grade_by_stats(img)
    score = round((cat_score * 0.6 + grade_score * 0.4), 3)

    recommend = PATH_MAP[grade]
    co2_estimate = round(_estimate_co2(category, recommend), 3)

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
    ton_factor = {
        "外卖厨余": 90.82, "快递纸箱": 1200.0, "塑料": 2000.0, "有害": 700.0,
        "纸箱": 1200.0, "玻璃": 500.0,
    }.get(category, 100.0)
    weight = {"外卖厨余": 0.5, "快递纸箱": 0.2, "塑料": 0.05, "有害": 0.1, "纸箱": 0.2}.get(category, 0.2)
    return round(ton_factor * weight / 1000, 4)


def ai_status() -> dict:
    """暴露当前 AI 模式"""
    if _FINETUNED_OK:
        mode = f"finetuned-{len(_finetuned_classes)}class"
        extra = {"trained_classes": _finetuned_classes, "val_acc_approx": "best"}
    elif _IMAGENET_OK:
        mode = "imagenet-mobilenetv3"
        extra = {}
    else:
        mode = "mock-heuristic"
        extra = {}
    return {"mode": mode, "categories": CATEGORIES, "grades": GRADES, **extra}


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


# ---------- EXIF 拍摄时间提取 ----------
_EXIF_DATETIME_ORIGINAL = 36867  # EXIF tag: DateTimeOriginal
_EXIF_DATETIME_DIGITIZED = 36868  # EXIF tag: DateTimeDigitized (fallback)


def extract_exif_datetime(image_bytes: bytes) -> datetime | None:
    """
    从 JPEG 字节中提取 EXIF DateTimeOriginal（拍摄时间）。
    返回 datetime 对象，若无 EXIF 或读取失败返回 None。

    EXIF 格式：'YYYY:MM:DD HH:MM:SS'
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif = img._getexif()
        if not exif:
            return None

        # 优先用 DateTimeOriginal，其次用 DateTimeDigitized
        for tag in (_EXIF_DATETIME_ORIGINAL, _EXIF_DATETIME_DIGITIZED):
            raw = exif.get(tag)
            if raw and isinstance(raw, str):
                try:
                    return datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    continue

        return None
    except Exception:
        return None


def is_exif_too_old(image_bytes: bytes, max_age_minutes: int) -> tuple[bool, str]:
    """
    检查照片 EXIF 拍摄时间是否过期。
    返回 (is_too_old, reason)。
    - 无 EXIF → too_old=True, reason="无EXIF"
    - 时间超过 max_age_minutes → too_old=True, reason="X分钟前拍摄"
    - 正常 → too_old=False, reason=""
    """
    dt = extract_exif_datetime(image_bytes)
    if dt is None:
        return True, "照片缺少拍摄信息（无EXIF），请使用相机现场拍摄"
    age = (datetime.utcnow() - dt).total_seconds()
    if age < 0:
        # 设备时钟不准，允许少量超前
        pass
    age_min = abs(age) / 60
    if age_min > max_age_minutes:
        return True, f"照片拍摄于 {age_min:.0f} 分钟前（允许 {max_age_minutes} 分钟内），请现场重新拍摄"
    return False, ""
