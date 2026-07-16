# Reproducing and Modernizing the PB–ROE Strategy

## 10-minute English presentation script

Target speaking time: 9 minutes 40 seconds to 10 minutes. The remaining few seconds are a buffer for slide transitions. The Q&A section is separate and is designed for the following five minutes.

### Slide 1 — Title | 0:00–0:25

Good morning. My project asks whether a Chinese equity strategy published in 2011 survives modern point-in-time testing.

I reproduce the historical PB–ROE rule, evaluate its modern behavior, test twelve candidate factors, compare Elastic Net with LightGBM, and finally build constrained portfolios.

The historical rule is broadly reproducible, but the proposed modern improvement fails out of sample. That negative result is my central finding.

### Slide 2 — Economic and market logic | 0:25–1:05

PB–ROE is a value-quality hypothesis.

ROE measures the profitability earned on book capital. PB measures how much the market asks investors to pay for that capital. The combined score therefore rewards firms with high ROE and low PB.

The possible market mechanism is slow repricing. Investors may extrapolate recent bad news, anchor on past valuations, or be unable to arbitrage unpopular firms immediately.

But the idea can fail. Low PB can indicate a value trap, ROE can be cyclical or accounting-driven, factor crowding can remove the premium, and turnover can absorb the spread.

That is why I require positive IC, ICIR, ordered group returns, post-cost payoff and frozen-period persistence. An attractive cumulative curve alone is not enough.

### Slide 3 — Technical implementation and AI governance | 1:05–1:45

I implemented the study as a reproducible cross-sectional research environment rather than a spreadsheet backtest.

Five canonical Parquet tables contain the security master, trading calendar, historical CSI 300 membership, prices and point-in-time fundamentals. Every month, factors are winsorized at one and ninety-nine percent and standardized across the active cross-section. The same panel then supports IC tests, quantile portfolios, walk-forward models and CVXPY portfolio optimization.

AI assisted specification review, code scaffolding, debugging, documentation and plotting scripts. It did not choose the universe, thresholds, freeze rule or final conclusion. Those remained researcher decisions.

I independently checked the implementation with Git history, deterministic seeds, seventy-nine automated tests, seventeen release audits, input and result hashes, and figures generated from frozen CSV files rather than by a generative image model.

### Slide 4 — Time design and information timing | 1:45–2:40

The original-paper reproduction covers eighteen holding periods from 2005 to 2011.

For the modern layer, 2010 to April 2012 is warm-up history. It supplies trailing prices for momentum, beta, volatility and covariance. It is input history, not a missing backtest. Formal modern evaluation begins in May 2012. Factor selection and model development use 2015 through 2022. The frozen test is 2023 through 2025.

At every month-end, I freeze the information then available, trade at the next open, and allow a return label into training only after its holding period has ended.

One important repair concerns ROE timing. The corrected pipeline uses Eastmoney’s first announcement date, `NOTICE_DATE`, rather than a later update date. The median announcement lag is thirty-nine days and the ninety-fifth percentile is one hundred and nineteen days.

The 790 securities stored locally are only the union of all firms that entered the CSI 300 during the research window. Each monthly cross-section still uses the members active on that date; it is not a CSI 800 universe.

### Slide 5 — Original-paper reproduction | 2:40–3:25

The historical score is the ROE cross-sectional percentile plus one minus the PB percentile.

Using historical CSI 300 constituents and information available at each signal date, the reproduced PB–ROE Top 50 portfolio earns 29.86 percent annualized after the paper’s cost assumptions. The report gives 35 percent. The strategy beats the constituent equal-weight proxy in twelve of eighteen holding periods.

So the direction and approximate magnitude are reproducible.

However, the industry-equal-weight version is not the best version in my data. Free sources cannot reproduce every Wind field, historical industry label or adjustment method. The correct claim is broad reproduction, not numerical identity and not evidence that the original report fabricated results.

### Slide 6 — Modern PB–ROE | 3:25–4:15

In the modern monthly sample, PB–ROE has a mean Rank IC of 5.13 percent, an annualized ICIR of 0.82 and a Newey–West t-statistic of 3.73.

