#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_analize.py — 数据集清洗与分析脚本
=======================================

负责扫描数据集目录（默认 input/），检查图片的：
  - 有效性：能否正常解码（损坏文件检测）
  - 尺寸：过滤边长过小的异常图片
  - 重复：按 MD5 判定内容完全相同的文件

输出统计报告，并在 --clean 模式下把问题文件移动到隔离目录。

用法示例:
    python data_analize.py                      # 只分析，输出报告
    python data_analize.py --clean              # 分析并清理（移动到隔离目录）
    python data_analize.py --min-size 64        # 自定义最小边长
"""

import argparse
import hashlib
import os
import shutil
import sys
from collections import Counter, defaultdict

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:
    sys.exit("缺少依赖 Pillow，请先安装: pip install pillow")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}


def md5_of(path, chunk=1 << 20):
    """计算文件 MD5。"""
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def scan(data_dir, min_size):
    """扫描目录，返回 (统计信息, 问题文件字典 reason -> [paths])。"""
    ok = []
    problems = defaultdict(list)
    class_counts = Counter()
    total = 0

    for root, _, files in os.walk(data_dir):
        for name in sorted(files):
            ext = os.path.splitext(name)[1].lower()
            if ext not in IMAGE_EXTS:
                continue
            path = os.path.join(root, name)
            # 跳过隔离目录本身
            if "quarantine" in path.split(os.sep):
                continue

            total += 1
            rel = os.path.relpath(path, data_dir)
            cls = rel.split(os.sep)[0] if os.sep in rel else "(root)"
            class_counts[cls] += 1

            # 1) 有效性检查（verify 验证文件结构完整性）
            try:
                with Image.open(path) as img:
                    img.verify()
                with Image.open(path) as img:
                    w, h = img.size
            except (UnidentifiedImageError, OSError, ValueError):
                problems["corrupt"].append(path)
                continue

            # 2) 尺寸检查
            if min(w, h) < min_size:
                problems["too_small"].append(path)
                continue

            ok.append(path)

    # 3) 重复检查（只针对通过前两项的文件）
    hash_map = {}
    for path in ok:
        h = md5_of(path)
        if h in hash_map:
            problems["duplicate"].append(path)
        else:
            hash_map[h] = path

    stats = {
        "total": total,
        "ok": len(hash_map),
        "class_counts": class_counts,
    }
    return stats, problems


def main():
    parser = argparse.ArgumentParser(description="数据集清洗与分析")
    parser.add_argument("--data-dir", default="input", help="数据集根目录（默认 input）")
    parser.add_argument("--clean", action="store_true",
                        help="将问题文件移动到隔离目录（默认不移动，仅报告）")
    parser.add_argument("--quarantine-dir", default=None,
                        help="隔离目录（默认 data_dir/quarantine）")
    parser.add_argument("--min-size", type=int, default=32,
                        help="允许的最小边长，像素（默认 32）")
    parser.add_argument("--report", default="output/data_report.txt",
                        help="报告输出路径（默认 output/data_report.txt）")
    args = parser.parse_args()

    if not os.path.isdir(args.data_dir):
        sys.exit(f"数据集目录不存在: {args.data_dir}")

    print(f"开始扫描: {args.data_dir}")
    stats, problems = scan(args.data_dir, args.min_size)

    # ---- 控制台统计 ----
    print("\n===== 扫描统计 =====")
    print(f"图片总数: {stats['total']}")
    print(f"有效图片: {stats['ok']}")
    for reason in ("corrupt", "too_small", "duplicate"):
        print(f"{reason}: {len(problems.get(reason, []))}")

    print("\n===== 类别分布 =====")
    for cls, cnt in stats["class_counts"].most_common():
        print(f"  {cls}: {cnt}")

    # ---- 问题文件明细 ----
    for reason, paths in problems.items():
        if not paths:
            continue
        print(f"\n----- {reason} ({len(paths)}) -----")
        for p in paths[:20]:
            print(f"  {p}")
        if len(paths) > 20:
            print(f"  ... 共 {len(paths)} 个，详见报告")

    # ---- 清理 ----
    if args.clean:
        qdir = args.quarantine_dir or os.path.join(args.data_dir, "quarantine")
        moved = 0
        for reason, paths in problems.items():
            for p in paths:
                rel = os.path.relpath(p, args.data_dir)
                dst = os.path.join(qdir, reason, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(p, dst)
                moved += 1
        print(f"\n已移动 {moved} 个问题文件到: {qdir}")

    # ---- 报告落盘 ----
    report_path = args.report
    if report_path:
        os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"数据集目录: {args.data_dir}\n")
            f.write(f"扫描时间统计 - 图片总数: {stats['total']}, "
                    f"有效图片: {stats['ok']}\n")
            for reason in ("corrupt", "too_small", "duplicate"):
                f.write(f"{reason}: {len(problems.get(reason, []))}\n")
            f.write("\n类别分布:\n")
            for cls, cnt in stats["class_counts"].most_common():
                f.write(f"  {cls}: {cnt}\n")
            for reason, paths in problems.items():
                if paths:
                    f.write(f"\n{reason}:\n")
                    for p in paths:
                        f.write(f"  {p}\n")
        print(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    main()
