# 10-Minute English Presentation Script

## Slide 1 — Research question · 0:00–0:45

Good afternoon. Today we present a reproduction and modernization of a Chinese PB–ROE stock-selection strategy published in 2011.

Our central question is not simply whether we can reproduce an attractive historical return. It is whether the original economic idea survives a modern, point-in-time research process.

We answer this in three stages: reproduce the historical rule, test PB–ROE in a modern monthly sample, and ask whether additional factors and models create genuine improvement.

The main result is deliberately mixed: the historical effect is broadly reproducible, modern PB–ROE still contains information, simple factor diversification improves risk-adjusted performance, but machine learning does not improve the final portfolio.

## Slide 2 — Economic hypothesis · 0:45–1:25

The original idea combines value and quality.

ROE measures how profitably a company uses book capital. PB measures how much investors pay for that capital. The strategy therefore looks for firms that are profitable but still cheaply valued.

Investors may react slowly to improving fundamentals, remain anchored to past weakness, or avoid apparently distressed stocks. High-ROE and low-PB firms may therefore be repriced gradually.

But the same signal can fail. Low PB may indicate a value trap, while high ROE may reflect leverage, a cyclical peak or accounting effects. Turnover and crowding may also remove the return.

This gives us our evaluation principle: we must test prediction, statistical stability, portfolio ordering, transaction costs and later-period persistence separately.

## Slide 3 — Research implementation · 1:25–2:05

To test that idea fairly, we built one reproducible cross-sectional research pipeline rather than a collection of spreadsheet backtests.

Five canonical datasets contain the universe, calendar, historical CSI 300 membership, prices and point-in-time fundamentals. At each month-end, factors are winsorized and standardized. The same panel supports IC analysis, grouped returns, screening, models and portfolios.

The important point is consistency. Every method sees the same universe, signal dates, return labels and cost assumptions. AI assisted coding, debugging and documentation, but the economic hypotheses, thresholds, evidence labels and final conclusions remained researcher-owned.

Ninety automated tests and thirty-one release audits check this design. The next question is how we separate the time periods.

## Slide 4 — Time framework · 2:05–2:55

There are two distinct historical lines, and they must not be mixed.

The first is the original-paper reproduction from 2005 to 2011, containing eighteen actual holding periods. This window answers only whether the published rule can be reproduced.

The modern line starts collecting data in 2010, but the period to April 2012 only builds history for momentum, volatility and covariance. Modern evaluation starts in May 2012, after data coverage becomes reliable. Factor and model development use 2015 to 2022.

Every prediction uses only labels whose holding periods have ended. The 2023-to-2025 period is prior out-of-sample for the frozen reversal rule, but exploratory for the redesigned model because we had already inspected those years.

With that evidence boundary defined, we can begin with the historical reproduction.

## Slide 5 — Historical reproduction · 2:55–3:35

The original rule ranks historical CSI 300 constituents using high ROE and low PB, based only on information available at each signal date.

After applying the paper’s cost assumptions, our reproduced PB–ROE Top 50 portfolio earns 29.86 percent annualized, compared with 35 percent in the original report. It beats the constituent equal-weight proxy in twelve of eighteen holding periods.

So the direction and broad magnitude are reproducible. However, the industry-equal-weight version is not the best version in our data. Free data fields, industry definitions and execution details also differ from Wind.

We therefore reproduce the rule and its direction, not every original database field. The more important question is whether the same idea remains useful after 2012.

## Slide 6 — Modern PB–ROE diagnosis · 3:35–4:20

In the modern monthly sample, PB–ROE still ranks future returns. Its mean Rank IC is 5.13 percent, with a Newey–West t-statistic of 3.73, and it is stronger than BP or ROE alone.

But predictive information is not the same as an investable payoff. After thirty basis points of cost, the long–short return is only 2.78 percent annualized. Five-group monotonicity is 0.70, below our 0.80 requirement.

This is the key diagnosis of the project. The historical value-quality idea has not disappeared, but its modern payoff is weaker and less orderly. PB–ROE therefore remains our baseline, while the improvement stage asks what information it is missing.

That motivates a compact factor pool rather than immediately applying machine learning.

## Slide 7 — Eight-factor standalone test · 4:20–5:15

We designed eight independent candidates in four interpretable groups.

Value contains BP and earnings yield; quality and growth contains ROE, cash flow to price and revenue growth; market behavior contains momentum and reversal; risk contains low volatility.

Each candidate faces the same five development-period gates: sufficient mean Rank IC, Newey–West significance, consistency across years, ordered five-group returns and a positive long–short payoff after thirty basis points.

Only one-month reversal passes all five gates. Its development IC is 4.47 percent and its post-cost return is 5.92 percent. However, its later-period IC becomes minus 1.89 percent.

