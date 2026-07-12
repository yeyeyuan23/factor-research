# PB-ROE Factor Research

复现华泰证券 2011 年《PB-ROE 策略》，并在严格 point-in-time 数据、现代因子评价、交易成本与样本外框架下检验其有效性。

## 项目计划与真实状态

本项目的开发计划**只有以下 10 个 Commit**，与项目计划书“十四、分步开发与提交原则”一致。下表区分“工程实现”与“正式研究结果”：通过 smoke fixture 只说明代码链路可运行，不能视为正式研究完成。

| 计划 Commit | 计划交付 | 对应首个 Git 提交 | 当前状态 |
|---|---|---|---|
| 01 | 冻结研究问题、原文/现代两层口径、数据字典、覆盖率闸门与停止条件 | `bb59ab8` | 已完成 |
| 02 | 建立配置、CLI、日志、目录、smoke fixture 与测试框架；smoke 只验工程链路 | `c743421` | 已完成 |
| 03 | 构建历史沪深300、行情和财务PIT数据管线，执行质量闸门并缓存 canonical Parquet | `e104f5f` | 已完成；复现闸门15/15、现代闸门16/16通过，现代因子有效起点为2012-05-31 |
| 04 | 严格按原文构造2005–2011组合，统一成本口径并逐项对照原研报结果 | `25dc6dd` | 已完成；早期ROE披露截止假设已披露 |
| 05 | 仅评价原研报核心信号BP、ROE、PB-ROE：IC、分层、成本、显著性、稳定性与暴露 | `1e3407c` | 已重新完成；48,560个观测、162个月，正式汇总已补齐；市值暴露降级披露 |
| 06 | 按5类Barra-style框架构建扩展因子；只在2015–2022开发期完成单因子验证、筛选、冻结和等权多因子基准 | `f5fe62f` | **已重新完成**；12个候选验证、6个因子冻结，等权基准及三档成本已生成 |
| 07 | 仅使用Commit 06冻结的因子，按相同walk-forward口径训练Elastic Net和唯一树模型LightGBM | `648dde5` | **待重跑**；现有结果使用了仅通过覆盖率闸门的全部12列，保留为初版实验，不作为最终结论 |
| 08 | 使用Commit 07冻结预测做Ledoit-Wolf风险估计、CVXPY约束组合、失败回退及10/30/50bp成本检验 | `9f37564` | **待重跑**；工程与初版结果存在，须随冻结因子模型更新 |
| 09 | 只读取重跑后的冻结结果生成离线Dashboard和静态备份，不下载、训练或回测 | `4e26435` | **待更新**；现有Dashboard和4张图对应初版模型结果 |
| 10 | 对最终流水线做泄漏检查、结果与哈希冻结、结论审阅和10分钟演示彩排 | `271541d` | **待重新验收**；旧审计仅证明初版流水线内部一致，不能替代修正后的最终审计 |

除上述 10 项外，不存在其他计划 Commit 编号。后续只会更新本表的状态，不会新建 C11、C12 等计划编号；任何额外 Git 提交仅是对既有 01–10 项的修复或补充，不改变项目计划。

### Commit 06 的明确验收条件

这里的“5类Barra-style因子”指 **Value、Quality、Growth、Momentum、Risk & Trading** 五类，不是强制只选5个具体因子，也不宣称复刻完整Barra风险模型。每类可以有多个候选变量，但入模前必须满足以下流程：

1. 先检查PIT口径、逐月覆盖率和异常值，不用未来修订值回填历史；
2. 因子筛选只使用2015–2022开发期，2023–2025冻结样本外不得参与筛选；
3. 对每个候选因子报告Rank IC、ICIR、正IC比例、Newey-West t值和年度稳定性；
4. 报告五分组收益、分层单调性、Top–Bottom spread及10/30/50bp成本敏感性；
5. 检查行业暴露、可获得的规模暴露、因子相关性和容量；缺失的历史市值必须降级披露；
6. 预先写明筛选规则和方向，冻结最终入模名单，不得仅因覆盖率合格就全部入模；
7. 在机器学习之前建立“原始PB-ROE → 扩展因子等权组合”的非机器学习增量基准；
8. 将候选、淘汰、保留及原因保存为可版本控制的小型结果表，README链接全部正式输出。

