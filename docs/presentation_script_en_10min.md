# Reproducing and Modernizing the PB–ROE Strategy

## 10-minute English presentation script

Target length: approximately 10 minutes. The timing marks are for rehearsal and do not appear on the audience slides.

### Slide 1 — Title | 0:00–0:35

Good morning. My project starts from a simple question: can a successful Chinese equity strategy published in 2011 still survive modern scrutiny?

I first reproduce the original PB–ROE rule in its historical window. I then test the same idea in a modern CSI 300 sample, validate twelve candidate factors, compare simple and machine-learning combinations, and finally convert predictions into constrained long-only portfolios.

My main result is that modernization helps, but it helps through disciplined factor validation rather than model complexity.

### Slide 2 — Research logic | 0:35–1:20

The key is that these are not separate experiments. They form one chain of evidence.

The historical reproduction asks whether I can recover the original direction and magnitude. The modern evaluation asks whether the same signal still predicts returns. The factor stage asks what can add information beyond PB–ROE. The model stage asks whether dynamic weighting or nonlinear interactions beat a transparent equal-weight combination. Finally, the portfolio stage asks whether statistical prediction survives trading costs and constraints.

At every step, I require an incremental improvement over the previous layer. An attractive backtest alone is not enough.

### Slide 3 — Time design | 1:20–2:15

The time design is essential. The original reproduction is entirely separate from the modern study.

For modern factors, 2010 to early 2012 supplies the trailing price history needed to calculate twelve-minus-one momentum, beta, volatility and a risk matrix. It is not a period that should generate formal return conclusions.

The modern PB–ROE evaluation starts in May 2012, after financial-data coverage becomes consistently usable. Factor selection and model development are restricted to 2015 through 2022. The final diagnostic period is 2023 through 2025.

At every month-end, I freeze the information then available, trade at the next open, and only allow a realized target into training after its exit date. Also, the 790 securities in the data inventory are the historical union of stocks that entered the CSI 300—not a CSI 800 universe.

### Slide 4 — Original-paper reproduction | 2:15–3:10

The original score rewards high ROE and low PB. I reproduce the paper’s low-frequency rebalancing rule using historical CSI 300 constituents and the latest available PB and ROE.

The core Top 50 portfolio earns 29.31 percent annualized after the paper’s cost assumptions, compared with 35 percent in the report, and it beats the benchmark in twelve of eighteen holding periods. So the direction and rough magnitude are reproducible.

However, the industry-equal-weight version is not the best in my data, and this is not a field-by-field replication of Wind. The appropriate conclusion is basic reproduction, not numerical identity—and certainly not evidence of fabrication.

### Slide 5 — Modern PB–ROE | 3:10–4:10

Next, I move the original idea into a monthly modern sample from May 2012 to October 2025.

PB–ROE still has a mean Rank IC of 3.91 percent and a Newey–West t-statistic of 3.10. This means the cross-sectional ordering contains statistically meaningful information.

But the economic payoff is much smaller. The raw long–short return after thirty basis points of turnover cost is only 0.44 percent annualized. Industry adjustment improves it to 2.28 percent, but this remains far below the historical report. ROE alone is close to ineffective.

Therefore, the modern result is not “the paper still earns 35 percent.” It is “the signal survives statistically, while its tradable payoff has decayed.”

### Slide 6 — Twelve-factor validation | 4:10–5:15

I then test twelve candidates from value, quality, growth, momentum and risk. I do not decide in advance that I need three, five or six factors.

Every candidate must pass the same development-sample gates: Rank IC of at least two percent, a Newey–West t-statistic of at least two, positive annual IC in at least half the years, five-group monotonicity of at least 0.8, and a positive Q5-minus-Q1 return after thirty basis points.

Only three pass everything: PB–ROE, twelve-minus-one momentum and low idiosyncratic volatility. Several other factors have positive IC, but fail either monotonicity or trading-cost robustness. Keeping the rule fixed is more important than rescuing a near-pass after seeing the result.

