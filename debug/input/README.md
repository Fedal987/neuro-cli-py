# input — 数据集目录

按 `torchvision.datasets.ImageFolder` 格式组织：

```
input/
├── train/                 # 训练集（必选）
│   ├── class_1/           # 每个子目录为一个类别
│   │   ├── img_001.jpg
│   │   └── ...
│   └── class_2/
└── val/                   # 验证集（可选，缺省时训练脚本自动从训练集划分 10%）
    ├── class_1/
    └── class_2/
```

使用前建议先运行数据清洗脚本检查数据质量：

```bash
python data_analize.py            # 仅分析
python data_analize.py --clean    # 清理（问题文件移入 input/quarantine/）
```
