# 12因子有效性分析与冻结报告

## 1. 这一阶段要回答什么

Commit06的目标不是凑出固定数量的因子，而是先在统一规则下评价12个候选，再把真正通过全部门槛的因子冻结给Commit07。正式重跑后，12个候选中只有**1个月反转**通过；旧版“三因子名单”及其分析已经失效，不再作为工程结论。

机器可读结果见[`results/factor_validation_summary.csv`](results/factor_validation_summary.csv)，每个因子的IC图和五分组图位于[`results/figures/factor-analysis-12/`](results/figures/factor-analysis-12/)。所有图片均由Python/Matplotlib从冻结结果生成。

## 2. 数据、时间和目标

| 项目 | 正式设定 |
|---|---|
| 股票池 | 每个信号日有效的沪深300历史成分股；790只是2010–2025所有历史成分的去重并集 |
| 因子计算起点 | 2012-05；2010-01至2012-04只用于积累价格历史和检查覆盖 |
| 筛选开发期 | 2015-01至2022-12，共96个月 |
| 冻结检验期 | 2023-01至2025-12，实际有34个完整下一月收益标签 |
| 预测目标 | 下一持有期原始个股收益，不使用当前行业快照中性化历史标签 |
| 缺失退出收益 | 分组在信号日先确定；缺失收益按0计，不依据未来可得性删股 |
| 预处理 | 每月截面1%/99%分位缩尾，再做z-score；当前实现没有使用MAD缩尾 |
| 分组 | 五分组；因子方向统一后，Q5代表预期收益更高的一组 |
| 成本 | 单边10/30/50bp；主门槛使用30bp后的Q5−Q1 |

行业字段来自抓取时的BaoStock静态快照，不能代表历史时点行业。因此本报告中的行业暴露只作为描述性敏感性诊断，不参与正式标签或组合约束。

## 3. 12个因子的类别、公式和方向

| 因子 | 类别 | 代码中的定义 | 评价方向 |
|---|---|---|---|
| BP | Value | `book_equity / market_cap`，工程中由`1 / PB`得到 | 越高越好 |
| PB-ROE综合 | Value | `ROE百分位 + 1 - PB百分位` | 越高越好 |
| ROE | Quality | TTM每股收益 / 平均每股净资产；仅使用信号日前已公告数据 | 越高越好 |
| 毛利率 | Quality | 披露的销售毛利率 | 越高越好 |
| 营收增长 | Growth | 披露的营业收入同比增长率 | 越高越好 |
| 盈利增长 | Growth | 披露的归母净利润同比增长率 | 越高越好 |
| 12–1月动量 | Momentum | `close[t-21] / close[t-252] - 1` | 越高越好 |
| 1个月反转 | Momentum | `-(close[t] / close[t-21] - 1)` | 越高越好，即上月跌得更多 |
| 60日波动率 | Risk & Trading | 60日收益标准差乘`sqrt(252)` | 越低越好，评价时乘-1 |
| 20日流动性 | Risk & Trading | `log(1 + 20日平均成交额)` | 按预设低流动性方向，评价时乘-1 |
| 252日Beta | Risk & Trading | 个股与等权市场日收益的滚动协方差 / 市场方差 | 越低越好，评价时乘-1 |
| 特异波动率 | Risk & Trading | `sqrt((个股方差-cov²/市场方差)×252)` | 越低越好，评价时乘-1 |

## 4. 统一筛选门槛

一个因子必须在2015–2022开发期同时满足：

1. 平均Rank IC不低于2%；
2. Newey–West t值不低于2；
3. 年度平均IC为正的年份比例不低于50%；
4. 五组平均收益与Q1→Q5组号的Spearman相关不低于0.8；
5. 30bp成本后的Q5−Q1年化收益为正。

这里的“五分组单调”只检查五个组的**组均值横截面顺序**，不是要求每组内部每只股票按收益排序。组内仍然会有噪声和个股差异。

## 5. 完整表现和筛选原因

下表全部使用开发期作筛选；“冻结IC”只用于最后检验，不能反过来修改名单。