The statistical ranking signal therefore remains visible. Its economic payoff is much weaker. After thirty basis points, annualized Q5-minus-Q1 return is only 2.78 percent. Five-group monotonicity is 0.70, below the selection threshold of 0.80. ROE alone has almost no post-cost payoff.

I show static-industry-adjusted numbers only as a diagnostic. BaoStock’s industry field is a current snapshot. Applying it causally across history would create classification look-ahead.

The modern conclusion is therefore precise: PB–ROE retains ranking information, while its tradable payoff has materially decayed.

### Slide 7 — Twelve-factor validation | 4:15–5:05

I test twelve candidates across value, quality, growth, momentum and trading-risk styles.

Each factor must pass five development-sample gates: mean Rank IC of at least two percent, a Newey–West t-statistic of at least two, positive annual IC in at least half the years, five-group monotonicity of at least 0.8, and a positive long–short return after thirty basis points.

Only one-month reversal passes all five. Its development IC is 4.47 percent, ICIR is 0.86, t-statistic is 2.29, monotonicity is one, and post-cost annual return is 5.92 percent.

Low idiosyncratic volatility has stronger IC but fails monotonicity. Twelve-minus-one momentum fails significance. PB–ROE fails monotonicity and cost robustness.

I do not rescue near-passes after seeing later results.

### Slide 8 — Frozen-factor test | 5:05–5:45

The frozen list therefore contains only one-month reversal.

In 2023 through 2025, its IC changes from positive 4.47 percent in development to minus 1.89 percent. Its thirty-basis-point long–short return changes from positive 5.92 percent to minus 14.67 percent annualized.

Some factors rejected in development happen to perform well later. Substituting them now would turn the frozen period back into a development sample.

The honest conclusion is that the selected signal did not persist. The likely explanations are regime change and selection error, not simply insufficient model complexity.

### Slide 9 — Walk-forward windows and models | 5:45–7:10

The left side of the chart shows one real forecast window rather than an abstract description.

For the forecast on 31 January 2023, Elastic Net uses sixty mature signal months from December 2017 through November 2022.

LightGBM uses the same eligible history but splits it in time order: the first forty-eight months fit the tree and the last twelve mature months validate early stopping. There is no random shuffle.

The December 2022 signal is excluded. Its position entered on 3 January, but its return label did not finish until 1 February—one day after the forecast. The new January signal trades on 1 February and its label finishes on 1 March. Only after that date may it enter a later training window.

This rolling procedure repeats for every month.

The right side shows the result. In the frozen period, the direct signal and Elastic Net both have IC of minus 1.89 percent. Elastic Net’s ICIR is minus 0.31. LightGBM has IC of minus 1.70 percent and ICIR of minus 0.35.

LightGBM is slightly less negative in mean IC, but neither model establishes stable incremental prediction. With only one frozen input, the tree also has little stable interaction structure to learn.

### Slide 10 — Constrained portfolios | 7:10–8:30

I finally convert predictions into fully invested, long-only portfolios.

The covariance matrix uses trailing daily returns with Ledoit–Wolf shrinkage. Each stock is capped at three percent, monthly turnover is limited to thirty percent, and results are shown after thirty basis points.

Turnover is measured from drifted pre-trade weights, including forced exits, rather than by comparing two target portfolios. Historical industry constraints are disabled because the available classification is not point in time.

In the frozen period, the CSI 300 constituent equal-weight proxy earns 5.58 percent annualized with a Sharpe ratio of 0.20 and a maximum drawdown of minus 21.5 percent.

Elastic Net earns 0.36 percent, with Sharpe 0.01 and drawdown minus 29.3 percent. LightGBM earns 4.33 percent, with Sharpe 0.15 and drawdown minus 22.6 percent.

Neither model beats the benchmark. LightGBM loses less than Elastic Net, but “less bad” is not evidence of alpha. Portfolio optimization cannot rescue a negative-IC input.

### Slide 11 — Conclusion | 8:30–10:00

I draw five conclusions.

First, the historical PB–ROE direction and return magnitude are broadly reproducible.

