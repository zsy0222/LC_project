"""AI 模型训练脚本 (v2 — 提升准确率)

改进：
  1. 类别权重损失 — 缓解 1.7x 样本不均衡
  2. RandAugment 风格强增强 — 提升泛化
  3. 提前解冻 backbone — epoch 5 释放全参数
  4. Label Smoothing — 防止过拟合
  5. ReduceLROnPlateau — 自适应学习率

用法：
  python -m src.train --data_dir ./dataset --epochs 30
"""

import argparse, json, os, sys
from collections import Counter
import warnings
warnings.filterwarnings("ignore")

import torch, torch.nn as nn, torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
from sklearn.metrics import classification_report

CATEGORIES = ["外卖厨余", "快递纸箱", "塑料", "有害"]


def get_train_transform():
    """强增强"""
    return transforms.Compose([
        transforms.RandomResizedCrop(224, scale=(0.6, 1.0), ratio=(0.75, 1.33)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.1),
        transforms.RandomRotation(degrees=20),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.08),
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1), shear=5),
        transforms.ToTensor(),
        transforms.RandomErasing(p=0.2, scale=(0.02, 0.1)),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def get_val_transform():
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def create_model(num_classes: int = 4) -> nn.Module:
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)

    # 冻结 backbone
    for name, param in model.named_parameters():
        if "classifier" not in name:
            param.requires_grad = False

    # 替换分类头：加 Dropout
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(in_features, num_classes),
    )
    return model


def compute_class_weights(dataset) -> torch.Tensor:
    """计算类别权重：样本少的类权重大"""
    labels = [label for _, label in dataset.samples]
    counts = Counter(labels)
    total = len(labels)
    weights = [total / counts[i] for i in range(len(dataset.classes))]
    return torch.tensor(weights, dtype=torch.float)


