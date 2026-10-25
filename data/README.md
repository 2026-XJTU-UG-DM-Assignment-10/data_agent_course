# 正式数据目录

当前尚未下载或生成正式数据。`examples/` 中只有明确标记的微型联调样本，不能用于课程规模验收。

由 A 实现 `scripts/prepare_data.py`，按任务书从 UCI Adult 获取 `adult.data`，保留来源、许可、原始文件与构造记录：<https://archive.ics.uci.edu/dataset/2/adult>。

目标布局：

```text
raw/adult.data
reference/train_reference.csv
reference/test_reference.csv
dirty/train_dirty.csv
manifests/split_manifest.csv
manifests/injection_manifest.csv
manifests/preparation_summary.json
```

生成数据由 `.gitignore` 排除，仓库保存准备脚本、固定参数和目录标记。正式提交时仍需将原始数据、构造数据、处理后数据和获取/构造说明另外打包；运行输出位于 `outputs/<run_id>/`。
