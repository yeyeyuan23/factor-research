# PB-ROE Factor Research

复现华泰证券 2011 年《PB-ROE 策略》，并在严格 point-in-time 数据、现代因子评价、交易成本与样本外框架下检验其有效性。

## 项目计划与真实状态

本项目的开发计划**只有以下 10 个 Commit**，与项目计划书“十四、分步开发与提交原则”一致。下表区分“工程实现”与“正式研究结果”：通过 smoke fixture 只说明代码链路可运行，不能视为正式研究完成。

| 计划 Commit | 计划交付 | 对应首个 Git 提交 | 当前状态 |
|---|---|---|---|
| 01 | 研究规格、数据字典、覆盖率审计与停止条件 | `bb59ab8` | 已完成 |
| 02 | 配置、CLI、日志、目录与测试框架 | `c743421` | 已完成 |
| 03 | PIT 数据管线、质量闸门与 Parquet 缓存 | `e104f5f` | 已完成；复现闸门 15/15、现代闸门 16/16 通过，现代因子有效起点为 2012-05-31 |
| 04 | 原研报组合、成本口径与结果对照 | `25dc6dd` | 已完成；2005–2011 全窗口规则复现，早期ROE披露截止假设已披露 |
| 05 | IC、分层、成本、显著性与暴露评价 | `1e3407c` | 已完成；市值暴露因可靠历史总市值缺失而降级披露 |
| 06 | 扩展因子与 Elastic Net 线性基准 | `f5fe62f` | 已完成；12因子正式walk-forward及冻结样本外预测已运行 |
| 07 | LightGBM 滚动训练与样本外预测 | `648dde5` | 已完成；正式walk-forward及冻结样本外预测已运行 |
| 08 | 风险估计、CVXPY 约束与失败回退 | `9f37564` | 已完成；两模型正式组合、成本敏感性及冻结样本外比较已运行 |
| 09 | 离线 Dashboard 与静态备份 | `4e26435` | 已完成；正式离线 Dashboard 与4张矢量结果图已生成并验收 |
| 10 | 泄漏检查、结果冻结、结论审阅与演示彩排 | `271541d` | smoke 审计完成；正式全量审计与结论冻结尚未完成 |

除上述 10 项外，不存在其他计划 Commit 编号。后续只会更新本表的状态，不会新建 C11、C12 等计划编号；任何额外 Git 提交仅是对既有 01–10 项的修复或补充，不改变项目计划。

完整项目计划以 [`docs/project_plan.md`](docs/project_plan.md) 为唯一正式版本；原研报的固定方法与结果笔记见 [`docs/paper_notes.md`](docs/paper_notes.md)，研究口径见 [`docs/research_spec.md`](docs/research_spec.md)，字段约定见 [`docs/data_dictionary.md`](docs/data_dictionary.md)。后续优先查固定笔记，仅在笔记未覆盖或需要逐字核验时重新读取原 PDF。

Commit 03 的现代全量数据实际覆盖 2010–2025 年逐月历史沪深 300：192 个信号日均为 300 只，历年成分股并集为 790 只（仅用于下载和历史还原），行情 2,746,038 行，财务指标 3,176,887 行。PB 月度覆盖率为 100%；ROE 从 2012-05-31 起连续高于 80% 闸门，因此 2010-01 至 2012-04 仅作数据积累，不进入现代因子结论。AKShare/Eastmoney 批量财务接口提供最新公告日期，历史修订值仅从该日期起生效；这是保守 PIT 处理，不用未来修订回填过去。9 条绝对日收益超过 50% 的记录均已进入异常清单，主要对应长期停牌后复牌、重整或退市阶段。

## 原研报全窗口复现结论（Commit 04）

完整对照见 [`docs/results/paper_reproduction_full.csv`](docs/results/paper_reproduction_full.csv)。2005首批沪深300名单及2005-07-01调整名单来自公开历史公告，2006年以后使用BaoStock历史快照；2005–2006 ROE仅请求新浪对应年份页面，并按原研报“一季报/半年报/三季报披露完成日”分别在4/30、8/31、10/31生效。披露完成日非交易时顺延到下一交易日成交。该方法复现原研报规则，但不能称为Wind字段的逐值数值复刻。