Second, announcement timing and historical membership are economically important data decisions, not implementation details.

Third, PB–ROE retains modern ranking information, but its cost-adjusted payoff is much weaker.

Fourth, the only factor that passed every development gate failed in the frozen period. Elastic Net and LightGBM also failed to produce positive frozen IC.

Fifth, neither optimized portfolio beat the benchmark after costs, and their Sharpe ratios and drawdowns were not better.

So I cannot claim a winning modern strategy. The contribution is a transparent chain from economic hypothesis, to point-in-time data, to standardized factor tests, to strict walk-forward prediction, and finally to a constrained portfolio.

The remaining limitations are also clear: free data do not reproduce every Wind snapshot; historical industry classifications and true CSI 300 weights are missing; and the delisting and suspension ledger can be improved.

The next decisive test is genuinely new data after the current freeze. My final takeaway is simple: a reproducible negative result is stronger than a polished backtest with hidden look-ahead. Thank you.

## Five-minute Q&A preparation

### Economic logic

**Why should high ROE and low PB predict returns?**

ROE represents profitability on book capital and PB represents the price paid for it. If investors underreact to durable profitability or over-penalize temporarily unpopular firms, high-ROE, low-PB stocks may be repriced upward. The mechanism is conditional, so the empirical gates test whether it is present in each period.

**When should PB–ROE fail?**

It can fail when low PB reflects permanent impairment, ROE is inflated or mean-reverting, the style becomes crowded, growth firms dominate the regime, or costs and turnover exceed the spread. The modern results show exactly this gap between statistical ranking and tradable payoff.

### Statistical design

**What is ICIR and why report both ICIR and the Newey–West t-statistic?**

ICIR is mean monthly IC divided by its standard deviation and annualized by the square root of twelve. It measures stability. The Newey–West t-statistic asks whether the mean differs from zero after allowing serial dependence. They answer related but different questions.

**Why are five-group returns not strictly increasing for every individual month?**

Monotonicity is evaluated on average group returns across the chosen sample, not inside every month. Individual months are noisy. Requiring every month to be ordered would reject almost every real factor.

**Why not add the factors that performed well in 2023–2025?**

Those results were unavailable when the development rule was frozen. Adding them now would be sample-out overfitting and would destroy the meaning of the frozen test.

### Time and data

**Why is 2010–2012 not reported as a modern backtest?**

It is warm-up history needed for trailing one-year factors and the risk matrix. Formal modern factor evaluation begins in May 2012.

**Why are there 790 stocks if the universe is CSI 300?**

790 is the deduplicated union of companies that entered the CSI 300 between 2010 and 2025. Every monthly cross-section uses only the members active on that date.

**Did the original paper use future information?**

Its stated rule does not use future returns, but the report does not disclose enough proprietary snapshot detail to verify every field. This project reproduces the stated method and clearly labels the remaining uncertainty.

**Why remove the industry constraint?**

The available industry label is a current snapshot applied across history. Using it causally would introduce classification look-ahead. A historical point-in-time source is required before restoring that constraint.

### Models and portfolio

**Does LightGBM beat Elastic Net?**

It is slightly less negative in frozen mean IC and has a higher portfolio return, but both ICs are negative and both portfolios trail the benchmark. It does not meet the pre-defined standard for a successful nonlinear increment.

**Why use machine learning when only one factor passed?**

The model stage was a pre-defined falsification test: could dynamic weighting stabilize the frozen signal? With one feature, the answer is no, and the limited feature space helps explain why LightGBM adds little.

**Is the missing-return treatment perfect?**

No. Missing next-month returns remain in the pre-formed portfolio and are conservatively set to zero. A complete holding ledger using delisting cash flows and last tradable prices is a future accounting improvement.

### AI use

**What exactly did AI do, and how did you avoid copying its output?**

AI helped challenge specifications, scaffold code, locate bugs and draft documentation. Research choices were recorded in the project plan and decision log. Every numerical claim comes from frozen machine outputs, figures are generated by Python, and tests plus final audits check the implementation. AI suggestions that conflicted with the plan or evidence were rejected or corrected.
