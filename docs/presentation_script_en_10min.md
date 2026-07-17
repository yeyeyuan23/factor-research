# 10-Minute English Presentation Script

## Slide 1 — Title · 0:00–0:35

Good morning. Our project rebuilds a Chinese PB–ROE stock-selection rule published in 2011 as a modern point-in-time research process.

We reproduce the historical rule, diagnose modern PB–ROE, redesign a compact eight-factor pool, require every extension to prove incremental value, and compare five-factor equal weight with Elastic Net and LightGBM inside the same constrained portfolio process.

The historical rule is broadly reproducible. The revised factor mix improves risk-adjusted performance, but not absolute return, and machine learning does not improve the final portfolio.

## Slide 2 — Economic and market logic · 0:35–1:15

PB–ROE combines value and quality. ROE measures profitability on book capital, while PB measures the market price paid for that capital. Profitable but cheaply valued firms may be repriced slowly because of anchoring, extrapolation and limits to arbitrage.

But low PB can be a value trap. High ROE can come from leverage, a cyclical peak or accounting choices. Crowding and turnover can erase the spread.

We therefore require positive Rank IC, statistical stability, ordered five-group returns, post-cost payoff and honest later evidence. An attractive cumulative curve alone is not enough.

## Slide 3 — Engineering and AI governance · 1:15–1:55

This is an executable cross-sectional research environment, not a spreadsheet backtest.

Five canonical Parquet tables describe securities, the trading calendar, historical CSI 300 membership, prices and point-in-time fundamentals. At each month-end, eight independent factors are winsorized at the first and ninety-ninth percentiles and standardized across stocks.

The same panel feeds IC tests, five-group portfolios, incremental screening, walk-forward models and a CVXPY optimizer. AI assisted specification review, implementation, debugging and documentation. We retained responsibility for the hypotheses, thresholds and conclusions. Ninety tests and thirty-one release audits verify the outputs.

## Slide 4 — Time design · 1:55–2:40

The project has two separate historical lines.

The original-paper reproduction runs from 2005 to March 2011 and contains eighteen real holding periods. The modern dataset starts in 2010, but January 2010 to April 2012 is warm-up history for momentum, volatility and the risk matrix. Modern PB–ROE evaluation starts in May 2012.

Standalone gates and incremental screening use 2015 through 2022. Strict reversal was fixed before its 2023-to-2025 test. The redesigned factor pool was created after those years had been inspected, so the same dates are exploratory for the revised models.

At every forecast, only labels whose holding periods have ended enter training. This prevents code leakage, but it cannot turn already observed history back into untouched evidence.

## Slide 5 — Historical reproduction · 2:40–3:20

The original score rewards high ROE and low PB. We use historical CSI 300 constituents and the latest financial information available at each signal date.

After the paper’s cost assumptions, the reproduced PB–ROE Top 50 portfolio earns 29.86 percent annualized, versus 35 percent in the original report. It beats the constituent equal-weight proxy in twelve of eighteen holding periods.

The direction and magnitude are broadly reproducible. The industry-equal-weight version is not the best in our data, so we claim rule and direction reproduction, not field-by-field Wind identity.

## Slide 6 — Modern PB–ROE · 3:20–4:00

In the modern monthly sample, PB–ROE has a mean Rank IC of 5.13 percent and a Newey–West t-statistic of 3.73. It ranks future returns better than BP or ROE alone.

But after thirty basis points, its long–short return is only 2.78 percent annualized, and five-group monotonicity is 0.70, below our 0.80 gate.

PB–ROE still contains information, but value and profitability alone no longer create a clean modern trading payoff. That diagnosis motivates the extension.

## Slide 7 — Eight-factor standalone validation · 4:00–5:00

We use four categories that are easy to explain at monthly frequency.

Value contains BP and earnings yield, or EP. Quality and growth contains ROE, operating cash flow to price, and revenue growth. Market behavior contains twelve-minus-one momentum and one-month reversal. Risk contains low sixty-day volatility. PB–ROE remains the comparison baseline and is not counted as an independent factor.

Each candidate faces five fixed gates: mean IC, Newey–West significance, positive years, five-group monotonicity and a positive spread after thirty basis points.

Only one-month reversal passes all five in development, with IC 4.47 percent and a 5.92 percent after-cost return. Its later IC falls to minus 1.89 percent. We preserve that failure rather than replacing it with a factor that happened to look better later. The interactive slide lets us inspect every factor’s IC and group chart.

