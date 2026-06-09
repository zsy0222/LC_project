"""下载并整理回收物四分类训练数据集

来源：Hugging Face — omasteam/waste-garbage-management-dataset
大小：~19,762 张图片，无需登录
许可证：公开数据集

类别映射：
  原标签          → 回收品类
  Biological       → 外卖厨余
  Cardboard        → 快递纸箱
  Plastic          → 塑料
  Battery          → 有害

输出目录结构：
  dataset/
    ├── 外卖厨余/
    ├── 快递纸箱/
    ├── 塑料/
    └── 有害/

用法：
  pip install datasets Pillow
  python -m src.download_dataset
"""

import os
import sys
from pathlib import Path
from collections import Counter

# 类别映射
LABEL_MAP = {
    "Biological": "外卖厨余",
    "Cardboard": "快递纸箱",
    "Plastic": "塑料",
    "Battery": "有害",
}

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "dataset"


def main():
    # Windows 终端强制 UTF-8
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("[download] Fetching dataset from Hugging Face...")
    print("  omasteam/waste-garbage-management-dataset")
    print()

    try:
        from datasets import load_dataset
    except ImportError:
        print("[ERROR] 请先安装 datasets: pip install datasets")
        sys.exit(1)

    # 下载全部数据（train split 包含所有图片）
    ds = load_dataset("omasteam/waste-garbage-management-dataset", split="train")
    print(f"   总计 {len(ds)} 张图片")
    print()

    # 统计原始类别分布
    label_counts = Counter()
    # 遍历一次统计
    for item in ds:
        label_counts[item["label"]] += 1

    # 获取标签名（从 features 中读取）
    feature_label = ds.features["label"]
    if hasattr(feature_label, "names"):
        label_names = feature_label.names
    else:
        label_names = feature_label.int2str if hasattr(feature_label, "int2str") else None

    if label_names is None:
        print("[warn]  无法读取标签名，请检查数据集结构")
        sys.exit(1)

    print("[stats] 原始类别分布：")
    total_used = 0
    for idx, name in enumerate(label_names):
        count = label_counts.get(idx, 0)
        mapped = LABEL_MAP.get(name, "（跳过）")
        if mapped == "（跳过）":
            print(f"   {name:20s}: {count:5d} → {mapped}")
        else:
            print(f"   {name:20s}: {count:5d} → {mapped}")
            total_used += count

    print(f"\n   共计 {total_used} 张可用于四分类训练")
    print()

    # 创建输出目录并保存图片
    print("[save] 保存图片到 dataset/ ...")
    for cat in LABEL_MAP.values():
        (OUTPUT_DIR / cat).mkdir(parents=True, exist_ok=True)

    saved = Counter()
    for item in ds:
        label_idx = item["label"]
        original_label = label_names[label_idx]
        target_cat = LABEL_MAP.get(original_label)
        if target_cat is None:
            continue

        img = item["image"]
        idx = saved[target_cat]
        saved[target_cat] += 1

        # 保存为 JPEG
        out_path = OUTPUT_DIR / target_cat / f"{original_label.lower()}_{idx:05d}.jpg"
        try:
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")
            img.save(out_path, "JPEG", quality=92)
        except Exception as e:
            print(f"   [warn] 跳过损坏图片: {out_path} ({e})")

    print()
    print("[OK] 下载完成！")
    for cat in LABEL_MAP.values():
        print(f"   {cat}: {saved[cat]} 张")
    print()
    print(f"   总计 {sum(saved.values())} 张训练图片")
    print()
    print("[next] 下一步：")
    print("   python -m src.train --data_dir ./dataset --epochs 20")


if __name__ == "__main__":
    main()