def train_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss, correct, total = 0.0, 0, 0
    for imgs, labels in loader:
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(imgs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * imgs.size(0)
        _, preds = torch.max(outputs, 1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)
    return total_loss / total, correct / total


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss, correct, total = 0.0, 0, 0
    all_preds, all_labels = [], []
    for imgs, labels in loader:
        imgs, labels = imgs.to(device), labels.to(device)
        outputs = model(imgs)
        loss = criterion(outputs, labels)
        total_loss += loss.item() * imgs.size(0)
        _, preds = torch.max(outputs, 1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)
        all_preds.extend(preds.cpu().tolist())
        all_labels.extend(labels.cpu().tolist())
    return total_loss / total, correct / total, all_preds, all_labels


def main():
    parser = argparse.ArgumentParser(description="Waste Classifier Training v2")
    parser.add_argument("--data_dir", required=True)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--output_dir", default="model")
    parser.add_argument("--val_split", type=float, default=0.2)
    parser.add_argument("--unfreeze_epoch", type=int, default=5, help="提前解冻 backbone")
    parser.add_argument("--label_smoothing", type=float, default=0.1)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[device] {device}")

    # 1. 加载数据集（不带 transform 以便划分）
    raw_dataset = datasets.ImageFolder(root=args.data_dir)
    found = raw_dataset.classes
    print(f"[data] {len(raw_dataset)} images, {len(found)} classes: {found}")

    # 2. 三层划分：训练 80% / 验证 10% / 测试 10%
    total = len(raw_dataset)
    test_size = int(total * 0.1)
    val_size = int(total * 0.1)
    train_size = total - val_size - test_size
    remainder, test_raw = torch.utils.data.random_split(
        raw_dataset, [train_size + val_size, test_size],
        generator=torch.Generator().manual_seed(42),
    )
    train_raw, val_raw = torch.utils.data.random_split(
        remainder, [train_size, val_size],
        generator=torch.Generator().manual_seed(84),
    )

    # 分别包装 transform
    train_ds = _TransformDataset(train_raw, raw_dataset, get_train_transform())
    val_ds   = _TransformDataset(val_raw,   raw_dataset, get_val_transform())
    test_ds  = _TransformDataset(test_raw,  raw_dataset, get_val_transform())

    # 类别权重（仅在 Loss 中加权，无需 WeightedSampler 节省 CPU）
    class_weights = compute_class_weights(raw_dataset).to(device)
    print(f"[weights] {dict(zip(found, class_weights.tolist()))}")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False, num_workers=0)
    test_loader  = DataLoader(test_ds,  batch_size=args.batch_size, shuffle=False, num_workers=0)

    num_classes = len(found)
    print(f"[split] train={train_size} val={val_size} test={test_size} classes={num_classes}\n")

    # 3. 模型
    model = create_model(num_classes=num_classes).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=args.label_smoothing)
    optimizer = optim.AdamW(model.classifier.parameters(), lr=args.lr, weight_decay=0.01)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=3)

    # 4. 训练
    print(f"[train] {args.epochs} epochs, batch={args.batch_size}, lr={args.lr}\n")
    best_acc = 0.0; best_epoch = 0
    os.makedirs(args.output_dir, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        if epoch == args.unfreeze_epoch:
            print(f"  [unlock] epoch {epoch} - unfreezing backbone")
            for param in model.parameters():
                param.requires_grad = True
            optimizer.add_param_group({
                "params": [p for n, p in model.named_parameters() if "classifier" not in n],
                "lr": args.lr * 0.1,
                "weight_decay": 0.01,
            })

        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc, preds, labels = evaluate(model, val_loader, criterion, device)
        scheduler.step(val_acc)

        lr_now = optimizer.param_groups[0]["lr"]
        mark = ""
        if val_acc > best_acc:
            best_acc = val_acc; best_epoch = epoch
            torch.save({
                "model_state_dict": model.state_dict(),
                "classes": found,
                "num_classes": num_classes,
                "val_acc": val_acc,
            }, os.path.join(args.output_dir, "recycle_classifier.pth"))
            mark = " [BEST]"

        print(f"  Epoch {epoch:2d}/{args.epochs} | T-loss {train_loss:.4f} T-acc {train_acc:.3f} | "
              f"V-loss {val_loss:.4f} V-acc {val_acc:.3f} | lr {lr_now:.1e}{mark}")

    # 5. 最终评估
    print(f"\n[eval] best: epoch {best_epoch}, val_acc={best_acc:.4f}")
    checkpoint = torch.load(os.path.join(args.output_dir, "recycle_classifier.pth"), map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])

    # 验证集报告
    _, _, val_preds, val_labels = evaluate(model, val_loader, criterion, device)
    print("[val set]")
    print(classification_report(val_labels, val_preds, target_names=found, zero_division=0))

    # 测试集报告（最终泛化能力）
    _, test_acc, test_preds, test_labels = evaluate(model, test_loader, criterion, device)
    print(f"[test set] acc={test_acc:.4f}")
    print(classification_report(test_labels, test_preds, target_names=found, zero_division=0))

    label_map = {i: name for i, name in enumerate(found)}
    with open(os.path.join(args.output_dir, "class_labels.json"), "w", encoding="utf-8") as f:
        json.dump(label_map, f, ensure_ascii=False, indent=2)
    print(f"[OK] model saved to {args.output_dir}/")


class _TransformDataset(torch.utils.data.Dataset):
    """对 random_split 的 subset 应用 transform"""
    def __init__(self, subset, full_dataset, transform):
        self.indices = subset.indices
        self.full_dataset = full_dataset
        self.transform = transform

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, idx):
        img, label = self.full_dataset[self.indices[idx]]
        # PIL palette transparency fix
        if img.mode == "P":
            img = img.convert("RGBA").convert("RGB")
        elif img.mode == "RGBA":
            img = img.convert("RGB")
        return self.transform(img), label


if __name__ == "__main__":
    main()