## Slide 8 — Incremental evidence beyond PB–ROE · 5:00–6:00

This is the bridge from diagnosis to improvement.

BP and ROE remain the core. For each of six extensions, we regress the candidate on BP and ROE within each month and test residual Rank IC. We also construct an Add-one score: two-thirds PB–ROE plus one-third of the candidate. The candidate must raise mean IC, improve at least half of development years, remain below the correlation limit, and pass data and direction checks.

Momentum, reversal and low volatility pass. EP, operating cash flow to price and revenue growth do not improve Add-one IC, so we report them but do not force them into the model. Together with BP and ROE, the final manifest contains five inputs.

## Slide 9 — Walk-forward models · 6:00–7:05

For each prediction month, we use at most sixty mature months and at least twenty-four. Elastic Net uses the complete mature window. LightGBM fits the earlier forty-eight months and validates on the final twelve in time order. There is no random shuffle.

The models train on each month’s centered cross-sectional return rank because Rank IC is our final prediction metric. The portfolio still uses realized returns.

In 2023-to-2025 exploratory history, PB–ROE IC is 7.22 percent, five-factor equal weight is 8.35 percent, Elastic Net is 8.86 percent and LightGBM is 8.42 percent. The linear model ranks best. The tree still does not beat the linear benchmark, so nonlinear enhancement is not established.

## Slide 10 — Constrained portfolio · 7:05–8:35

We send PB–ROE, five-factor equal weight, Elastic Net and LightGBM through the same fully invested, long-only optimizer. Every portfolio has a three-percent stock cap and ten, thirty and fifty basis-point cost scenarios.

Discretionary turnover is capped at thirty percent from drifted pre-trade weights. If an index rebalance forces more turnover, the cap expands only to the mathematically unavoidable floor, and costs still include every trade. Static industry constraints are disabled because the available industry field is not point in time.

After thirty basis points, the proxy benchmark earns 5.58 percent annualized. PB–ROE earns 11.56 percent. Five-factor equal weight earns 11.44 percent. It does not beat PB–ROE on raw return, but its Sharpe is higher at 0.61 versus 0.51 and its maximum drawdown is slightly smaller at minus 12.14 percent.

Elastic Net earns 7.78 percent and LightGBM 6.95 percent. Higher Rank IC did not fully translate into portfolio return because signal magnitude, constraints and turnover also matter.

## Slide 11 — Conclusion · 8:35–10:00

Five conclusions matter.

First, the historical PB–ROE direction and return magnitude are broadly reproducible, although the exact Wind fields and industry result are not.

Second, PB–ROE retains modern ranking information, but its economic payoff is weaker and less monotonic.

Third, the only standalone development winner fails its prior out-of-sample test.

Fourth, three extensions prove development-sample incrementality. The five-factor equal-weight portfolio improves Sharpe and drawdown, but not absolute annualized return relative to PB–ROE.

Fifth, Elastic Net produces a small exploratory Rank IC improvement, but no portfolio improvement. LightGBM does not beat Elastic Net or equal weight.

The next step is not a large parameter search. We should freeze this code, five-factor manifest, rank target and cost assumptions, then evaluate genuinely new months. The contribution is an industry-style MVP: reproduce the idea, diagnose the baseline, require incremental evidence, compare complexity with a simple benchmark, translate signals into constrained portfolios and label the evidence honestly.

Thank you.

## Short Q&A Answers

**Why keep Elastic Net and LightGBM if equal weight wins?**

They are controlled challengers. Elastic Net tests whether stable linear reweighting helps; LightGBM tests whether thresholds and interactions help. The current portfolio evidence says neither should replace equal weight.

**Did the revised model use future data?**

No future label enters training. The result is still exploratory because we had already inspected 2023–2025 before redesigning the factor pool.

**Why use monthly data?**

Financial statements change quarterly and become public on announcement dates. We align them point in time at each month-end, while price factors are calculated from daily history and sampled monthly. Daily rebalancing would not create new accounting information.

**Is this Barra?**

No. We use common economic categories, not MSCI Barra factor definitions or a Barra risk model.

**Why exclude PB–ROE from the model?**

PB–ROE is derived from BP and ROE. It remains the comparison baseline, but adding all three would count the same core information twice.

**Why can low volatility enter if its standalone spread is weak?**

Standalone tradability and incremental information answer different questions. Low volatility enters because its residual IC, Add-one IC and yearly improvement pass the development gates; the later portfolio test then decides whether that information is useful in combination.
