#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
debug.py — ResNet50 图像分类训练脚本
=====================================

负责训练 ResNet50 图像分类模型。

数据集目录结构（torchvision.datasets.ImageFolder 格式）:
    input/
        train/              # 训练集（必选）
            class_1/*.jpg
            class_2/*.jpg
            ...
        val/                # 验证集（可选，不提供时自动从训练集划分）
            class_1/*.jpg
            ...

输出（output/）:
    best_model.pth          验证集准确率最高的模型权重（含完整 checkpoint）
    last_model.pth          最后一个 epoch 的模型权重
    training_log.txt        训练日志

用法示例:
    python debug.py --epochs 30 --batch-size 32 --lr 0.001
    python debug.py --pretrained False --epochs 60
    python debug.py --resume output/last_model.pth --epochs 50
"""

import argparse
import logging
import os
import random
import time

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, models, transforms

try:  # torchvision >= 0.13 的新权重 API
    from torchvision.models import ResNet50_Weights
    NEW_API = True
except ImportError:
    NEW_API = False

LOG = logging.getLogger("resnet50")


def setup_logger(log_path):
    """配置日志：同时输出到控制台和日志文件。"""
    handlers = [logging.StreamHandler()]
    if log_path:
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


def set_seed(seed):
    """固定随机种子，保证实验可复现。"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def build_transforms(resize=256, crop=224, train=True):
    """构造数据增强管道。"""
    if train:
        return transforms.Compose([
            transforms.RandomResizedCrop(crop),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
    return transforms.Compose([
        transforms.Resize(resize),
        transforms.CenterCrop(crop),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])


def get_model(num_classes, pretrained=True):
    """构建 ResNet50，替换全连接层适配类别数。"""
    if NEW_API:
        weights = ResNet50_Weights.IMAGENET1K_V1 if pretrained else None
        model = models.resnet50(weights=weights)
    else:
        model = models.resnet50(pretrained=pretrained)
    in_features = model.fc.in_features
    model.fc = nn.Linear(in_features, num_classes)
    return model


def load_datasets(data_dir, val_ratio=0.1):
    """加载 ImageFolder 数据集；无 val/ 目录时从训练集划分验证集。"""
    train_dir = os.path.join(data_dir, "train")
    val_dir = os.path.join(data_dir, "val")
    if not os.path.isdir(train_dir):
        raise FileNotFoundError(f"未找到训练集目录: {train_dir}")

    train_ds = datasets.ImageFolder(train_dir, build_transforms(train=True))
    if os.path.isdir(val_dir):
        val_ds = datasets.ImageFolder(val_dir, build_transforms(train=False))
    else:
        LOG.info("未找到 val/ 目录，将从训练集中按比例 %.2f 划分验证集", val_ratio)
        n_val = int(len(train_ds) * val_ratio)
        n_train = len(train_ds) - n_val
        train_ds, val_ds = random_split(train_ds, [n_train, n_val])
    return train_ds, val_ds


def train_one_epoch(model, loader, criterion, optimizer, device, epoch):
    """训练一个 epoch，返回 (平均损失, 准确率)。"""
    model.train()
    running_loss, correct, total = 0.0, 0, 0
    for i, (inputs, labels) in enumerate(loader):
        inputs, labels = inputs.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * inputs.size(0)
        _, preds = torch.max(outputs, 1)
        total += labels.size(0)
        correct += (preds == labels).sum().item()

        if (i + 1) % 10 == 0:
            LOG.info("Epoch %d [%d/%d] loss=%.4f acc=%.4f",
                     epoch + 1, i + 1, len(loader), loss.item(),
                     correct / total)
    return running_loss / total, correct / total


@torch.no_grad()
def validate(model, loader, criterion, device):
    """在验证集上评估，返回 (平均损失, 准确率)。"""
    model.eval()
    running_loss, correct, total = 0.0, 0, 0
    for inputs, labels in loader:
        inputs, labels = inputs.to(device), labels.to(device)
        outputs = model(inputs)
        loss = criterion(outputs, labels)

        running_loss += loss.item() * inputs.size(0)
        _, preds = torch.max(outputs, 1)
        total += labels.size(0)
        correct += (preds == labels).sum().item()
    return running_loss / total, correct / total


def save_checkpoint(model, optimizer, epoch, acc, path):
    """保存完整 checkpoint。"""
    torch.save({
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "val_acc": acc,
    }, path)
    LOG.info("模型已保存: %s (val_acc=%.4f)", path, acc)


def parse_args():
    parser = argparse.ArgumentParser(description="ResNet50 图像分类训练")
    parser.add_argument("--data-dir", default="input", help="数据集根目录（默认 input）")
    parser.add_argument("--output-dir", default="output", help="模型输出目录（默认 output）")
    parser.add_argument("--epochs", type=int, default=30, help="训练轮数")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3, help="学习率")
    parser.add_argument("--momentum", type=float, default=0.9)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--pretrained", type=lambda s: s.lower() != "false",
                        default=True, help="是否使用 ImageNet 预训练权重")
    parser.add_argument("--resume", default=None, help="从 checkpoint 继续训练")
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--val-ratio", type=float, default=0.1,
                        help="无 val/ 目录时从训练集划分验证集的比例")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log-file", default="training_log.txt")
    return parser.parse_args()


def main():
    args = parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    log_path = os.path.join(args.output_dir, args.log_file) if args.log_file else None
    setup_logger(log_path)
    set_seed(args.seed)

    device = get_device()
    LOG.info("使用设备: %s", device)

    # 数据
    train_ds, val_ds = load_datasets(args.data_dir, args.val_ratio)
    if hasattr(train_ds, "classes"):
        classes = train_ds.classes
    else:  # random_split 返回 Subset
        classes = train_ds.dataset.classes
    num_classes = len(classes)
    LOG.info("训练样本数: %d, 验证样本数: %d, 类别数: %d (%s)",
             len(train_ds), len(val_ds), num_classes, classes)

    # 模型 / 损失 / 优化器
    model = get_model(num_classes, args.pretrained).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(model.parameters(), lr=args.lr,
                          momentum=args.momentum, weight_decay=args.weight_decay)
    scheduler = lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.1)

    # 断点续训
    start_epoch, best_acc = 0, 0.0
    if args.resume and os.path.isfile(args.resume):
        ckpt = torch.load(args.resume, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        start_epoch = ckpt.get("epoch", 0) + 1
        best_acc = ckpt.get("val_acc", 0.0)
        LOG.info("从 %s 恢复训练 (epoch=%d)", args.resume, start_epoch)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                              num_workers=args.num_workers)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False,
                            num_workers=args.num_workers)

    best_path = os.path.join(args.output_dir, "best_model.pth")
    last_path = os.path.join(args.output_dir, "last_model.pth")

    # 训练循环
    for epoch in range(start_epoch, args.epochs):
        t0 = time.time()
        tr_loss, tr_acc = train_one_epoch(model, train_loader, criterion,
                                          optimizer, device, epoch)
        va_loss, va_acc = validate(model, val_loader, criterion, device)
        scheduler.step()
        LOG.info("Epoch %d/%d train_loss=%.4f train_acc=%.4f | val_loss=%.4f val_acc=%.4f | %.1fs",
                 epoch + 1, args.epochs, tr_loss, tr_acc, va_loss, va_acc,
                 time.time() - t0)

        if va_acc > best_acc:
            best_acc = va_acc
            save_checkpoint(model, optimizer, epoch, va_acc, best_path)
        save_checkpoint(model, optimizer, epoch, va_acc, last_path)

    LOG.info("训练完成，最佳验证准确率: %.4f，模型位于 %s", best_acc, best_path)


if __name__ == "__main__":
    main()
