# output — 模型与结果输出目录

训练脚本 `debug.py` 运行后在此目录生成：

| 文件                 | 说明                                   |
|----------------------|----------------------------------------|
| `best_model.pth`     | 验证集准确率最高的 checkpoint          |
| `last_model.pth`     | 最后一个 epoch 的 checkpoint           |
| `training_log.txt`   | 训练日志                               |
| `data_report.txt`    | 数据清洗脚本 `data_analize.py` 的报告  |
