# 运行手册

## 1. 环境

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
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
- Elastic Net 与 LightGBM 均产生严格 walk-forward 预测；
- 组合优化产生约束持仓、净收益和求解诊断；
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

随后执行：

```bash
.venv/bin/python -m pb_roe data audit --config configs/paper.yaml --input-dir <canonical-data>
.venv/bin/python -m pb_roe reproduce --config configs/paper.yaml --input-dir <canonical-data>
.venv/bin/python -m pb_roe evaluate --config configs/modern.yaml --input-dir data/processed/modern_sample/canonical
.venv/bin/python -m pb_roe validate-factors --config configs/modern.yaml --input-dir data/processed/modern_sample/canonical
MPLCONFIGDIR=/private/tmp/mpl .venv/bin/python scripts/plot_factor_ic.py --run-dir results/runs/modern-pb-roe --output docs/results/figures/equal-weight-ic-matplotlib.png
.venv/bin/python -m pb_roe train --config configs/modern.yaml --input-dir data/processed/modern_sample/canonical --model elastic-net
.venv/bin/python -m pb_roe optimize --config configs/modern.yaml --input-dir data/processed/modern_sample/canonical --factor-file results/runs/modern-pb-roe/model_factor_panel.parquet --prediction-file results/runs/modern-pb-roe/elastic-net_predictions.parquet
.venv/bin/python -m pb_roe report --config configs/modern.yaml --run-dir results/runs/modern-pb-roe --paper-run-dir results/runs/paper-reproduction --static-dir docs/results/figures
```

当前真实数据适配层提供 BaoStock 行情与沪深 300 快照读取能力；财务公告时点、历史成分区间重建和正式全量下载仍需先落为 canonical Parquet。任何一项覆盖率未达到配置阈值时，不得生成论文结论。

`configs/paper.yaml` 现用于2005–2011全窗口规则复现：2005历史成分由首批名单和7月调整公告重建，2006年以后使用BaoStock历史快照；早期ROE只请求新浪2005、2006年度页，并按原研报固定披露完成日生效。`configs/paper_free.yaml` 保留为旧的2007–2011对照配置，不再作为主复现结果。

构建免费数据：

```bash
.venv/bin/python -m pb_roe data ingest \
  --config configs/paper_free.yaml \
  --output-dir data/processed/paper_free
```

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
