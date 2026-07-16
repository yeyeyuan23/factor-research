# PB-ROE Factor Research

华泰证券2011年《PB-ROE策略》的规则复现与现代因子研究工程。项目包含历史沪深300还原、point-in-time财务数据、因子验证、walk-forward模型、风险约束组合、离线报告和最终审计。

研究结论见[`docs/final_research_report.md`](docs/final_research_report.md)。10阶段开发计划、验收状态和模型使用建议只在[`docs/project_plan.md`](docs/project_plan.md)维护，README不重复保存Commit计划。

## 当前工程状态

- 原研报主复现：`configs/paper.yaml`，2005–2011完整18期；
- 现代主实验：`configs/modern.yaml`，历史沪深300，2015–2022开发期，2023–2025滚动样本外；
- 冻结因子：开发期唯一通过全部门槛的1个月反转；冻结期IC转负；
- 预测模型：Elastic Net与唯一树模型LightGBM；
- 组合结论：两模型在2023–2025均未超过沪深300成分等权代理；
- 自动测试全套通过；最终审计：17项通过。

当前正式结果、限制和证据强弱以最终研究报告为准，不以README中的摘要替代研究结论。

## 环境安装

要求Python 3.11或更高版本。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[data,dev]'
```

macOS运行LightGBM前需要OpenMP：

```bash
brew install libomp
```

检查配置和CLI：

```bash
.venv/bin/python -m pb_roe config-check --config configs/modern.yaml
.venv/bin/python -m pb_roe --help
```

## 快速工程验证

```bash
./scripts/run_smoke.sh
```

Smoke使用`configs/smoke.yaml`中的确定性fixture，依次检查配置、数据审计、原文复现、现代评价、两个模型、组合优化、离线报告、最终审计、pytest和ruff。

Smoke只证明工程链路能够运行，其收益、IC和模型表现不能作为论文结论。

## 数据契约

正式运行需要一个canonical目录，其中包含：

```text
security_master.parquet
trading_calendar.parquet
universe_membership.parquet
prices.parquet
fundamentals.parquet
manifest.json
```

核心约束：

- 股票池使用每个信号日有效的历史沪深300成分，不用当前成分回填历史；
- 790只是研究窗口内历史成分并集，用于下载和还原，不是中证800；
- 财务记录必须满足`effective_date <= signal_date`；
- 现代ROE使用Eastmoney首次公告日`NOTICE_DATE`，数据审计检查公告滞后；
- 当前行业字段是静态快照，不进入正式历史标签或组合约束；
- 原始数据和canonical大文件保存在`data/processed/`，不提交Git；
- 任何覆盖率闸门失败时停止生成正式结论；

字段、主键、单位和PIT规则见[`docs/data_dictionary.md`](docs/data_dictionary.md)。

## 正式流水线

以下命令使用仓库当前的正式数据目录。数据未准备好时，先根据运行手册构建canonical数据，不要重复下载已经缓存的请求。

```bash
PY=.venv/bin/python
PAPER_DATA=data/processed/paper_full_incremental/canonical
MODERN_DATA=data/processed/modern_sample/canonical

$PY -m pb_roe data audit \
  --config configs/paper.yaml \
  --input-dir "$PAPER_DATA"

$PY -m pb_roe reproduce \
  --config configs/paper.yaml \
  --input-dir "$PAPER_DATA"

$PY -m pb_roe data audit \
  --config configs/modern.yaml \
  --input-dir "$MODERN_DATA"

$PY -m pb_roe evaluate \
  --config configs/modern.yaml \
  --input-dir "$MODERN_DATA"

$PY -m pb_roe validate-factors \
  --config configs/modern.yaml \
  --input-dir "$MODERN_DATA"

$PY -m pb_roe train \
  --config configs/modern.yaml \
  --factor-file results/runs/modern-pb-roe/model_factor_panel.parquet \
  --model elastic-net

$PY -m pb_roe train \
  --config configs/modern.yaml \
  --factor-file results/runs/modern-pb-roe/model_factor_panel.parquet \
  --model lightgbm

$PY -m pb_roe optimize \
  --config configs/modern.yaml \
  --input-dir "$MODERN_DATA" \
  --factor-file results/runs/modern-pb-roe/model_factor_panel.parquet \
  --prediction-file results/runs/modern-pb-roe/elastic-net_predictions.parquet

$PY -m pb_roe optimize \
  --config configs/modern.yaml \
  --input-dir "$MODERN_DATA" \
  --factor-file results/runs/modern-pb-roe/model_factor_panel.parquet \
  --prediction-file results/runs/modern-pb-roe/lightgbm_predictions.parquet

$PY -m pb_roe report \
  --config configs/modern.yaml \
  --run-dir results/runs/modern-pb-roe \
  --paper-run-dir results/runs/paper-reproduction

