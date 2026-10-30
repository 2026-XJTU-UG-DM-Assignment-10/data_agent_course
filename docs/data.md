# 正式数据说明（2026-10-30 集成补齐）

A 分支的交接清单声明了本文件，但实际上传遗漏。以下由集成人根据 A 的准备脚本和本次真实重建结果补齐；没有恢复或冒充原始缺失文档，也没有改写原交付摘要。

- 来源：UCI Adult，下载 https://archive.ics.uci.edu/static/public/2/adult.zip；来源页 https://archive.ics.uci.edu/dataset/2/adult；许可及引用见准备摘要。
- 命令：`python scripts/prepare_data.py --seed 42 --sample-size 10000`。
- 真实原始记录 32,561 条；抽样 10,000 条；按 14 个特征的稳定签名分组，训练 7,000 条、测试 3,000 条，来源组交叉为 0。
- 只在训练集加入问题：缺失 4,857 个单元格、格式问题 1,198 个单元格、异常 70 行、复制 140 行；待清洗训练集 7,140 行。各类问题可重叠，不能直接相加当作问题行数。
- 原始数据 SHA-256：`5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d`。
- 参考数据保留原生缺失，测试集不额外注入问题。填补、编码及标准化参数只从训练集学习；标签及两个来源 ID 不作特征。
- `data/manifests/` 仅供数据构造审计，不传给检测器、大模型或分类器。完整数据路径见 `data/README.md`。
- 本次 `python checks/check_A.py --integration` 通过 54 项检查。完整输出在 `outputs/member_A/`；本地正式数据、原始文件及运行记录需要另行打包，不能仅依赖 GitHub 源码。
