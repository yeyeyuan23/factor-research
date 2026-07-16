# 10-Minute English Presentation Script

## Slide 1 — Title · 0:00–0:35

Good morning. My project asks how a Chinese PB–ROE stock-selection rule published in 2011 changes when it is rebuilt as a modern point-in-time research process.

I first reproduce the historical rule. I then re-evaluate PB–ROE in a modern monthly setting, test twelve candidate factors, separate standalone factor validity from model-input eligibility, compare a simple eleven-factor score with Elastic Net and LightGBM, and finally build constrained portfolios.

My main result is nuanced: the historical rule is broadly reproducible, and simple multi-factor diversification is promising. However, machine learning adds no value over equal weighting, and the revised positive result is exploratory rather than untouched out of sample.

## Slide 2 — Economic and market logic · 0:35–1:20

PB–ROE combines value and quality. ROE measures profitability on book capital. PB measures the market price paid for that capital. The hypothesis is that profitable but cheaply valued firms may be repriced slowly because of anchoring, extrapolation and limits to arbitrage.

But each leg can fail. Low PB may be a value trap. High ROE may come from leverage, a cyclical peak or accounting choices. The trade can become crowded, and turnover can consume the spread.

So I do not accept a visually attractive equity curve. I require positive Rank IC, statistical stability, ordered five-group returns, positive payoff after costs and honest evidence from later data.

## Slide 3 — Engineering and AI governance · 1:20–2:00

This is an executable cross-sectional research environment, not a spreadsheet backtest.

Five canonical Parquet tables describe securities, the trading calendar, historical CSI 300 membership, prices and point-in-time fundamentals. At each month-end, factors are winsorized at the first and ninety-ninth percentiles and standardized across the available stocks.

The same panel feeds IC tests, five-group portfolios, walk-forward models and a CVXPY portfolio optimizer. AI helped review specifications, scaffold code, debug and draft documentation. I retained responsibility for the universe, hypotheses, thresholds, evidence labels and conclusions. Tests, deterministic seeds, input hashes and a final machine audit independently check the outputs.

## Slide 4 — Time design · 2:00–2:55

The project has two separate historical lines.

The original-paper reproduction runs from 2005 to March 2011 and contains eighteen real holding periods. It is a genuine backtest of the historical rule.

The modern dataset begins in 2010, but January 2010 to April 2012 is only warm-up history. Twelve-minus-one momentum needs roughly one year of prices, while Beta, idiosyncratic volatility and the risk matrix need long trailing windows. PB and ROE coverage also becomes consistently usable only in May 2012. So warm-up data are inputs to later signals, not missing return results.

Modern PB–ROE evaluation begins in May 2012. Standalone gates and model eligibility use 2015 through 2022. The strict reversal rule was fixed before its 2023-to-2025 test. The revised eleven-factor design was created after that period had already been inspected, so those same dates are exploratory for the revised models.

At every fold, only labels whose holding periods have ended can enter training. This prevents code leakage, but it does not turn already observed history back into untouched evidence.

## Slide 5 — Historical reproduction · 2:55–3:40

The original score rewards high ROE and low PB. I use historical CSI 300 constituents and the latest financial information available at each signal date.

After the paper’s cost assumptions, the reproduced PB–ROE Top 50 portfolio earns 29.86 percent annualized, versus 35 percent in the original report. It beats the constituent equal-weight proxy in twelve of eighteen holding periods.

The direction and magnitude are therefore broadly reproducible. However, the industry-equal-weight version is not the best version in my data. Free sources cannot reconstruct every Wind field, historical industry label or adjustment convention, so the appropriate claim is rule and direction reproduction, not field-by-field numerical identity.

## Slide 6 — Modern PB–ROE · 3:40–4:25

In the modern monthly sample, PB–ROE has a mean Rank IC of 5.13 percent and a Newey–West t-statistic of 3.73. It ranks future returns better than BP or ROE alone.

But economic performance is much weaker than in the historical paper. After thirty basis points, the long–short return is only 2.78 percent annualized, and five-group monotonicity is 0.70, below my 0.80 gate.

This means value and quality still contain ranking information, but the payoff is not cleanly ordered or strongly tradable. Static industry labels improve some diagnostics, but they are current snapshots and therefore cannot support a causal historical industry-neutral claim.

## Slide 7 — Twelve-factor validation · 4:25–5:35

I organize twelve candidates into value, quality, growth, momentum and risk-and-trading styles. These are common academic and practitioner factors; this is not a commercial Barra model.

Each factor has an economic pattern and a failure mode. BP represents value but can select value traps. ROE and gross margin represent quality but are affected by leverage, cycles and industry differences. Revenue and earnings growth may capture fundamental acceleration, but suffer from base effects and non-recurring items. Twelve-minus-one momentum reflects slow information diffusion but can crash when trends reverse. One-month reversal reflects temporary liquidity shocks but has high turnover. Low volatility and low Beta may arise from leverage constraints, while their main limitation is defensive-industry exposure. Low idiosyncratic volatility may reflect lottery preference but overlaps with total risk. Low liquidity may earn a premium, although capacity and impact are difficult to model.

