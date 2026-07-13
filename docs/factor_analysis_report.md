# Commit 06 因子分析报告

## 1. 目的与边界

本报告记录扩展因子的**开发期验证与冻结**，而不是模型训练结果。候选因子按 Value、Quality、Growth、Momentum、Risk & Trading 五类组织；筛选只使用 2015-01 至 2022-12。2023-01 至 2025-12 是冻结样本外，仅在名单固定后用于报告。

因子分数、下一月收益和行业中性目标均来自本项目的 point-in-time 面板。低 Beta、低特异波动和低流动性在图表和IC计算中已经统一方向：数值越高，预期下一月收益越高。

## 2. 预先冻结的筛选规则

候选因子必须同时满足：

- 每月最低覆盖率不低于80%；
- 开发期 Rank IC 不低于2%；
- Newey-West t 值不低于1.5；
- 年度正IC比例不低于50%；
- 五分组30bp成本后收益的 Spearman 单调性不低于0.6；
- 30bp成本后 Top–Bottom 多空年化收益为正。

完整候选表、方向和淘汰原因见 [factor_validation_summary.csv](results/factor_validation_summary.csv)，冻结名单见 [frozen_factor_selection.json](results/frozen_factor_selection.json)。

## 3. 筛选结果

| 类别 | 保留 | 淘汰及原因 |
|---|---|---|
| Value | BP、PB-ROE综合 | 无 |
| Quality | 无 | ROE：分层不单调且30bp多空为负；毛利率：IC和t值不足 |
| Growth | 无 | 营收增长、盈利增长：IC和t值不足 |
| Momentum | 12–1月动量、1月反转 | 无 |
| Risk & Trading | 低Beta、低特异波动 | 流动性：IC、单调性和成本不合格；总波动率：单调性和成本不合格 |

规则没有预设入选数量。12个候选逐一通过同一组门槛后，实际有6个通过，最终冻结为：**BP、PB-ROE综合、12–1月动量、1月反转、低Beta、低特异波动**。入选因子间绝对相关性最大约为0.59，详见 [selected_factor_correlations.csv](results/selected_factor_correlations.csv)；没有出现接近完全重复的因子对。

## 4. 12个候选因子的完整证据

下表不是只展示最后入选的因子。每个候选都有一张月度 Rank IC/累计IC图和一张五分组收益/累计净值图；图全部由 `scripts/plot_all_factor_analysis.py` 使用 Matplotlib 从真实结果生成。这里的多空年化是行业中性目标收益上的五分组 Top–Bottom，按实际分组换手扣除30bp成本；它是因子可交易性的辅助证据，不等同于后续真实多头优化组合收益。

| 因子 | 开发期IC | NW t | 单调性 | 30bp多空年化 | 冻结期IC | 结论 | 图 |
|---|---:|---:|---:|---:|---:|---|---|
| 盈利增长 | 0.53% | 0.85 | 0.60 | 0.50% | -3.06% | 淘汰：IC、t不足 | [IC](results/figures/factor-analysis-12/earnings-growth-ic.png) · [五分组](results/figures/factor-analysis-12/earnings-growth-quantiles.png) |
| 营收增长 | 0.33% | 0.41 | 0.70 | 0.72% | -5.58% | 淘汰：IC、t不足 | [IC](results/figures/factor-analysis-12/revenue-growth-ic.png) · [五分组](results/figures/factor-analysis-12/revenue-growth-quantiles.png) |
| 12–1月动量 | 2.89% | 2.05 | 1.00 | 4.48% | 4.92% | **保留** | [IC](results/figures/factor-analysis-12/momentum-12-1-ic.png) · [五分组](results/figures/factor-analysis-12/momentum-12-1-quantiles.png) |
| 1月反转 | 2.87% | 2.17 | 0.60 | 1.84% | -0.38% | **保留**；冻结期衰减 | [IC](results/figures/factor-analysis-12/reversal-1m-ic.png) · [五分组](results/figures/factor-analysis-12/reversal-1m-quantiles.png) |
| 毛利率 | 0.68% | 1.01 | 0.60 | 0.80% | -2.20% | 淘汰：IC、t不足 | [IC](results/figures/factor-analysis-12/gross-margin-ic.png) · [五分组](results/figures/factor-analysis-12/gross-margin-quantiles.png) |
| ROE | 1.90% | 1.97 | 0.20 | -1.12% | -0.90% | 淘汰：IC、单调性、成本 | [IC](results/figures/factor-analysis-12/roe-ic.png) · [五分组](results/figures/factor-analysis-12/roe-quantiles.png) |
| 低Beta | 3.40% | 2.89 | 0.70 | 0.13% | 6.09% | **保留**；成本后较弱 | [IC](results/figures/factor-analysis-12/beta-252d-ic.png) · [五分组](results/figures/factor-analysis-12/beta-252d-quantiles.png) |
| 低特异波动 | 4.50% | 4.60 | 0.80 | 2.77% | 9.58% | **保留** | [IC](results/figures/factor-analysis-12/idiosyncratic-volatility-ic.png) · [五分组](results/figures/factor-analysis-12/idiosyncratic-volatility-quantiles.png) |
| 低流动性 | 1.27% | 1.11 | -0.40 | -4.45% | 2.43% | 淘汰：IC、t、单调性、成本 | [IC](results/figures/factor-analysis-12/liquidity-20d-ic.png) · [五分组](results/figures/factor-analysis-12/liquidity-20d-quantiles.png) |
| 低总波动率 | 3.76% | 4.12 | 0.50 | -0.73% | 9.34% | 淘汰：单调性、成本 | [IC](results/figures/factor-analysis-12/volatility-60d-ic.png) · [五分组](results/figures/factor-analysis-12/volatility-60d-quantiles.png) |
| BP | 2.76% | 2.52 | 0.70 | 1.01% | 5.44% | **保留** | [IC](results/figures/factor-analysis-12/bp-ic.png) · [五分组](results/figures/factor-analysis-12/bp-quantiles.png) |
| PB-ROE综合 | 3.67% | 3.70 | 0.90 | 1.64% | 4.20% | **保留** | [IC](results/figures/factor-analysis-12/paper-score-ic.png) · [五分组](results/figures/factor-analysis-12/paper-score-quantiles.png) |

