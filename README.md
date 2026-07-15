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
| 06 | 按5类Barra-style框架构建扩展因子；只在2015–2022开发期完成单因子验证、筛选、冻结和等权多因子基准 | `f5fe62f` | **已重新完成**；12个候选五分组验证、3个因子冻结，十组残留已清理 |
| 07 | 仅使用Commit 06冻结的因子，按相同walk-forward口径训练Elastic Net和唯一树模型LightGBM | `648dde5` | **已重新完成**；训练入口强制读取3因子冻结文件，旧12因子模型产物已替换 |
| 08 | 使用Commit 07冻结预测做Ledoit-Wolf风险估计、CVXPY约束组合、失败回退及10/30/50bp成本检验 | `9f37564` | **已重新完成**；主动风险版本跨开发期和冻结期改善，Elastic Net确定为主模型 |
| 09 | 只读取重跑后的冻结结果生成离线Dashboard和静态备份，不下载、训练或回测 | `4e26435` | **已重新完成**；离线Dashboard仅读取最终冻结结果，正式静态图全部由Matplotlib生成 |
| 10 | 对最终流水线做泄漏检查、结果与哈希冻结、结论审阅和10分钟演示彩排 | `271541d` | **已重新完成**；15项审计通过，最终报告与10分钟PPT已冻结 |

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

Commit 06–08现已按上述顺序重新完成。失效的12因子结果和初版展示文件已删除；Commit 09–10只能读取新的3因子模型与组合结果。

### Commit 06 因子验证结论

正式候选与淘汰原因见 [`docs/results/factor_validation_summary.csv`](docs/results/factor_validation_summary.csv)，冻结名单见 [`docs/results/frozen_factor_selection.json`](docs/results/frozen_factor_selection.json)，方向调整后的等权基准见 [`docs/results/equal_weight_factor_baseline.csv`](docs/results/equal_weight_factor_baseline.csv)，入选因子相关矩阵见 [`docs/results/selected_factor_correlations.csv`](docs/results/selected_factor_correlations.csv)。筛选只使用2015–2022开发期；冻结期指标是在名单确定后追加报告，不参与`selected`判断。

- 12个候选覆盖Value、Quality、Growth、Momentum、Risk & Trading五类；筛选数量没有预设，按 `IC≥2%`、`NW t≥2.0`、五分组单调性≥0.8和30bp多空为正等冻结规则，实际保留PB-ROE综合、12–1月动量和低特异波动3个因子。
- 反转、低Beta和BP虽有正IC，但未通过收紧后的单调性门槛；其余候选因IC、显著性、单调性或成本被淘汰。
- 三因子开发期等权得分IC为6.19%、Newey-West t值5.69；五组严格递增，30bp成本后多空年化6.94%、Sharpe 0.86、最大回撤-8.78%。
- 冻结期等权得分IC为9.87%，30bp成本后多空年化2.51%，50bp为1.67%；方向延续但五组不再严格单调。
- 候选因子平均绝对行业主动权重约1.7%–2.4%，入选因子相关性绝对值最高约0.43；历史总市值缺失，规模暴露继续按停止条件降级披露，不以指数权重替代。

展示用基础IC图见 [`docs/results/figures/equal-weight-ic-matplotlib.png`](docs/results/figures/equal-weight-ic-matplotlib.png)：蓝/红柱表示正/负Rank IC，橙色虚线为IC均值，黑线为累计IC，竖向虚线标出2023年冻结样本外起点。

Commit 06的完整方法、12个候选各自的IC图、五分组单调性图和筛选结论见 [`docs/factor_analysis_report.md`](docs/factor_analysis_report.md)。


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

## 三因子 Elastic Net（Commit 07 正式结果）

单因子正式证据见 [`docs/factor_analysis_report.md`](docs/factor_analysis_report.md)，Elastic Net分段结果见 [`docs/results/elastic_net_summary.csv`](docs/results/elastic_net_summary.csv)。训练入口会校验配置指纹并强制读取Commit 06的冻结文件；本次实际输入只有12–1月动量、低特异波动和PB-ROE综合3列，不再以覆盖率合格代替因子筛选。

- Elastic Net整体138个月Rank IC为6.07%，正IC比例67.39%；2015–2022开发期IC为5.55%。
- 2023–2025冻结样本外IC为8.12%、Newey-West t值3.74，横截面预测在冻结期保持显著。
- 滚动平均系数为动量+0.00263、低特异波动原始方向-0.00248、PB-ROE综合+0.00020；前两者每期非零，PB-ROE约52.9%的月份非零。
- 这些指标只证明预测排序；成本后真实多头组合仍须由Commit 08使用新预测重新优化后判断，旧组合结果不能沿用。

