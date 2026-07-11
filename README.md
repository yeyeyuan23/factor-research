# PB-ROE Factor Research

复现华泰证券 2011 年《PB-ROE 策略》，并在严格 point-in-time 数据、现代因子评价、交易成本与样本外框架下检验其有效性。

当前开发范围为项目计划的 Commit 01-05：

1. 研究规格与数据审计；
2. 工程脚手架与 CLI；
3. PIT 数据管线与质量闸门；
4. 原研报策略复现；
5. 现代因子评价体系。

完整研究口径见 [`docs/research_spec.md`](docs/research_spec.md)，字段约定见 [`docs/data_dictionary.md`](docs/data_dictionary.md)。

## 安装

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

macOS 上 LightGBM 还需要 OpenMP：

```bash
brew install libomp
```

## 一键 smoke 验证

```bash
./scripts/run_smoke.sh
```

该命令依次执行配置检查、数据审计、原文复现、现代评价、Elastic Net、LightGBM、组合优化、离线报告和最终审计。

> `configs/smoke.yaml` 使用确定性 fixture，只验证工程逻辑，fixture 的收益、IC 和模型表现严禁作为论文结论。正式研究必须使用通过质量闸门的历史沪深 300、行情和公告时点财务数据。

## 开发原则

- 原研报复现与现代改进使用不同配置和实验编号；
- 原始数据不可覆盖，派生数据必须记录来源和生成配置；
- 财务数据必须满足 `effective_date <= signal_date`；
- 先运行 smoke 数据，再运行 full 数据；
- 2023-2025 为冻结样本外区间，不用于选因子或调参。