单调性是开发期五组平均净收益与 Q1–Q5 顺序的 Spearman 相关系数，并不要求五根柱严格逐级升高。筛选只读开发期指标；冻结期IC在名单固定后报告，因此不会反向改变入选名单。

## 5. 六因子等权综合：IC稳定性

![六因子等权综合IC](results/figures/equal-weight-ic-matplotlib.png)

开发期六因子等权得分的 Rank IC 为 **6.53%**，Newey-West t 值为 **6.40**，ICIR 为 **2.21**，月度正IC比例为 **75%**。冻结期 Rank IC 为 **8.65%**、NW t 为 **5.69**。这说明冻结期的横截面排序预测并未减弱。

但这张图的累计IC不能单独推出可投资结论：IC只衡量横截面排序与下一月行业中性收益的相关性，还需要结合分层、成本和后续真实组合验证。

## 6. 五分组收益与单调性

![六因子等权综合五分组收益](results/figures/equal-weight-quantiles-30bp.png)

图中是六因子等权得分从低到高的五分组，按每组实际换手扣除30bp后，展示平均月收益：

| 区间 | Q1 | Q2 | Q3 | Q4 | Q5 | 判断 |
|---|---:|---:|---:|---:|---:|---|
| 开发期 | -0.57% | -0.38% | -0.08% | 0.15% | 0.13% | 总体从低到高改善，但Q4略高于Q5，不是严格单调 |
| 冻结期 | -0.27% | -0.37% | -0.17% | -0.04% | 0.14% | Q5仍显著最好；Q1/Q2次序反转，严格单调性不足 |

因此，六因子得分的主要证据是“低分组明显差、最高组相对好”，不是每个相邻分组都严格递增。开发期30bp Top–Bottom 年化为 **5.31%**，Sharpe 为 **0.70**；冻结期30bp Top–Bottom 年化降至 **1.62%**，50bp时仅 **0.05%**。成本敏感性表明统计预测能力没有完全转化为稳健的经济收益。

## 7. 暴露、容量与局限

- 候选因子的平均绝对行业主动权重约为1.7%–2.4%，并非完全行业中性；后续优化阶段仍需行业约束。
- 按10% ADV参与率、完全换仓的简化容量估计，入选因子的中位容量约为2.9–5.8亿元。
- 历史总市值字段不可可靠获得，规模暴露按项目停止条件降级披露，未以指数权重冒充规模中性。
- 免费财务源的历史公告口径存在限制，因此结果是严格PIT处理下的可复现研究证据，不是Wind逐值复刻。

## 8. Commit 06 结论与下一步

Commit 06完成了开发期因子筛选和冻结。六因子等权得分在开发期具有强IC和正的成本后分层收益，但冻结期分层收益明显走弱，因而不能把等权组合直接表述为稳定可交易策略。

下一阶段 Commit 07 只能使用本报告冻结的6个因子重训 Elastic Net 和 LightGBM；不得重新把已淘汰的增长、质量或流动性因子加入模型。
