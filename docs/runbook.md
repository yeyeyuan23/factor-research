# 运行手册

## 1. 环境

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[data,dev]'
```

macOS 使用 LightGBM 前执行：

```bash
brew install libomp
```

## 2. Smoke 全链路

```bash
./scripts/run_smoke.sh
```

预期结果：

- 数据质量闸门通过；
- 原文复现产生持仓、每期收益与汇总；
- 现代评价产生 IC、分层、多空、成本和暴露；
- 因子验证同时产生严格单因子名单和模型输入资格manifest；
- Elastic Net 与 LightGBM 均产生严格 walk-forward 预测；
- 严格反转、合格因子等权、Elastic Net和LightGBM都产生约束持仓、净收益和求解诊断；
- `dashboard.html` 可断网打开；
- `final_audit.json` 的 `passed` 为 `true`。

## 3. 正式数据运行前置条件

正式结果不能使用 fixture。必须先生成满足 `docs/data_dictionary.md` 的五张 Parquet 表：

```text
security_master.parquet
trading_calendar.parquet
universe_membership.parquet
prices.parquet
fundamentals.parquet
```

当前正式数据目录：

```text
原研报：data/processed/paper_full_incremental/canonical
现代层：data/processed/modern_sample/canonical
```

随后严格按顺序执行：

```bash
PY=.venv/bin/python
PAPER_DATA=data/processed/paper_full_incremental/canonical
MODERN_DATA=data/processed/modern_sample/canonical

$PY -m pb_roe data audit --config configs/paper.yaml --input-dir "$PAPER_DATA"
$PY -m pb_roe reproduce --config configs/paper.yaml --input-dir "$PAPER_DATA"
$PY -m pb_roe data audit --config configs/modern.yaml --input-dir "$MODERN_DATA"
$PY -m pb_roe evaluate --config configs/modern.yaml --input-dir "$MODERN_DATA"
$PY -m pb_roe validate-factors --config configs/modern.yaml --input-dir "$MODERN_DATA"

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
  --prediction-file results/runs/modern-pb-roe/pb_roe_baseline_predictions.parquet

$PY -m pb_roe optimize \
  --config configs/modern.yaml \
  --input-dir "$MODERN_DATA" \
  --factor-file results/runs/modern-pb-roe/model_factor_panel.parquet \
  --prediction-file results/runs/modern-pb-roe/strict_factor_equal_weight_predictions.parquet

$PY -m pb_roe optimize \
  --config configs/modern.yaml \
  --input-dir "$MODERN_DATA" \
  --factor-file results/runs/modern-pb-roe/model_factor_panel.parquet \
  --prediction-file results/runs/modern-pb-roe/model_input_equal_weight_predictions.parquet

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

`validate-factors`必须先生成严格名单`frozen_factor_selection.json`、PB-ROE增量表`factor_incremental_analysis.csv`、资格表`model_factor_eligibility.csv`、输入清单`model_feature_manifest.json`和`model_factor_panel.parquet`。两个模型读取同一8因子manifest和同一面板。严格名单回答“能否独立交易”，增量表回答“是否改善PB-ROE”，manifest回答“能否作为多因子模型输入”，三者不能混用。`freeze_results.py`只在最终审计通过后执行，把机器结果复制为可版本控制摘要。报告、冻结和绘图命令不下载、训练或回测。

正式图表在相应研究阶段完成后生成：

```bash
MPLCONFIGDIR=/private/tmp/mpl $PY scripts/plot_factor_ic.py --run-dir results/runs/modern-pb-roe --output docs/results/figures/equal-weight-ic-matplotlib.png --quantile-output docs/results/figures/equal-weight-quantiles-30bp.png
MPLCONFIGDIR=/private/tmp/mpl $PY scripts/plot_all_factor_analysis.py --run-dir results/runs/modern-pb-roe --output-dir docs/results/figures/factor-analysis-12
MPLCONFIGDIR=/private/tmp/mpl $PY scripts/plot_modern_core_factors.py --run-dir results/runs/modern-pb-roe --ic-output docs/results/figures/modern-core-factor-ic.png --quantile-output docs/results/figures/modern-core-factor-quantiles.png
MPLCONFIGDIR=/private/tmp/mpl $PY scripts/plot_model_comparison.py --run-dir results/runs/modern-pb-roe --segment-output docs/results/figures/model-ic-segment-comparison.png --timeseries-output docs/results/figures/model-ic-timeseries.png
MPLCONFIGDIR=/private/tmp/mpl $PY scripts/plot_factor_incremental.py --input docs/results/factor_incremental_analysis.csv --output docs/results/figures/factor-incremental-analysis.png
MPLCONFIGDIR=/private/tmp/mpl $PY scripts/plot_signal_method_comparison.py --run-dir results/runs/modern-pb-roe --output docs/results/figures/signal-method-ic-comparison.png
MPLCONFIGDIR=/private/tmp/mpl $PY scripts/plot_portfolio_analysis.py --run-dir results/runs/modern-pb-roe --performance-output docs/results/figures/portfolio-performance.png --segment-output docs/results/figures/portfolio-segment-metrics.png --yearly-output docs/results/figures/portfolio-oos-yearly.png
MPLCONFIGDIR=/private/tmp/mpl $PY scripts/plot_presentation_en.py --results-dir docs/results --output-dir docs/results/figures/presentation-en
$PY scripts/build_standalone_presentation.py --input docs/presentation_en_10min.html --output docs/presentation_en_10min_standalone.html
```

绘图脚本全部使用Matplotlib并只读取结果文件。最后一条命令把主展示图和按需展开的因子明细图编码进HTML；生成的`presentation_en_10min_standalone.html`不依赖同目录图片，可以作为单个文件直接发送。不要向`report`命令传`--static-dir`重新生成旧的手写SVG备份。

当前真实数据适配层使用BaoStock行情与沪深300历史快照，并直接保存Eastmoney季度业绩接口的首次公告日`NOTICE_DATE`和后续`UPDATE_DATE`。数据审计要求ROE公告滞后中位数不超过200天；任何覆盖或时点门槛失败时不得生成论文结论。

`configs/paper.yaml` 用于2005–2011全窗口规则复现：2005历史成分由首批名单和7月调整公告重建，2006年以后使用BaoStock历史快照；早期ROE只请求新浪2005、2006年度页，并按原研报固定披露完成日生效。旧的2007–2011截断配置和运行目录已经删除，不能再作为正式入口。

BaoStock 登录会话不支持多进程并发，`download_workers` 必须为 1。下载器按股票和季度缓存，接口中断后重复同一命令即可续跑；不要通过并发绕过这一限制。

## 4. 结果冻结

正式运行结束后依次生成模型、优化和报告，再执行：

```bash
.venv/bin/python -m pb_roe final-audit --config configs/modern.yaml --run-dir results/runs/modern-pb-roe --paper-run-dir results/runs/paper-reproduction
```

归档以下内容：

- 使用的配置文件；
- canonical 数据 manifest；
- `final_audit.json`；
- `result_manifest.json`；
- `dashboard.html`；
- 对应 Git commit。