- 全窗口18期均为当期300只历史成分股；数据闸门16/16通过，PB最低覆盖99.67%，ROE最低覆盖99.0%。
- PB-ROE Top50累计毛收益468.93%、累计净收益352.72%、成本后年化29.31%，18期中12期跑赢等权股票池；原研报相应为累计净收益488.20%、成本后年化35.00%、13期跑赢。
- 加入2005–2006后，旧版约5.6%的年化结果大幅上升，确认缺失早期牛市是此前未复现的主要原因。
- 价值质量综合排序的方向和收益量级得到复现，但原研报最优的行业等权版本在本项目中成本后年化为27.78%，低于PB-ROE Top50和等权股票池，行业版本“最优”的结论未复现。

## 当前现代因子证据（Commit 05，尚未最终冻结）

当前可提交摘要见 [`docs/results/modern_factor_baseline.csv`](docs/results/modern_factor_baseline.csv)，分段稳定性见 [`docs/results/modern_factor_segments.csv`](docs/results/modern_factor_segments.csv)。结果使用 2012-05-31 至 2025-10-31 的 162 个月、48,560 个可交易截面观测，配置指纹为 `6799e05ac4e93d9c`。这里的行业调整是截面去除行业均值后的现代检验，不等同于原研报每行业前 5 的组合。

- BP 的 Rank IC 均值为 4.56%，Newey-West t 值为 2.50；行业调整后分别为 3.13% 和 2.83，说明价值信号不完全由行业差异解释。
- ROE TTM 的 Rank IC 均值仅为 0.50%，t 值为 0.43，当前数据不支持其作为独立现代选股信号。
- PB-ROE 综合得分的 Rank IC 均值为 3.91%，t 值为 3.10；行业调整后为 3.03% 和 3.69，但 30bp 换手成本后的多空年化仅为 2.28%。
- 30bp 成本下，行业调整 BP 的多空年化为 3.41%、Sharpe 为 0.27、最大回撤为 -37.63%；统计有效不等于具有足够经济收益。
- 2024–2025 年度 IC 明显弱于 2023 年，现代样本外稳定性仍不足。目前只能得出“BP 有一定预测能力、ROE 单因子无效、PB-ROE 统计显著但成本后偏弱”的阶段性结论。

月度明细保存在本地 `results/runs/modern-pb-roe/`，该目录不提交 Git；Commit 10 将冻结最终结果、配置与哈希。当前成交规则会识别一字涨跌停，并在计划成交失败后最多等待 5 个交易日：162 个月中共识别 153 个计划入场日锁板观测，入场/退出分别有 287/286 个观测发生延迟，最终收益标签平均覆盖率为 97.64%、最低为 87.63%。Top 组按 10% ADV 参与率、完全换仓估算的中位容量约为 3.2–4.0 亿元，仅用于量级检查。历史总市值字段仍缺失，市值暴露不能可靠计算；按照计划书的数据停止条件，该项降级为限制披露，不使用指数权重冒充市值。

## 扩展因子与 Elastic Net（Commit 06）

扩展因子单项结果见 [`docs/results/expanded_factor_ic.csv`](docs/results/expanded_factor_ic.csv)，Elastic Net分段结果见 [`docs/results/elastic_net_summary.csv`](docs/results/elastic_net_summary.csv)。12个因子均满足逐月最低80%覆盖门槛；训练每月只使用过去最多60个月，前24个月仅积累训练数据，固定参数且不做网格搜索。配置指纹为`00cb56dba97f011e`。

