# 工程代码走读：从一条原始记录到最终结论

这份文档不是另一份项目计划，而是一张“读代码地图”。第一次看工程时，不要按文件名字母顺序阅读；应当沿着数据流读：

```text
YAML研究口径
  -> 五张canonical数据表与时点审计
  -> 原研报规则复现
  -> 现代PB-ROE评价
  -> 12因子独立验证 + 模型输入资格manifest
  -> 严格反转 / 11因子等权 / 两模型walk-forward预测
  -> 风险约束组合与成本核算
  -> 冻结结果、图片、HTML和最终审计
```

## 1. 先建立三个概念

1. **配置是实验合同**：`configs/paper.yaml`定义2005–2011原研报复现，`configs/modern.yaml`定义2015–2025现代实验；代码不能临时改变时间、成本或筛选门槛。
2. **runner是每一阶段的入口**：先读各目录的`runner.py`，知道输入和输出，再下钻公式文件。不要一上来逐行读所有工具函数。
3. **结果分本地运行与Git冻结两层**：`results/runs/`保存完整本地运行，`docs/results/`只保存最终审计通过后可提交的摘要和图片。

## 2. 建议的第一遍阅读顺序

按下面顺序读，约60–90分钟可以理解主链路：

| 顺序 | 文件 | 先回答的问题 |
|---|---|---|
| 1 | `README.md`、`docs/project_plan.md` | 项目研究什么，10个阶段完成到哪里？ |
| 2 | `configs/paper.yaml`、`configs/modern.yaml` | 两层实验的时间、股票池、成本和门槛是什么？ |
| 3 | `src/pb_roe/cli.py` | 一条命令最终调用哪个runner？ |
| 4 | `src/pb_roe/data/bundle.py`、`schema.py`、`pit.py` | 五张表如何组织，怎样禁止未来数据？ |
| 5 | `src/pb_roe/reproduction/runner.py` | 原研报的信号、持有期和收益怎样串起来？ |
| 6 | `src/pb_roe/evaluation/runner.py` | 现代PB-ROE如何计算IC、五分组和成本后收益？ |
| 7 | `src/pb_roe/factors/validation.py`、`eligibility.py` | 独立因子门槛与模型输入资格为什么分开？ |
| 8 | `src/pb_roe/models/runner.py`、`linear.py`、`lightgbm.py` | 每个月怎样只用当时已实现的标签训练？ |
| 9 | `src/pb_roe/portfolio/runner.py`、`optimizer.py` | 预测怎样变成满足约束的持仓？ |
| 10 | `src/pb_roe/validation/final_audit.py` | 哪些条件不通过就不能发布结论？ |

第二遍再读对应测试。测试通常比实现更快地告诉你一个函数必须保证什么。

## 3. CLI怎样把整个工程串起来

入口是`src/pb_roe/__main__.py`，命令解析和路由在`src/pb_roe/cli.py`。主要命令与代码入口如下：

| 命令 | 主要入口 | 作用 |
|---|---|---|
| `config-check` | `config.py` | 检查YAML必填字段并输出确定性配置指纹 |
| `data ingest` | `data/ingest_baostock.py` | 下载或复用缓存，生成五张canonical表 |
| `data audit` | `data/audit.py` | 检查主键、覆盖率、价格、成员区间和公告滞后 |
| `reproduce` | `reproduction/runner.py` | 复现2005–2011原研报规则组合 |
| `evaluate` | `evaluation/runner.py` | 评价现代BP、ROE与PB-ROE |
| `validate-factors` | `factors/validation.py` | 冻结严格因子名单、模型资格manifest和两类简单基准 |
| `train` | `models/runner.py` | 运行Elastic Net或LightGBM的walk-forward预测 |
| `optimize` | `portfolio/runner.py` | 将预测变成约束组合并计入交易成本 |
| `report` | `reporting/runner.py` | 从已有结果生成离线Dashboard |
| `final-audit` | `validation/final_audit.py` | 做发布前的时点、约束、文件和哈希审计 |

`src/pb_roe/config.py`负责读取配置、验证必填部分、生成fingerprint以及确定`run_id`对应的输出目录。同一份配置应当产生同一个指纹，防止结果和配置错配。