### Slide 7 — Three-factor improvement | 5:15–6:15

Before using machine learning, I create the simplest possible modern benchmark: the average of standardized PB–ROE, momentum and negative idiosyncratic volatility.

In the 2015 to 2022 development period, the mean Rank IC rises from 3.67 percent for PB–ROE alone to 6.19 percent. The cost-adjusted long–short return rises from 1.64 to 6.94 percent. This is the strongest evidence that the modern extension adds value.

In the frozen period, IC is even higher at 9.87 percent, but the return falls to 2.51 percent and the five groups are no longer perfectly ordered. So the signal direction persists more strongly than the economic payoff.

### Slide 8 — Strict walk-forward models | 6:15–7:25

The machine-learning test is strictly walk-forward. At each month-end, I keep only labels whose full holding period has already ended. I use up to sixty months of mature history, retrain, predict the current cross-section and trade at the next open.

For example, on January thirty-first 2023, the November 2022 return label is complete and can be used, but the December label does not finish until February first and is excluded. This creates a one-month label isolation gap and prevents future return leakage.

After this repair, equal weighting remains best. Frozen IC is 9.87 percent, versus 7.82 for Elastic Net and 3.24 for LightGBM. With only three low-dimensional factors, flexible nonlinear interactions do not receive enough stable information. Complexity adds estimation error rather than predictive value.

### Slide 9 — Constrained portfolios | 7:25–8:45

Finally, I convert predictions into fully invested, long-only portfolios with a three-percent stock cap, five-percent industry deviation limit, thirty-percent monthly turnover limit and transaction costs.

Elastic Net earns 7.75 percent annualized after thirty basis points, compared with 5.58 percent for the CSI 300 constituent equal-weight proxy. Its Sharpe rises from 0.20 to 0.34, and drawdown improves.

However, the information ratio is only 0.13, the outperformance is concentrated in 2023, and the strategy lags in 2024 and 2025. More importantly, the active-risk objective was introduced after the first frozen-period review. The result is useful robustness evidence, but it is not a pristine, untouched out-of-sample alpha claim.

### Slide 10 — Conclusion | 8:45–10:00

To conclude, the project supports four claims.

First, the historical PB–ROE result is broadly reproducible. Second, the signal still ranks stocks in the modern CSI 300, but its return after costs is far weaker. Third, momentum and low idiosyncratic volatility provide a meaningful modern improvement. Fourth, the transparent equal-weight combination is more predictive than either Elastic Net or LightGBM.

What I cannot claim is equally important. This is not a field-by-field Wind replication, LightGBM does not add nonlinear value, and the optimized portfolio has not demonstrated persistent live alpha.

The next decisive test is to freeze the present code and evaluate genuinely new months.

My final takeaway is simple: modernization worked through disciplined factor validation, not model complexity. Thank you.

## Short Q&A backup

**Why is 2010–2012 not reported as a backtest?**  
It is a warm-up period used to calculate trailing price-based factors and risk estimates. The modern evaluation begins only after the required factor and financial-data histories are available.

**Did the original paper use future information?**  
Its stated rule does not directly use future returns, but the report does not disclose enough historical field detail to prove that every underlying Wind observation was fully point-in-time.

**Why does equal weighting beat machine learning?**  
There are only three selected factors and relatively few independent monthly regimes. The dominant structure is stable and low-dimensional, so additional model flexibility mainly increases estimation error.

**Why can Elastic Net have lower IC but a better portfolio result?**  
IC measures cross-sectional ranking. The portfolio also reflects score magnitudes, covariance estimates, active-risk optimization, industry limits and turnover constraints. These can favor a smoother linear forecast even when its raw ranking is weaker.

**Can the frozen-period portfolio be called out-of-sample?**  
The prediction timing is strict, but the active-risk objective was changed after the first frozen-period review. It should therefore be described as post-hoc robustness evidence, not a pristine untouched test.