Strict standalone screening therefore does not guarantee persistence. But standalone tradability is not the same as usefulness inside a combination, so we need a second screening layer.

## Slide 8 — Incremental factor selection · 5:15–6:15

This second layer creates the logical bridge from the PB–ROE diagnosis to the final factor model.

BP and ROE remain the core because they define the original hypothesis. For each of the other six factors, we ask whether it adds information beyond that core.

First, we remove the part explained by BP and ROE and test residual Rank IC. Second, we add the candidate to PB–ROE and require improved IC in at least half of the development years. We also check coverage, direction and redundancy.

Momentum, reversal and low volatility pass. Earnings yield, cash flow to price and revenue growth do not improve the Add-one signal, so they do not enter the model.

The final input set therefore contains five factors: BP, ROE, momentum, reversal and low volatility. Only after freezing these inputs do we compare weighting methods.

## Slide 9 — Walk-forward model comparison · 6:15–7:20

We compare three ways to combine the same five inputs.

The first is direction-adjusted equal weight, which is our simple benchmark. Elastic Net tests whether stable linear reweighting adds value. LightGBM tests whether nonlinear thresholds and interactions add further value.

All three use the same monthly panel and up to sixty completed months. Elastic Net uses the mature window; LightGBM fits the earlier forty-eight months and validates on the final twelve in time order. No unfinished label enters training.

In the exploratory 2023-to-2025 history, PB–ROE has a Rank IC of 7.22 percent, five-factor equal weight 8.35 percent, Elastic Net 8.86 percent and LightGBM 8.42 percent.

Elastic Net ranks slightly better, but the tree does not beat the linear model. We must now test whether these ranking differences survive portfolio constraints and costs.

## Slide 10 — Portfolio result · 7:20–8:40

We pass all four signals through the same fully invested, long-only portfolio process. This isolates the signal rather than changing portfolio rules for each model.

After thirty basis points of cost, the equal-weight CSI 300 proxy earns 5.58 percent annualized. PB–ROE earns 11.56 percent. Five-factor equal weight earns 11.44 percent, so it does not beat PB–ROE on absolute return.

However, the five-factor portfolio has the best risk-adjusted result. Its Sharpe ratio is 0.61, compared with 0.51 for PB–ROE, and its maximum drawdown is slightly smaller at minus 12.14 percent.

Elastic Net earns 7.78 percent and LightGBM 6.95 percent. Their Rank IC does not translate into a better portfolio because constraints, turnover and signal magnitude also matter.

The investment conclusion is therefore simpler than the prediction ranking suggests.

## Slide 11 — Conclusion · 8:40–10:00

We can now answer the original question in four steps.

First, the historical PB–ROE effect is broadly reproducible in direction and magnitude, although not field by field.

Second, PB–ROE still contains modern ranking information, but its economic payoff is weaker and less monotonic than in the original period.

Third, adding momentum, reversal and low volatility to BP and ROE improves diversification. The five-factor equal-weight portfolio improves Sharpe and drawdown, but not absolute annualized return.

Fourth, greater model complexity is not rewarded. Elastic Net produces the highest exploratory Rank IC, but neither Elastic Net nor LightGBM beats simple equal weight in the final portfolio.

The contribution is therefore not a claim of a superior strategy. It is an industry-style MVP: reproduce the idea, diagnose its weakness, require incremental evidence, compare complexity with a simple benchmark, and preserve negative results.

The next valid test is to freeze the current five-factor manifest, model rules and cost assumptions, then evaluate genuinely new months. Thank you.

## Short Q&A Answers

**Why keep Elastic Net and LightGBM if equal weight wins?**

They are controlled challengers. Elastic Net tests stable linear reweighting, while LightGBM tests nonlinear relationships. Their failure to beat equal weight is itself an important result about model complexity.

**Did the revised model use future data?**

No unfinished future label enters training. The result is still exploratory because the research team had already inspected the 2023–2025 period before redesigning the factor pool.

**Why use monthly data?**

Financial information changes mainly when quarterly statements are announced. We align those statements point in time at each month-end; price-based factors use daily history but are sampled monthly. Daily rebalancing would not create new accounting information.

**Is this a Barra model?**

No. We use interpretable economic factor categories, not MSCI Barra definitions or a complete Barra risk model.

**Why is PB–ROE not also included as a model input?**

PB–ROE is derived from BP and ROE. It remains the baseline, but including all three would count the same core information twice.

**Why can low volatility enter if it fails the standalone portfolio gate?**

Standalone tradability and incremental information answer different questions. Low volatility enters because it adds development-period information beyond BP and ROE; the portfolio test then determines whether that information is useful in combination.