## 4. Commit01–03：研究合同与数据层

### 4.1 五张canonical表是什么

`src/pb_roe/data/schema.py`定义字段和主键，`bundle.py`把它们装进一个`DataBundle`：

| 表 | 主要内容 | 为什么需要 |
|---|---|---|
| `security_master` | 股票代码、名称、上市日、行业快照 | 证券基础信息和上市时间过滤 |
| `trading_calendar` | 交易日 | 把理论信号日调整到可交易日 |
| `universe_membership` | 沪深300成员进入和退出区间 | 每个历史时点只使用当时成分股 |
| `prices` | 开高低收、复权、成交额、交易状态 | 因子、执行价、收益和风险矩阵 |
| `fundamentals` | 报告期、公告日、生效日、指标和值 | 在当时可见的财务数据中选最新一条 |

`data/store.py`负责Parquet读写和`manifest.json`哈希。大数据不提交Git，但manifest可以证明本次运行读的是哪一版输入。

### 4.2 数据从哪里来

- `data/providers/baostock.py`：行情、交易日和历史沪深300快照；
- `data/providers/akshare.py`：Eastmoney财务数据，保留首次公告日`NOTICE_DATE`；
- `data/providers/early_paper.py`：补充2005–2006原研报窗口的早期ROE；
- `data/providers/fixture.py`：只给smoke测试使用的小型确定性数据；
- `data/ingest_baostock.py`：统一调度Provider、缓存、标准化和落盘。

### 4.3 PIT是怎样避免未来数据的

核心代码在`data/pit.py`。对信号日`t`：

```text
股票可选条件：member_start <= t <= member_end
财务可见条件：effective_date <= t
最终取值：在可见记录中选effective_date最新的一条
```

因此，后来发布或后来修订的数据不能倒填到过去。`data/audit.py`再检查主键重复、OHLC关系、成员区间、公告滞后、因子覆盖率和manifest。

建议配合阅读：`tests/test_pit.py`、`tests/test_data_audit.py`、`tests/test_store.py`。

## 5. Commit04：原研报规则复现

入口是`reproduction/runner.py`，内部顺序是：

```text
读取并审计数据
  -> schedule.py生成4月、8月、10月信号和持有区间
  -> factors.py在信号日拼接可见PB与ROE并计算综合分
  -> strategies.py按原文规则形成多种组合
  -> backtest.py用信号日收盘进入、期末最后可见收盘退出
  -> 输出持仓、逐期收益和汇总
```

`factors.py`中的PB-ROE综合分是：

```text
ROE截面百分位 + (1 - PB截面百分位)
```

分数越高表示ROE较高且PB较低。这里是在还原原研报规则，不是机器学习。正式配置必须得到2005–2011共18个持有期；`final_audit.py`会硬性检查这一点。

主要输出在`results/runs/paper-reproduction/`，Git中的摘要在`docs/results/paper/`。建议配合阅读`tests/test_reproduction.py`。

## 6. Commit05：现代PB-ROE评价

入口是`evaluation/runner.py`。这一阶段的目标不是直接训练模型，而是回答BP、ROE和PB-ROE在现代沪深300中还有没有预测能力。

### 6.1 月度样本怎样形成

`evaluation/panel.py`在每个月末建立信号截面：

1. 只保留当月有效的历史沪深300成分；
2. 财务数据必须在信号日前已经公告；
3. 信号以后用下一次可交易开盘价进入，最多允许5个交易日执行延迟；
4. 下一持有期退出，得到下一月前瞻收益`forward_return`；
5. 处理ST、停牌、涨跌停、上市时间和成交额过滤。

`evaluation/preprocessing.py`按月做1%/99%缩尾，再做截面z-score。静态行业只允许做诊断版中性化，不进入正式历史标签。

### 6.2 指标怎样计算

- `evaluation/ic.py`：每月Spearman RankIC、IC均值、ICIR、Newey–West t值；
- `evaluation/quantiles.py`：五分组收益、单调性、换手和10/30/50bp成本；
- `evaluation/performance.py`：年化收益、波动、Sharpe和最大回撤；
- `evaluation/exposures.py`：暴露和容量诊断。