只有Commit 06通过以上验收，Commit 07–10才可依次恢复为“已完成”。现有12因子模型、组合和图表仍可用于工程回归检查，但统一标为**初版实验结果**，不能作为论文最终结果。

### Commit 06 因子验证结论

正式候选与淘汰原因见 [`docs/results/factor_validation_summary.csv`](docs/results/factor_validation_summary.csv)，冻结名单见 [`docs/results/frozen_factor_selection.json`](docs/results/frozen_factor_selection.json)，方向调整后的等权基准见 [`docs/results/equal_weight_factor_baseline.csv`](docs/results/equal_weight_factor_baseline.csv)，入选因子相关矩阵见 [`docs/results/selected_factor_correlations.csv`](docs/results/selected_factor_correlations.csv)。筛选只使用2015–2022开发期；冻结期指标是在名单确定后追加报告，不参与`selected`判断。

- 12个候选覆盖Value、Quality、Growth、Momentum、Risk & Trading五类；最终保留BP、PB-ROE、12–1动量、1月反转、低Beta和低特异波动6个因子。
- 营收增长、盈利增长和毛利率因开发期IC及t值不足淘汰；ROE因分层不单调且30bp成本后多空为负淘汰；流动性因IC、单调性和成本均不合格淘汰；总波动率虽IC显著，但分层单调性和成本后收益未过线。
- 入选因子开发期等权得分IC为6.53%、Newey-West t值6.40；30bp成本后多空年化5.31%、Sharpe 0.70、最大回撤-16.41%。
- 冻结期等权得分IC为8.65%，但30bp成本后多空年化仅1.62%，50bp仅0.05%，说明预测显著性没有完全转化为交易收益。
- 候选因子平均绝对行业主动权重约1.7%–2.4%，入选因子相关性绝对值最高约0.59；历史总市值缺失，规模暴露继续按停止条件降级披露，不以指数权重替代。

展示用基础IC图见 [`docs/results/figures/equal-weight-ic-matplotlib.png`](docs/results/figures/equal-weight-ic-matplotlib.png)：蓝/红柱表示正/负Rank IC，橙色虚线为IC均值，黑线为累计IC，竖向虚线标出2023年冻结样本外起点。

完整项目计划以 [`docs/project_plan.md`](docs/project_plan.md) 为唯一正式版本；原研报的固定方法与结果笔记见 [`docs/paper_notes.md`](docs/paper_notes.md)，研究口径见 [`docs/research_spec.md`](docs/research_spec.md)，字段约定见 [`docs/data_dictionary.md`](docs/data_dictionary.md)。后续优先查固定笔记，仅在笔记未覆盖或需要逐字核验时重新读取原 PDF。

Commit 03 的现代全量数据实际覆盖 2010–2025 年逐月历史沪深 300：192 个信号日均为 300 只，历年成分股并集为 790 只（仅用于下载和历史还原），行情 2,746,038 行，财务指标 3,176,887 行。PB 月度覆盖率为 100%；ROE 从 2012-05-31 起连续高于 80% 闸门，因此 2010-01 至 2012-04 仅作数据积累，不进入现代因子结论。AKShare/Eastmoney 批量财务接口提供最新公告日期，历史修订值仅从该日期起生效；这是保守 PIT 处理，不用未来修订回填过去。9 条绝对日收益超过 50% 的记录均已进入异常清单，主要对应长期停牌后复牌、重整或退市阶段。

## 原研报全窗口复现结论（Commit 04）

完整对照见 [`docs/results/paper_reproduction_full.csv`](docs/results/paper_reproduction_full.csv)。2005首批沪深300名单及2005-07-01调整名单来自公开历史公告，2006年以后使用BaoStock历史快照；2005–2006 ROE仅请求新浪对应年份页面，并按原研报“一季报/半年报/三季报披露完成日”分别在4/30、8/31、10/31生效。披露完成日非交易时顺延到下一交易日成交。该方法复现原研报规则，但不能称为Wind字段的逐值数值复刻。

