# 10-Minute English Presentation Script

## Slide 1 — Title · 0:00–0:35

Good morning. My project rebuilds a Chinese PB–ROE stock-selection rule published in 2011 as a modern point-in-time research process.

I first reproduce the historical rule. I then diagnose modern PB–ROE, require every extension to prove incremental information beyond that baseline, compare an eight-factor equal-weight score with Elastic Net and LightGBM, and finally build constrained portfolios.

The historical rule is broadly reproducible. Simple factor diversification improves the baseline, but machine learning adds no value over equal weighting. The positive revised result is exploratory rather than untouched out of sample.

## Slide 2 — Economic and market logic · 0:35–1:15

PB–ROE combines value and quality. ROE measures profitability on book capital. PB measures the market price paid for that capital. Profitable but cheaply valued firms may be repriced slowly because of anchoring, extrapolation and limits to arbitrage.

But low PB may be a value trap. High ROE may come from leverage, a cyclical peak or accounting choices. Crowding and turnover can erase the spread.

So I require positive Rank IC, statistical stability, ordered five-group returns, post-cost payoff and honest later evidence. An attractive cumulative curve alone is not enough.

## Slide 3 — Engineering and AI governance · 1:15–1:55

This is an executable cross-sectional research environment, not a spreadsheet backtest.

Five canonical Parquet tables describe securities, the trading calendar, historical CSI 300 membership, prices and point-in-time fundamentals. At each month-end, factors are winsorized at the first and ninety-ninth percentiles and standardized across stocks.

The same panel feeds IC tests, five-group portfolios, PB–ROE incremental screening, walk-forward models and a CVXPY optimizer. AI assisted specification review, implementation, debugging and documentation. I retained responsibility for the hypotheses, thresholds, evidence labels and conclusions. Eighty-seven tests and thirty-one release audits independently verify the outputs.

## Slide 4 — Time design · 1:55–2:45

The project has two separate historical lines.

The original-paper reproduction runs from 2005 to March 2011 and contains eighteen real holding periods. The modern dataset starts in 2010, but January 2010 to April 2012 is warm-up history. Momentum needs roughly one year of prices; Beta, idiosyncratic volatility and the risk matrix need long trailing windows. PB and ROE coverage becomes consistently usable only in May 2012.

Modern PB–ROE evaluation starts in May 2012. Standalone gates and PB–ROE incremental screening use 2015 through 2022. Strict reversal was fixed before its 2023-to-2025 test. The revised eight-factor design was created after those years had been inspected, so they are exploratory for the revised models.

At every forecast, only labels whose holding periods have ended can enter training. This prevents code leakage, but it does not turn already observed history back into untouched evidence.

## Slide 5 — Historical reproduction · 2:45–3:25

The original score rewards high ROE and low PB. I use historical CSI 300 constituents and the latest financial information available at each signal date.

After the paper’s cost assumptions, the reproduced PB–ROE Top 50 portfolio earns 29.86 percent annualized, versus 35 percent in the original report. It beats the constituent equal-weight proxy in twelve of eighteen holding periods.

The direction and magnitude are broadly reproducible. However, the industry-equal-weight version is not the best in my data. Free sources cannot reconstruct every Wind field or historical industry label, so the correct claim is rule and direction reproduction, not numerical identity.

## Slide 6 — Modern PB–ROE · 3:25–4:05

In the modern monthly sample, PB–ROE has a mean Rank IC of 5.13 percent and a Newey–West t-statistic of 3.73. It ranks future returns better than BP or ROE alone.

But after thirty basis points, its long–short return is only 2.78 percent annualized, and five-group monotonicity is 0.70, below my 0.80 gate.

This diagnosis motivates the extension: PB–ROE still has information, but value and profitability alone do not create a clean modern trading payoff.

## Slide 7 — Twelve-factor standalone validation · 4:05–5:00

I organize twelve candidates into value, quality, growth, momentum and risk-and-trading styles. These are common practitioner factors, not a commercial Barra model.

For standalone validity, every factor must pass five development gates: IC, Newey–West significance, positive-year stability, five-group monotonicity and a positive spread after thirty basis points.

Only one-month reversal passes all five. Its development IC is 4.47 percent, but its later IC falls to minus 1.89 percent. I preserve that failure and do not replace it with a factor that happened to look better later.

The interactive tiles show each factor’s market pattern, mechanism, limitation, monthly IC and five-group result.

## Slide 8 — PB–ROE incremental factor evidence · 5:00–6:00