主要输出是`modern_factor_panel.parquet`以及IC、五分组、成本和暴露CSV。建议配合阅读`tests/test_evaluation.py`。

## 7. Commit06：12因子独立验证与模型输入资格

因子公式在`factors/library.py`，模型面板构造在`models/dataset.py`，统一验证在`factors/validation.py`。

第一层是严格独立有效性：

```text
2015–2022开发期
  -> 对12个候选逐一计算IC、NW t、年度稳定性、五分组单调性、30bp后价差
  -> 同时通过全部门槛的因子写入frozen_factor_selection.json
  -> 名单冻结后，才查看2023–2025原预留表现
```

正式门槛是开发期IC均值不低于2%、NW t不低于2、正IC年份占比不低于50%、五分组单调性不低于80%、30bp后多空价差为正。当前唯一通过者是`reversal_1m_z`，但它在原预留区间IC转负。

第二层在`factors/eligibility.py`：只检查PIT、覆盖率、数值变化、预设方向冲突和开发期冗余。11个原始因子合格，派生`paper_score_z`因与BP、ROE重复被排除。结果写入`model_factor_eligibility.csv`、`model_factor_correlations.csv`和`model_feature_manifest.json`。

`model_factor_panel.parquet`是Commit07唯一允许读取的模型输入；入口检查manifest的配置指纹、canonical输入哈希和特征顺序。`strict_factor_equal_weight_predictions.parquet`保存严格失败基准，`model_input_equal_weight_predictions.parquet`保存11因子简单等权基准。建议配合阅读`tests/test_factor_library.py`和`tests/test_factor_validation.py`。

## 8. Commit07：严格walk-forward模型

入口是`models/runner.py`。两个模型读取完全相同的11因子manifest：

- `models/linear.py`：Elastic Net线性基准；
- `models/lightgbm.py`：唯一树模型LightGBM。

对每一个预测月`t`，训练集只允许包含：

```text
signal_date < t
并且 label_exit_date <= t
```

第二个条件尤其重要。例如4月信号对应的收益要到5月退出后才实现，那么在5月退出以前不能拿这条收益训练。程序最多使用过去60个月，并要求至少24个月；LightGBM再把训练窗口最后12个月作为按时间排序的验证集做early stopping，不能随机打乱。

每个月重新拟合、预测当月横截面，最后把各月预测拼起来。输出包括：

```text
elastic-net_predictions.parquet
lightgbm_predictions.parquet
*_diagnostics.csv
*_ic_summary.csv
```

诊断文件记录每次训练实际使用的最晚标签退出日，最终审计会验证它早于或等于预测日。建议配合阅读`tests/test_linear_model.py`、`tests/test_lightgbm_model.py`和`tests/test_model_runner.py`。

## 9. Commit08：从预测到可交易组合

入口是`portfolio/runner.py`。这一步不再改变预测，只解决“怎样持仓”：

1. `portfolio/risk.py`用预测日前最多252个交易日收益估计协方差，并做Ledoit–Wolf收缩；
2. `portfolio/optimizer.py`解基准相对均值—方差问题；
3. 约束满仓、只做多、单票不超过3%、漂移后换手不超过30%；
4. 求解失败时使用确定性的排序回退，不悄悄丢掉该月；
5. 对严格反转、11因子等权、Elastic Net和LightGBM分别核算10/30/50bp成本，并与沪深300成分等权代理比较。

“漂移后换手”表示先让上期持仓随实际收益自然变化，再计算调仓差额；不是简单拿两期目标权重相减。输出包括目标持仓、组合月收益、汇总绩效和求解诊断。建议配合阅读`tests/test_portfolio.py`。

## 10. Commit09–10：报告、图片与发布审计

### 10.1 报告和图片

- `reporting/dashboard.py`：从运行结果生成可断网打开的Plotly HTML；
- `scripts/freeze_results.py`：最终审计通过后，把正式摘要复制到`docs/results/`并记录配置、输入和文件哈希；
- `scripts/plot_*.py`：只读冻结结果，用Matplotlib生成论文和展示图片；
- `docs/presentation_en_10min.html`：英文10分钟展示页，只引用`docs/results/figures/presentation-en/`中的PNG；
- `scripts/build_standalone_presentation.py`：把上述PNG嵌入可直接发送的单文件HTML；
- `docs/presentation_script_en_10min.md`：逐页英文讲稿。