## LightGBM 非线性检验（Commit 07 正式结果）

与Elastic Net的可提交对照见 [`docs/results/lightgbm_summary.csv`](docs/results/lightgbm_summary.csv)。LightGBM沿用同一3因子、60个月滚动窗口和最后12个月时序验证集，固定超参数并使用early stopping；没有第二个树模型。

- LightGBM整体Rank IC为2.59%，低于Elastic Net的6.07%；开发期IC为2.98%，同样低于Elastic Net的5.55%。
- 2023–2025冻结样本外IC仅1.73%、Newey-West t值0.98，明显低于Elastic Net的8.12%和3.74。
- 增益重要性依次为低特异波动、PB-ROE综合、12–1月动量。
- 当前证据明确不支持非线性优于线性模型；Commit 08仍可按计划做同口径组合对照，但主模型应为Elastic Net。

正式模型对比图：

- [开发期与冻结期IC/t值对比](docs/results/figures/model-ic-segment-comparison.png)
- [月度IC与累计IC](docs/results/figures/model-ic-timeseries.png)

## 组合优化与模型可交易性（Commit 08 正式结果）

完整分析见 [`docs/portfolio_analysis_report.md`](docs/portfolio_analysis_report.md)，机器可读对照见 [`docs/results/portfolio_model_comparison.csv`](docs/results/portfolio_model_comparison.csv)。两种模型均使用Ledoit-Wolf协方差、3%单票上限、行业偏离不超过5%、单月换手不超过30%和相同风险/换手惩罚；138个月全部求解成功，fallback均为0。因免费源没有历史沪深300真实权重，基准使用当期成员等权代理。

- 修复了月度预测与年化协方差直接混用的单位错误；旧结果无效。正式优化会先将月度预测年化，再与年化风险进入同一目标函数。
- 风险目标进一步改为相对成分等权基准的主动风险 `(w-b)'Σ(w-b)`，与指数增强目标一致；该修改是在查看首次冻结期结果后完成，最终冻结期只能视为后验稳健性证据。
- 30bp后Elastic Net全样本年化11.49%/Sharpe 0.50，基准为7.83%/0.31；开发期为6.78%/0.31，基准为3.08%/0.13。
- 2023–2025冻结期Elastic Net年化7.24%、Sharpe 0.32、最大回撤-17.21%，基准分别为5.62%、0.20和-21.51%；50bp年化仍为6.49%。
- LightGBM全样本未跑赢，冻结期IC也不显著；最终主模型为Elastic Net，复杂非线性没有稳定增量。
- 现代组合绝对年化低于原研报35%和本项目复现29.31%，但跨区间不可直接比较。现代改进的贡献是严格PIT和风险约束下的小幅风险调整增量，而不是复制早期牛市收益。

正式组合图：

- [30bp累计净值与回撤](docs/results/figures/portfolio-performance.png)
- [开发期/冻结期收益与Sharpe](docs/results/figures/portfolio-segment-metrics.png)
- [冻结期年度收益](docs/results/figures/portfolio-oos-yearly.png)

Commit 09只读取冻结的原研报、因子、模型和组合结果生成约5MB的自包含离线Dashboard，没有下载、训练或回测，也没有重新生成已淘汰的十组图。正式静态图全部由项目Python脚本调用Matplotlib生成。

## 最终交付与审计（Commit 10）

- 最终研究报告：[`docs/final_research_report.md`](docs/final_research_report.md)
- 10分钟展示PPT：[`docs/PB-ROE复现与改进_10min.pptx`](docs/PB-ROE复现与改进_10min.pptx)
- PPT可复现构建脚本：[`scripts/build_final_presentation.mjs`](scripts/build_final_presentation.mjs)
- 最终审计摘要：[`docs/results/final_audit_summary.json`](docs/results/final_audit_summary.json)

Commit 10最终审计共15项：新增检查确认原研报复现为2005-05-09至2011-03-25完整18期，而不是2007年开始的12期截断版本；16项数据质量闸门通过；Elastic Net与LightGBM各41,366条预测均满足训练/验证时间早于信号日；两种组合均满足满仓、非负权重、3%单票上限和30%换手上限；Dashboard不依赖外部Plotly CDN；冻结区间配置保持为2023–2025。

PPT只嵌入项目Python脚本用Matplotlib生成的已有研究图，不使用生成式图片，并已逐页渲染检查、通过画布溢出测试。最终结论保留主动风险版本的审计限制：该目标是在查看首次冻结期结果后修正，因此2023–2025只能称为后验稳健性证据。

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
