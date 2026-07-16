# Reproducing and Modernizing the PB–ROE Strategy

## 10-minute English presentation script

Target length: about ten minutes. The slide notes embedded in the HTML use the same conclusions.

### Slide 1 — Title | 0:00–0:35

Good morning. My project asks whether a Chinese equity strategy published in 2011 survives modern point-in-time testing.

I first reproduce the historical PB–ROE rule. I then test twelve modern candidate factors, compare Elastic Net with LightGBM in a strict walk-forward design, and convert their predictions into constrained long-only portfolios.

The historical rule is broadly reproducible, but the modern improvement fails out of sample. That negative result is my central finding.

### Slide 2 — Research logic | 0:35–1:15

These are not separate backtests. They form one chain of evidence.

The reproduction asks whether I recover the original direction and magnitude. The modern evaluation asks whether PB–ROE still predicts returns. Factor validation freezes every candidate that passes the same gates, without choosing the number in advance. The model stage asks whether linear or nonlinear weighting improves the frozen signal. Finally, the portfolio stage asks whether prediction survives costs and constraints.

At every step, an improvement must beat the previous layer.

### Slide 3 — Time design and data timing | 1:15–2:15

The original-paper test covers eighteen holding periods from 2005 to 2011.

For the modern layer, 2010 to April 2012 is warm-up history. It supplies approximately one year of prices for momentum, beta, volatility and the covariance matrix. It is input history, not a missing backtest. Formal modern factor evaluation starts in May 2012. Factor selection and model development use 2015 through 2022. The frozen test is 2023 through 2025.

At every month-end I freeze the information then available, trade at the next open, and allow a return label into training only after its holding period has ended.

One important repair concerns ROE. The old pipeline used Eastmoney’s later update date as if it were the first announcement date. The corrected pipeline uses `NOTICE_DATE`. The median ROE announcement lag falls from roughly 456 days to 39 days, with a 95th percentile of 119 days.

Also, the 790 securities in storage are the union of all stocks that entered the CSI 300 during the research window. Each month still uses exactly that month’s 300 constituents. It is not a CSI 800 universe.

### Slide 4 — Original-paper reproduction | 2:15–3:05

The original score rewards high ROE and low PB.

Using historical CSI 300 constituents and only information available at each signal date, the reproduced PB–ROE Top 50 portfolio earns 29.86 percent annualized after the original cost assumptions. The paper reports 35 percent. The strategy beats the equal-weight proxy in twelve of eighteen holding periods.

So the historical direction and approximate magnitude are reproducible.

However, the industry-equal-weight version is not the best version in my data. Free data cannot replicate every Wind field, historical industry label or adjustment method. The correct conclusion is broad reproduction, not numerical identity and not evidence that the paper fabricated results.

### Slide 5 — Modern PB–ROE | 3:05–4:00

In the modern monthly sample, PB–ROE still has a mean Rank IC of 5.13 percent, with a Newey–West t-statistic of 3.73.

But the economic payoff is much weaker. After thirty basis points, the annualized Q5-minus-Q1 return is only 2.78 percent. Five-group monotonicity is 0.70, below my selection threshold of 0.80. ROE alone has little economic payoff.

I do show static-industry-adjusted numbers as a diagnostic, but I do not use them as the formal historical target. The free BaoStock industry field is a current snapshot. Applying it to old dates would create classification look-ahead.

The modern conclusion is therefore: PB–ROE retains ranking information, but its tradable payoff has decayed.

### Slide 6 — Twelve-factor validation | 4:00–5:05

I test twelve candidates from value, quality, growth, momentum and trading-risk styles.

Every factor must pass five development-sample gates: mean Rank IC of at least two percent, a Newey–West t-statistic of at least two, positive annual IC in at least half the years, five-group monotonicity of at least 0.8, and a positive long–short return after thirty basis points.

Only one-month reversal passes all five. Its development IC is 4.47 percent, its t-statistic is 2.29, monotonicity is exactly one, and the cost-adjusted annual return is 5.92 percent.

Low idiosyncratic volatility has stronger IC but fails monotonicity. Twelve-minus-one momentum fails significance. PB–ROE fails monotonicity and cost robustness.

I do not rescue near-passes after seeing the result.

### Slide 7 — Frozen-factor test | 5:05–5:55

The selected list therefore contains only one-month reversal.