| 因子 | 开发IC | NW t | 正IC年份 | 单调性 | 30bp多空年化 | 冻结IC | 结论/失败原因 |
|---|---:|---:|---:|---:|---:|---:|---|
| 1个月反转 | 4.47% | 2.29 | 75.0% | 1.00 | 5.92% | -1.89% | **通过全部门槛** |
| 特异波动率 | 5.76% | 3.00 | 75.0% | 0.70 | 3.45% | 11.88% | 单调性不足 |
| 60日波动率 | 5.21% | 2.84 | 75.0% | 0.10 | -2.96% | 12.03% | 单调性、成本后收益失败 |
| 252日Beta | 4.90% | 2.06 | 62.5% | 0.60 | 0.38% | 6.89% | 单调性不足 |
| PB-ROE综合 | 3.66% | 2.06 | 75.0% | 0.60 | -0.90% | 5.49% | 单调性、成本后收益失败 |
| 12–1月动量 | 2.94% | 1.39 | 75.0% | 1.00 | 6.23% | 3.79% | t值不足 |
| 20日流动性 | 2.72% | 1.71 | 62.5% | 0.30 | -1.97% | 4.11% | t值、单调性、成本后收益失败 |
| ROE | 2.68% | 1.74 | 75.0% | 0.80 | -0.14% | -3.11% | t值、成本后收益失败 |
| BP | 2.18% | 0.89 | 75.0% | -0.20 | -5.04% | 9.36% | t值、单调性、成本后收益失败 |
| 毛利率 | 2.06% | 1.39 | 75.0% | 0.50 | 1.48% | -3.34% | t值、单调性不足 |
| 营收增长 | -0.50% | -0.32 | 50.0% | -0.10 | -4.27% | -7.19% | IC、t值、单调性、成本后收益失败 |
| 盈利增长 | -1.04% | -0.79 | 37.5% | -0.70 | -5.09% | -3.00% | 除覆盖外全部失败 |

![12因子门槛矩阵](results/figures/presentation-en/03-factor-gates.png)

## 6. 每个因子的IC和五分组图

| 因子 | 月度IC与累计IC | 五分组收益与累计净值 |
|---|---|---|
| BP | ![BP IC](results/figures/factor-analysis-12/bp-ic.png) | ![BP quantiles](results/figures/factor-analysis-12/bp-quantiles.png) |
| PB-ROE综合 | ![PB-ROE IC](results/figures/factor-analysis-12/paper-score-ic.png) | ![PB-ROE quantiles](results/figures/factor-analysis-12/paper-score-quantiles.png) |
| ROE | ![ROE IC](results/figures/factor-analysis-12/roe-ic.png) | ![ROE quantiles](results/figures/factor-analysis-12/roe-quantiles.png) |
| 毛利率 | ![毛利率 IC](results/figures/factor-analysis-12/gross-margin-ic.png) | ![毛利率 quantiles](results/figures/factor-analysis-12/gross-margin-quantiles.png) |
| 营收增长 | ![营收增长 IC](results/figures/factor-analysis-12/revenue-growth-ic.png) | ![营收增长 quantiles](results/figures/factor-analysis-12/revenue-growth-quantiles.png) |
| 盈利增长 | ![盈利增长 IC](results/figures/factor-analysis-12/earnings-growth-ic.png) | ![盈利增长 quantiles](results/figures/factor-analysis-12/earnings-growth-quantiles.png) |
| 12–1月动量 | ![动量 IC](results/figures/factor-analysis-12/momentum-12-1-ic.png) | ![动量 quantiles](results/figures/factor-analysis-12/momentum-12-1-quantiles.png) |
| 1个月反转 | ![反转 IC](results/figures/factor-analysis-12/reversal-1m-ic.png) | ![反转 quantiles](results/figures/factor-analysis-12/reversal-1m-quantiles.png) |
| 60日波动率 | ![总波动 IC](results/figures/factor-analysis-12/volatility-60d-ic.png) | ![总波动 quantiles](results/figures/factor-analysis-12/volatility-60d-quantiles.png) |
| 20日流动性 | ![流动性 IC](results/figures/factor-analysis-12/liquidity-20d-ic.png) | ![流动性 quantiles](results/figures/factor-analysis-12/liquidity-20d-quantiles.png) |
| 252日Beta | ![Beta IC](results/figures/factor-analysis-12/beta-252d-ic.png) | ![Beta quantiles](results/figures/factor-analysis-12/beta-252d-quantiles.png) |
| 特异波动率 | ![特异波动 IC](results/figures/factor-analysis-12/idiosyncratic-volatility-ic.png) | ![特异波动 quantiles](results/figures/factor-analysis-12/idiosyncratic-volatility-quantiles.png) |

## 7. 冻结结论与结果分析

冻结文件[`results/frozen_factor_selection.json`](results/frozen_factor_selection.json)只包含`reversal_1m_z`。这不是说反转因子在经济上已经稳定有效，而是说它是开发期唯一同时满足五项预设规则的候选。

真正重要的后续证据是：该因子在2023–2025的冻结IC变为-1.89%，30bp后的分组年化收益为-14.67%。因此Commit06的正确结论是：

- 开发期确实找到一个统计与分组条件都合格的短期反转信号；
- 该信号没有在冻结期延续，存在明显时变或开发期选择误差；
- 不应根据冻结期表现回头加入特异波动率、低Beta或PB-ROE，否则会造成事后挑选；
- Commit07仍应严格使用这1个冻结因子，检验Elastic Net和LightGBM能否改善其时变性。

最后，冻结期中部分未入选因子表现反而很好（例如低波动、BP），恰好说明“看完样本外再换名单”会很容易制造漂亮但无效的结论。本项目保留负结果，是比追求固定因子数量更重要的研究纪律。