- 全窗口18期均为当期300只历史成分股；数据闸门16/16通过，PB最低覆盖99.67%，ROE最低覆盖99.0%。
- PB-ROE Top50累计毛收益468.93%、累计净收益352.72%、成本后年化29.31%，18期中12期跑赢等权股票池；原研报相应为累计净收益488.20%、成本后年化35.00%、13期跑赢。
- 加入2005–2006后，旧版约5.6%的年化结果大幅上升，确认缺失早期牛市是此前未复现的主要原因。
- 价值质量综合排序的方向和收益量级得到复现，但原研报最优的行业等权版本在本项目中成本后年化为27.78%，低于PB-ROE Top50和等权股票池，行业版本“最优”的结论未复现。

## 原研报核心信号的现代证据（Commit 05，已完成）

完整小型汇总见 [`docs/results/core_factor_validation.csv`](docs/results/core_factor_validation.csv)，原有摘要见 [`docs/results/modern_factor_baseline.csv`](docs/results/modern_factor_baseline.csv)，分段稳定性见 [`docs/results/modern_factor_segments.csv`](docs/results/modern_factor_segments.csv)。结果使用2012-05-31至2025-10-31的162个月、48,560个可交易截面观测；新汇总同时列出全样本、2015–2022开发期、2023–2025冻结期IC，五分组30bp成本后月均收益、单调性和10/30/50bp多空年化。这里的行业调整是截面去除行业均值后的现代检验，不等同于原研报每行业前5的组合。Commit 05只评价既定核心信号，不据此选择Commit 06扩展因子。

- BP 的 Rank IC 均值为 4.56%，Newey-West t 值为 2.50；行业调整后分别为 3.13% 和 2.83，说明价值信号不完全由行业差异解释。
- ROE TTM 的 Rank IC 均值仅为 0.50%，t 值为 0.43，当前数据不支持其作为独立现代选股信号。
- PB-ROE 综合得分的 Rank IC 均值为 3.91%，t 值为 3.10；行业调整后为 3.03% 和 3.69，但 30bp 换手成本后的多空年化仅为 2.28%。
- 30bp 成本下，行业调整 BP 的多空年化为 3.41%、Sharpe 为 0.27、最大回撤为 -37.63%；统计有效不等于具有足够经济收益。
- 2024–2025 年度 IC 明显弱于 2023 年，现代样本外稳定性仍不足。目前只能得出“BP 有一定预测能力、ROE 单因子无效、PB-ROE 统计显著但成本后偏弱”的阶段性结论。

月度明细保存在本地 `results/runs/modern-pb-roe/`，该目录不提交 Git；修正后的Commit 10将重新冻结最终结果、配置与哈希。当前成交规则会识别一字涨跌停，并在计划成交失败后最多等待 5 个交易日：162 个月中共识别 153 个计划入场日锁板观测，入场/退出分别有 287/286 个观测发生延迟，最终收益标签平均覆盖率为 97.64%、最低为 87.63%。Top 组按 10% ADV 参与率、完全换仓估算的中位容量约为 3.2–4.0 亿元，仅用于量级检查。历史总市值字段仍缺失，市值暴露不能可靠计算；按照计划书的数据停止条件，该项降级为限制披露，不使用指数权重冒充市值。

## 扩展因子与 Elastic Net（Commit 06–07 初版，非最终结果）

扩展因子单项结果见 [`docs/results/expanded_factor_ic.csv`](docs/results/expanded_factor_ic.csv)，Elastic Net分段结果见 [`docs/results/elastic_net_summary.csv`](docs/results/elastic_net_summary.csv)。这些文件记录已完成的初版实验：12列均满足逐月最低80%覆盖门槛，但单因子表使用了包含冻结期的全样本，且缺少Commit 06规定的开发期完整验证和冻结筛选。因此以下结果只能用于诊断和后续重跑对照。

- 单因子中，低特异波动（IC方向为负，绝对值5.97%）、低总波动（-5.45%）、低Beta（-4.27%）、BP（3.57%）、PB-ROE（3.51%）、12-1动量（3.25%）和1月反转（2.40%）具有显著预测信息。
- ROE TTM、毛利率、营收增长和盈利增长的独立IC较弱；它们是否提供条件性增量由Elastic Net系数和样本外预测共同判断。
- Elastic Net整体138个月Rank IC为5.54%，正IC比例67.39%；2015–2022开发期IC为5.28%，2023–2025冻结样本外IC为6.06%、Newey-West t值2.90。
- 线性模型的主要稳定贡献来自12-1动量、低特异波动、1月反转、BP和毛利率。冻结样本外IC高于行业调整PB-ROE的2.62%，说明扩展因子提供了统计增量；成本后组合增量仍需在Commit 08验证。