This is where the result changes sharply. In 2023 through 2025, the frozen IC becomes minus 1.89 percent, and the thirty-basis-point long–short return becomes minus 14.67 percent annualized.

Several factors that failed development happen to look better later. I still do not substitute them, because that would turn the frozen period back into a development sample.

The honest conclusion is that the development winner did not persist. The likely explanations are factor regime change and selection error, not insufficient model complexity.

### Slide 8 — Strict walk-forward models | 5:55–7:05

I next test whether machine learning can stabilize the signal.

At each month-end, I keep only fully matured labels, use up to sixty months of history, retrain and trade at the next open. For example, when predicting on January thirty-first 2023, the November 2022 label is complete, but the December label has not finished and is excluded.

The direct frozen signal and Elastic Net both have a frozen IC of minus 1.89 percent. LightGBM has minus 1.70 percent.

LightGBM is slightly less negative than Elastic Net, but both are negative and statistically insignificant. Therefore, LightGBM does not satisfy the project requirement of a stable sample-out improvement over the linear benchmark.

With only one selected input, the tree model also has very little stable interaction structure to learn.

### Slide 9 — Constrained portfolios | 7:05–8:30

Finally, I convert predictions into fully invested, long-only portfolios.

The stock cap is three percent and monthly turnover is limited to thirty percent. Turnover is now computed from drifted pre-trade weights, including forced exits, instead of incorrectly reusing the previous target weights. I disable historical industry constraints because the available industry field is not point in time.

After thirty basis points, the CSI 300 constituent equal-weight proxy earns 5.58 percent annualized in the frozen period. Elastic Net earns only 0.36 percent, with a Sharpe ratio of 0.01 and a maximum drawdown of minus 29.31 percent. LightGBM earns 4.33 percent, with a Sharpe of 0.15 and a drawdown of minus 22.62 percent.

Neither model beats the benchmark. LightGBM loses less than Elastic Net, but “less bad” is not evidence of alpha. The portfolio layer cannot rescue a negative-IC input.

### Slide 10 — Conclusion | 8:30–10:00

I draw five conclusions.

First, the historical PB–ROE direction and return magnitude are broadly reproducible.

Second, corrected announcement timing matters. Using the later update date materially changed the factor-selection and model results, so the old three-factor conclusion had to be discarded.

Third, PB–ROE still contains modern ranking information, but its cost-adjusted payoff is much weaker.

Fourth, the only factor that passed the development gates did not survive the frozen period. Elastic Net and LightGBM also failed to produce positive frozen IC.

Fifth, neither optimized portfolio beat the benchmark after costs.

So I cannot claim a winning modern strategy. The contribution is a reproducible research chain that shows exactly where a historically successful idea stops generalizing.

The next decisive test is genuinely new data after the current freeze, together with point-in-time historical industry data and a full delisting and suspension holding ledger.

My final takeaway is simple: a reproducible negative result is stronger than a polished backtest with hidden look-ahead. Thank you.

## Short Q&A backup

**Why is 2010–2012 not reported as a modern backtest?**
It is the warm-up history needed to calculate trailing one-year factors and the risk matrix. Formal modern factor evaluation begins in May 2012.

**Why are there 790 stocks if the universe is the CSI 300?**
790 is the deduplicated union of companies that entered the CSI 300 between 2010 and 2025. Every monthly cross-section still uses the 300 members active on that date.

**Did the original paper use future information?**
Its stated rule does not use future returns, but the report does not disclose enough Wind snapshot detail to prove every field was fully point in time. This project therefore reproduces the stated method, not every proprietary data observation.

**Why not add the factors that performed well in 2023–2025?**
Because those results were not available when the development rule was frozen. Adding them now would be sample-out overfitting.

**Why remove the industry constraint?**
The available industry label is a current snapshot applied across history. Using it would introduce classification look-ahead. A historical point-in-time industry source is required before restoring the constraint.

**Does LightGBM beat Elastic Net?**
Only narrowly in frozen IC and portfolio return, but both ICs are negative and both portfolios trail the benchmark. It does not meet the pre-defined standard for a successful nonlinear increment.

**Is missing return treatment perfect?**
No. Missing next-month returns are kept in the pre-formed portfolio and conservatively set to zero. A full holding ledger using delisting cash flows and last tradable prices is the next accounting improvement.