This slide is the key bridge from diagnosis to modern improvement.

BP and ROE remain the core. For each of nine other candidates, I regress the candidate on BP and ROE within each month, then compute the residual Rank IC. This asks whether the candidate contains information that value and profitability do not already explain.

I also construct an Add-one score: two-thirds PB–ROE plus one-third of the candidate. The candidate must raise mean IC and improve PB–ROE in at least half of the eight development years. Correlation must remain below 0.85, and data and direction checks must pass.

Six extensions qualify: twelve-minus-one momentum, one-month reversal, low total volatility, low liquidity, low Beta and low idiosyncratic volatility. Gross margin, revenue growth and earnings growth fail. Together with BP and ROE, the final model manifest has eight inputs. The rules were fixed before this rerun.

## Slide 9 — Walk-forward models · 6:00–7:05

For every prediction month, I use at most sixty mature historical months and at least twenty-four. Elastic Net uses the full window. LightGBM fits the earlier forty-eight months and validates on the final twelve mature months in time order. There is no random shuffle.

In the 2023-to-2025 exploratory history, PB–ROE IC is 7.22 percent. Eight-factor equal weight reaches 10.91 percent. Elastic Net has 1.91 percent and LightGBM 3.48 percent.

The extensions add information, but dynamic weighting does not. Equal weighting fixes economically meaningful directions and averages noise. Rolling coefficients and tree thresholds are more flexible, but sixty monthly observations are a short time series and factor relationships change.

The model comparison is still valuable because it falsifies the assumption that complexity automatically creates alpha.

## Slide 10 — Constrained portfolio · 7:05–8:30

I send PB–ROE, eight-factor equal weight, Elastic Net and LightGBM through the same fully invested, long-only optimizer. Every portfolio has a three-percent stock cap and ten, thirty and fifty basis-point cost scenarios.

Discretionary turnover is capped at thirty percent from drifted pre-trade weights. If an index rebalance forces more turnover, the cap expands only to the mathematically unavoidable floor, and costs still include every trade. Static industry constraints are disabled because the available industry field is not point in time.

After thirty basis points, the proxy benchmark earns 5.58 percent annualized. PB–ROE earns 11.56 percent. Eight-factor equal weight earns 15.87 percent, with Sharpe 0.86 and maximum drawdown minus 12.25 percent. Elastic Net earns 1.65 percent. LightGBM earns 5.25 percent.

The simplest diversified signal has the best return, Sharpe and drawdown. But this remains exploratory history, and the linear cost model does not fully capture market impact or capacity.

## Slide 11 — Conclusion · 8:30–10:00

Five conclusions matter.

First, the historical PB–ROE direction and return magnitude are broadly reproducible, although the exact Wind fields and industry result are not.

Second, PB–ROE retains modern ranking information, but its economic payoff is weaker and less monotonic.

Third, the only standalone development winner fails its prior out-of-sample test. That negative result remains part of the study.

Fourth, six extensions prove development-sample incrementality beyond PB and ROE. Their eight-factor equal-weight score improves the PB–ROE baseline in exploratory history.

Fifth, Elastic Net and LightGBM do not beat that simple equal-weight score. Machine-learning enhancement is therefore not established.

The next step is not a large parameter search. It is to freeze this code, eight-factor manifest and thresholds, then evaluate genuinely new months. A future version may add economically distinct data such as analyst revisions and reliable point-in-time industry classifications.

The project’s contribution is an industry-style MVP: reproduce the idea, diagnose the baseline, require new factors to prove incremental value, compare complexity with a simple benchmark, translate signals into constrained portfolios and label the evidence honestly.

Thank you.

## Short Q&A Answers

**Why keep Elastic Net and LightGBM if equal weight wins?**

They are controlled challengers. Their failure shows that dynamic weighting and nonlinear interactions do not add value in this sample.

**Did the revised model use future data?**

No future label enters training. The result is exploratory because the researcher had already seen 2023–2025 before revising the feature design.

**Is this Barra?**

No. The project uses common style categories, not MSCI Barra factor definitions, exposures or a Barra risk model.

**Why exclude PB–ROE from the model?**

PB–ROE is derived from BP and ROE. It remains the comparison baseline, but adding all three to the model would count the same core information twice.

**Why can low volatility enter if its standalone spread is weak?**

Standalone tradability and model incrementality answer different questions. Low volatility enters only because its residual IC, Add-one IC and yearly improvement pass the frozen development gates; the final equal-weight and model comparisons then test whether that information is useful in combination.