画图不重新下载、不训练、不优化。如果图不对，应先判断是绘图脚本问题还是上游结果问题，不能靠手工修改图片掩盖结果。

### 10.2 最终审计

`validation/final_audit.py`是发布开关，主要检查：

- 原研报复现是2005–2011完整18期；
- canonical manifest、配置指纹和ROE公告滞后有效；
- 收益退出价在当时可观察；
- 静态行业没有进入正式历史目标和组合约束；
- 模型训练标签在预测时已经实现；
- 模型manifest与canonical数据哈希一致、派生PB-ROE未重复输入、两模型特征完全相同；
- 组合满仓、非负、单票上限和换手上限成立；
- Dashboard不依赖外部CDN；
- 严格反转的2023–2025预留检验与新版模型探索性历史检验标签没有混淆；
- 正式结果文件生成SHA-256清单。

任何一项失败，都不应执行`freeze_results.py`或更新最终展示。

## 11. 跟着一条数据走

理解工程最有效的方法，是任选一只股票和一个月，追踪这些字段：

```text
fundamentals.parquet
  report_period / announce_date / effective_date / metric / value
        |
        | effective_date <= signal_date
        v
modern_factor_panel.parquet
  signal_date / security_id / BP / ROE / PB-ROE / entry_date / exit_date / forward_return
        |
        | 因子扩展、月度缩尾和z-score
        v
model_factor_panel.parquet + model_feature_manifest.json
  *_z / target_return / label_exit_date / sample_segment
        |
        | 只用已实现历史标签逐月拟合
        v
*_predictions.parquet
  prediction / train_end_date / train_label_exit_max
        |
        | 风险矩阵与组合约束
        v
*_holdings.parquet + *_portfolio_returns.csv
  target_weight / pretrade_weight / turnover / gross_return / net_return
```

调试时只打印这一只股票、这一个月，比反复重跑全量流程更容易发现时点或口径错误。

## 12. 怎样实际学习和调试这个工程

### 第一次：只看流程，不跑全量

```bash
.venv/bin/python -m pb_roe --help
.venv/bin/python -m pb_roe config-check --config configs/modern.yaml
./scripts/run_smoke.sh
```

smoke fixture是测试数据，只验证接口和时点约束，不代表研究结果。

### 第二次：从测试反推规则

```bash
.venv/bin/python -m pytest tests/test_pit.py -q
.venv/bin/python -m pytest tests/test_reproduction.py -q
.venv/bin/python -m pytest tests/test_factor_validation.py -q
.venv/bin/python -m pytest tests/test_model_runner.py -q
.venv/bin/python -m pytest tests/test_portfolio.py -q
```

每读完一个runner，就读对应测试，并尝试解释每个断言在防止哪种研究偏差。

### 第三次：检查已有正式结果，不重复训练

```bash
column -s, -t < docs/results/models/model_ic_comparison.csv
column -s, -t < docs/results/portfolio/portfolio_summary.csv
.venv/bin/python -m json.tool docs/results/final_audit_summary.json
```

图片和HTML都只读这些冻结结果。完整重跑命令集中在`docs/runbook.md`，只有数据或研究逻辑改变时才需要执行。

## 13. 当前结论应怎样从代码中得到

工程的逻辑结论不是“模型越复杂越好”，而是逐层检验：

```text
原研报规则能否在可得免费数据上复现？
  -> 现代PB-ROE是否仍有稳定预测力？
  -> 12个候选中哪些能独立通过统一门槛？
  -> 哪些基础因子具备模型输入资格？
  -> 严格反转到2023–2025是否仍有效？
  -> 11因子等权、Elastic Net或LightGBM谁更稳定？
  -> 计入风险、换手和成本后能否超过基准？
```

当前答案是：原研报方向和量级得到基本复现，但行业版本不一致；现代候选只有1个月反转能独立通过，且原预留检验失效；11个原始因子通过模型资格，简单方向等权在2023–2025探索区间优于基准；Elastic Net与LightGBM都没有击败简单等权。因而工程既保留严格负结果，也把多因子分散的正结果正确降级为待未来验证的探索性证据。