- 单因子中，低特异波动（IC方向为负，绝对值5.97%）、低总波动（-5.45%）、低Beta（-4.27%）、BP（3.57%）、PB-ROE（3.51%）、12-1动量（3.25%）和1月反转（2.40%）具有显著预测信息。
- ROE TTM、毛利率、营收增长和盈利增长的独立IC较弱；它们是否提供条件性增量由Elastic Net系数和样本外预测共同判断。
- Elastic Net整体138个月Rank IC为5.54%，正IC比例67.39%；2015–2022开发期IC为5.28%，2023–2025冻结样本外IC为6.06%、Newey-West t值2.90。
- 线性模型的主要稳定贡献来自12-1动量、低特异波动、1月反转、BP和毛利率。冻结样本外IC高于行业调整PB-ROE的2.62%，说明扩展因子提供了统计增量；成本后组合增量仍需在Commit 08验证。

## LightGBM 非线性检验（Commit 07）

与Elastic Net的可提交对照见 [`docs/results/lightgbm_summary.csv`](docs/results/lightgbm_summary.csv)。LightGBM沿用同一12因子、60个月滚动窗口和最后12个月时序验证集，固定超参数并使用early stopping；未增加第二个树模型。

- LightGBM整体138个月Rank IC为4.28%，低于Elastic Net的5.54%；开发期IC为3.53%，同样低于Elastic Net的5.28%。
- 2023–2025冻结样本外IC为6.23%，仅略高于Elastic Net的6.06%，两者正IC月份比例同为67.65%左右。
- 主要增益重要性依次来自1月反转、12-1动量、60日波动率、特异波动率和毛利率；ROE与PB-ROE综合得分的重要性靠后。
- 当前证据不支持“LightGBM显著优于线性模型”。只有Commit 08证明其成本后组合表现也改善，才能认为非线性提供有效增量。

## 组合优化与模型可交易性（Commit 08）

正式对照见 [`docs/results/portfolio_model_comparison.csv`](docs/results/portfolio_model_comparison.csv)。两种模型均使用Ledoit-Wolf协方差、3%单票上限、行业偏离不超过5%、单月换手不超过30%和相同风险/换手惩罚；138个月全部求解成功，fallback均为0。因免费源没有历史沪深300真实权重，行业基准使用当期成员等权代理并明确披露。

- 2023–2025冻结样本外，等权基准年化5.62%；30bp成本后Elastic Net年化8.64%、LightGBM年化9.39%，对应最大回撤分别为-13.48%和-13.15%。
- 50bp成本下两模型冻结样本外仍分别年化8.26%和9.00%，说明该阶段增量未被简化交易成本完全吞噬。
- LightGBM在冻结期比Elastic Net年化高约0.75个百分点，同时IC略高；但2015–2022开发期两者成本后年化均约-1.7%，全样本也均落后等权基准。
- 冻结期超额收益主要来自2023年；2024和2025两种模型平均月度超额均为负，绝对超额最大的5个月约占总绝对波动38%。因此LightGBM不满足“增量不是由少数时期驱动”的有效条件，最终结论仍是非线性没有提供稳健优势。

## 正式结果展示（Commit 09）

离线 Dashboard 从本地冻结结果生成在 `results/runs/modern-pb-roe/dashboard.html`，不重新运行下载、训练或回测。Git 中保存以下轻量矢量备份，可直接用于论文和展示：

- [原研报复现累计净值](docs/results/figures/paper-reproduction.svg)
- [扩展因子 Rank IC](docs/results/figures/expanded-factor-ic.svg)
- [Elastic Net 与 LightGBM 分段 IC](docs/results/figures/model-ic-comparison.svg)
- [约束组合成本后累计净值](docs/results/figures/portfolio-net-value.svg)

所有图片均由正式 `paper-reproduction` 和 `modern-pb-roe` 结果生成，不包含 smoke fixture 数据。Dashboard 与静态图的生成命令记录在 [`docs/runbook.md`](docs/runbook.md)。

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
- 原研报复现与现代改进的主股票池统一为历史沪深 300（`CSI300`）；中证 800 不进入正式主实验；
- 原始数据不可覆盖，派生数据必须记录来源和生成配置；
- 财务数据必须满足 `effective_date <= signal_date`；
- 先运行 smoke 数据，再运行 full 数据；
- 2023-2025 为冻结样本外区间，不用于选因子或调参。