## LightGBM 非线性检验（Commit 07 初版，待重跑）

与Elastic Net的可提交对照见 [`docs/results/lightgbm_summary.csv`](docs/results/lightgbm_summary.csv)。LightGBM沿用同一12因子、60个月滚动窗口和最后12个月时序验证集，固定超参数并使用early stopping；未增加第二个树模型。

- LightGBM整体138个月Rank IC为4.28%，低于Elastic Net的5.54%；开发期IC为3.53%，同样低于Elastic Net的5.28%。
- 2023–2025冻结样本外IC为6.23%，仅略高于Elastic Net的6.06%，两者正IC月份比例同为67.65%左右。
- 主要增益重要性依次来自1月反转、12-1动量、60日波动率、特异波动率和毛利率；ROE与PB-ROE综合得分的重要性靠后。
- 当前证据不支持“LightGBM显著优于线性模型”。只有Commit 08证明其成本后组合表现也改善，才能认为非线性提供有效增量。

## 组合优化与模型可交易性（Commit 08 初版，待重跑）

初版对照见 [`docs/results/portfolio_model_comparison.csv`](docs/results/portfolio_model_comparison.csv)。两种模型均使用Ledoit-Wolf协方差、3%单票上限、行业偏离不超过5%、单月换手不超过30%和相同风险/换手惩罚；138个月全部求解成功，fallback均为0。因免费源没有历史沪深300真实权重，行业基准使用当期成员等权代理并明确披露。

- 2023–2025冻结样本外，等权基准年化5.62%；30bp成本后Elastic Net年化8.64%、LightGBM年化9.39%，对应最大回撤分别为-13.48%和-13.15%。
- 50bp成本下两模型冻结样本外仍分别年化8.26%和9.00%，说明该阶段增量未被简化交易成本完全吞噬。
- LightGBM在冻结期比Elastic Net年化高约0.75个百分点，同时IC略高；但2015–2022开发期两者成本后年化均约-1.7%，全样本也均落后等权基准。
- 冻结期超额收益主要来自2023年；2024和2025两种模型平均月度超额均为负，绝对超额最大的5个月约占总绝对波动38%。因此LightGBM不满足“增量不是由少数时期驱动”的有效条件，最终结论仍是非线性没有提供稳健优势。

## 初版结果展示（Commit 09，待更新）

离线 Dashboard 从本地冻结结果生成在 `results/runs/modern-pb-roe/dashboard.html`，不重新运行下载、训练或回测。Git 中保存以下轻量矢量备份，可直接用于论文和展示：

- [原研报复现累计净值](docs/results/figures/paper-reproduction.svg)
- [扩展因子 Rank IC](docs/results/figures/expanded-factor-ic.svg)
- [Elastic Net 与 LightGBM 分段 IC](docs/results/figures/model-ic-comparison.svg)
- [约束组合成本后累计净值](docs/results/figures/portfolio-net-value.svg)

所有图片均由真实 `paper-reproduction` 和 `modern-pb-roe` 结果生成，不包含 smoke fixture 数据；但模型相关图片对应尚未完成Commit 06筛选的初版实验，不能作为最终论文图片。Dashboard 与静态图的生成命令记录在 [`docs/runbook.md`](docs/runbook.md)。

## 初版审计记录（Commit 10，待重新验收）

旧审计摘要见 [`docs/results/final_audit_summary.json`](docs/results/final_audit_summary.json)，旧版10分钟讲稿见 [`docs/presentation_10min.md`](docs/presentation_10min.md)。14项检查证明初版流水线在数据闸门、预测时间顺序、组合约束和离线展示方面内部一致，但没有检查“扩展因子是否先在开发期完成验证和冻结”。因此该记录保留作审计轨迹，不代表最终研究已冻结。

初版阶段结论是：原研报PB-ROE Top50的方向与收益量级可以复现，但行业等权最优未复现；当前12列初版实验显示部分扩展因子具有预测信息，LightGBM冻结期略优但开发期失效。扩展因子筛选和模型重跑完成前，不冻结现代改进部分的最终结论。

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