$PY -m pb_roe final-audit \
  --config configs/modern.yaml \
  --run-dir results/runs/modern-pb-roe \
  --paper-run-dir results/runs/paper-reproduction

$PY scripts/freeze_results.py
```

执行顺序不能交换：`validate-factors`先冻结因子，模型入口才允许训练；组合只能读取冻结预测；报告和审计只读取已有结果，不下载、训练或回测。

更详细的数据构建、绘图和冻结步骤见[`docs/runbook.md`](docs/runbook.md)。

## Python可视化

正式研究图全部由Matplotlib脚本从结果文件生成，不使用生成式图片：

```bash
.venv/bin/python scripts/plot_factor_ic.py --help
.venv/bin/python scripts/plot_all_factor_analysis.py --help
.venv/bin/python scripts/plot_modern_core_factors.py --help
.venv/bin/python scripts/plot_model_comparison.py --help
.venv/bin/python scripts/plot_signal_method_comparison.py --help
.venv/bin/python scripts/plot_portfolio_analysis.py --help
.venv/bin/python scripts/plot_paper_reproduction.py --help
.venv/bin/python scripts/plot_presentation_en.py --help
.venv/bin/python scripts/build_standalone_presentation.py --help
```

绘图脚本只读取冻结结果。输出图保存在`docs/results/figures/`。普通HTML保留相对图片便于开发；`build_standalone_presentation.py`把图片嵌入单个HTML，适合直接发送和离线打开。

## 测试与质量检查

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check --no-cache src tests scripts
```

最终审计检查：

- 正式原研报复现必须为2005–2011完整18期；
- 数据质量闸门；
- ROE首次公告滞后、规范输入manifest和配置指纹；
- Elastic Net和LightGBM训练、验证、预测的时间顺序，以及收益标签退出日在预测日前已经实现；
- 静态行业不进入正式历史目标或组合约束；
- 满仓、非负权重、3%单票上限和漂移后30%换手上限；
- Dashboard不依赖外部Plotly CDN；
- 2023–2025冻结样本外配置；
- 冻结结果文件SHA-256清单。

机器可读摘要见[`docs/results/final_audit_summary.json`](docs/results/final_audit_summary.json)。

## 目录结构

```text
factor-research/
├── configs/                 原研报、现代实验和smoke配置
├── data/                    本地原始、缓存和canonical数据
├── docs/                    计划书、研究报告、运行手册和提交结果
│   └── results/             可版本控制的汇总表与Matplotlib图
├── results/runs/            本地完整运行产物，不提交大文件
├── scripts/                 smoke、结果冻结和Matplotlib绘图脚本
├── src/pb_roe/
│   ├── data/                Provider、PIT拼接、存储和质量闸门
│   ├── reproduction/        原研报规则复现
│   ├── factors/             扩展因子验证与冻结
│   ├── evaluation/          IC、分组、成本和暴露
│   ├── models/              Elastic Net与LightGBM
│   ├── portfolio/           风险估计与CVXPY优化
│   ├── reporting/           离线Dashboard
│   └── validation/          最终审计
└── tests/                   单元、PIT、回测和回归测试
```

## 文档入口

- 项目计划与Commit阶段：[`docs/project_plan.md`](docs/project_plan.md)
- 最终研究报告：[`docs/final_research_report.md`](docs/final_research_report.md)
- 原研报固定笔记：[`docs/paper_notes.md`](docs/paper_notes.md)
- 研究口径：[`docs/research_spec.md`](docs/research_spec.md)
- 数据字典：[`docs/data_dictionary.md`](docs/data_dictionary.md)
- 运行手册：[`docs/runbook.md`](docs/runbook.md)
- 12因子分析：[`docs/factor_analysis_report.md`](docs/factor_analysis_report.md)
- 模型与组合分析：[`docs/portfolio_analysis_report.md`](docs/portfolio_analysis_report.md)
- 英文10分钟HTML展示：[`docs/presentation_en_10min.html`](docs/presentation_en_10min.html)
- 可直接发送的单文件HTML：[`docs/presentation_en_10min_standalone.html`](docs/presentation_en_10min_standalone.html)
- 英文10分钟逐页讲稿：[`docs/presentation_script_en_10min.md`](docs/presentation_script_en_10min.md)
- 工程代码走读：[`docs/code_walkthrough.md`](docs/code_walkthrough.md)

## 已知限制

- 原研报复现使用免费源，不能称为Wind字段逐值复刻；
- 2005–2006早期ROE按统一披露截止日生效，不是逐公司精确公告时点；
- 免费财务接口不能保证保留每次历史修订快照；
- BaoStock行业字段是当前静态快照，因此正式现代层未做历史行业约束；
- 缺少可靠历史沪深300真实权重和历史总市值，现代基准使用成分等权代理；
- 组合缺失下一月收益当前按0计，尚未实现完整退市/长期停牌持仓账本；
- 当前正式冻结结果未跑赢基准，不能宣称获得可持续Alpha。