For standalone validity, every factor must pass five development gates: IC, Newey–West significance, positive-year stability, five-group monotonicity and a positive spread after thirty basis points. Only one-month reversal passes all five. Its development IC is 4.47 percent, but this result does not survive later data.

The interactive tiles show each factor’s monthly IC, group returns, market pattern, mechanism and limitation.

## Slide 8 — Two-layer factor evidence · 5:35–6:25

The strict reversal list remains frozen and its failure is preserved. In the prior out-of-sample period, reversal IC falls to minus 1.89 percent. I do not replace it with factors that happened to look better later.

I then ask a different question: can a factor be a useful model input even if it cannot independently satisfy every trading gate?

The eligibility layer checks point-in-time data, coverage, cross-sectional variation, conflict with a pre-declared economic direction and redundancy above 0.85 correlation. Eleven primitive factors qualify. PB–ROE itself is excluded from the model because it is derived from BP and ROE.

The direction-adjusted eleven-factor equal-weight score has an exploratory IC of 8.37 percent. No standalone gate was relaxed; the two layers answer different questions.

## Slide 9 — Walk-forward models · 6:25–7:25

For every prediction month, I use at most sixty mature historical months and at least twenty-four. Elastic Net uses the full training window. LightGBM fits the earlier forty-eight months and uses the final twelve mature months for time-ordered early stopping. There is no random shuffle.

All methods use the same eleven-feature manifest. In the 2023-to-2025 exploratory history, the simple equal-weight score has IC 8.37 percent. Elastic Net has 1.93 percent and LightGBM 3.58 percent.

LightGBM is better than Elastic Net, but neither beats the simple score. The likely reason is estimation error. Equal weighting fixes economically meaningful directions and averages noise. Rolling regression coefficients and tree thresholds are more flexible, but the monthly time series is short and factor relationships change over time.

Therefore, the model comparison is still valuable: it falsifies the assumption that complexity automatically creates alpha.

## Slide 10 — Constrained portfolio · 7:25–8:35

I send strict reversal, eleven-factor equal weight, Elastic Net and LightGBM through the same optimizer.

Every portfolio is fully invested and long-only, with a three-percent stock cap, a thirty-percent turnover limit and ten, thirty and fifty basis-point cost scenarios. Turnover is measured from drifted pre-trade weights. I disable historical industry constraints because the available industry field is not point in time.

After thirty basis points, the CSI 300 constituent equal-weight proxy earns 5.58 percent annualized. Strict reversal loses 4.84 percent. The eleven-factor equal-weight portfolio earns 9.76 percent, with a Sharpe ratio of 0.54 and maximum drawdown of minus 12.29 percent. Elastic Net earns 1.85 percent. LightGBM earns 5.24 percent.

The simplest diversified signal therefore has the best return, Sharpe and drawdown. It also remains at 9.12 percent under fifty basis points. However, these are exploratory historical results, and the cost model does not fully capture impact, limit-up queues or large-scale capacity.

## Slide 11 — Conclusion · 8:35–10:00

Four conclusions are supported.

First, the historical PB–ROE direction and return magnitude are broadly reproducible, although the industry version and exact Wind values are not.

Second, PB–ROE retains modern ranking information, but its economic payoff is much weaker and less monotonic.

Third, the only standalone development winner fails its prior out-of-sample test. That negative result remains part of the study.

Fourth, eleven reliable primitive factors show promising diversification, but Elastic Net and LightGBM do not beat their simple equal-weight baseline. Machine-learning enhancement is therefore not established.

The next step is not another large parameter search. It is to freeze this code, feature manifest and thresholds, then evaluate genuinely new months. A future version may add economically distinct data such as analyst revisions, and a reliable point-in-time industry classification and historical benchmark weights.

The project’s main contribution is an industry-style MVP: reproduce the idea, audit information timing, test factors individually, qualify model inputs separately, compare complexity with a simple benchmark, translate signals into constrained portfolios and label the evidence honestly.

Thank you.

## Short Q&A Answers

**Why keep Elastic Net and LightGBM if equal weight wins?**

Because the models are controlled challengers. Their failure is evidence that dynamic weighting and nonlinear interactions do not add value in this sample.

**Did the revised model use future data?**

No future label enters training. The result is called exploratory because the researcher had already seen the 2023–2025 period before revising the feature design.

**Is this Barra?**

No. The factors use common style categories, but the project does not implement MSCI Barra factor definitions, exposures or a Barra risk model.

**Why exclude PB–ROE from the model?**

PB–ROE is a derived combination of BP and ROE. Keeping all three would count the same information twice.
