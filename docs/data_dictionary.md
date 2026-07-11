# 数据字典

所有日期使用 ISO `YYYY-MM-DD`，股票代码使用带交易所后缀的 canonical code，例如 `600000.SH`、`000001.SZ`。

## security_master

| 字段 | 类型 | 说明 |
|---|---|---|
| security_id | string | canonical 股票代码，主键 |
| exchange | string | `SH` / `SZ` / `BJ` |
| symbol | string | 六位数字代码 |
| name | string | 当前或记录时点简称 |
| list_date | date | 上市日期 |
| delist_date | date/null | 退市日期 |
| source | string | 数据来源 |

## trading_calendar

| 字段 | 类型 | 说明 |
|---|---|---|
| trade_date | date | 交易日期，主键 |
| is_open | bool | 是否开市 |
| previous_open_date | date/null | 上一交易日 |
| next_open_date | date/null | 下一交易日 |

## universe_membership

| 字段 | 类型 | 说明 |
|---|---|---|
| universe_id | string | 如 `CSI300` |
| security_id | string | 股票代码 |
| member_from | date | 纳入生效日，包含 |
| member_to | date/null | 调出生效日，不包含；空值表示仍有效 |
| weight | float/null | 可用时保存指数权重 |
| industry | string/null | 该记录对应的行业分类 |
| source | string | 来源 |

主键：`universe_id, security_id, member_from`。

## prices

| 字段 | 类型 | 说明 |
|---|---|---|
| trade_date | date | 交易日 |
| security_id | string | 股票代码 |
| open/high/low/close | float | 未复权价格 |
| volume | float | 成交量 |
| amount | float/null | 成交额 |
| adjustment_factor | float/null | 复权因子 |
| is_suspended | bool | 是否停牌 |
| is_st | bool | 是否 ST |
| limit_status | string | `none/up/down/unknown` |
| source | string | 来源 |

主键：`trade_date, security_id, source`。

## fundamentals

| 字段 | 类型 | 说明 |
|---|---|---|
| security_id | string | 股票代码 |
| report_period | date | 报告期末 |
| announce_date | date | 首次公告日 |
| revision_date | date/null | 更正公告日 |
| effective_date | date | 本记录可使用日期 |
| metric | string | 标准化指标名 |
| value | float/null | 数值 |
| unit | string | 单位 |
| statement_type | string | 合并/母公司、单季/累计等 |
| source | string | 来源 |

主键：`security_id, report_period, effective_date, metric, source`。

## factor_panel

| 字段 | 类型 | 说明 |
|---|---|---|
| signal_date | date | 信号日期 |
| security_id | string | 股票代码 |
| factor | string | 因子名 |
| raw_value | float/null | 原始因子值 |
| processed_value | float/null | 去极值、标准化后数值 |
| source_report_period | date/null | 来源财报期 |
| source_effective_date | date/null | 来源记录生效日 |

主键：`signal_date, security_id, factor`。

## portfolio_returns

| 字段 | 类型 | 说明 |
|---|---|---|
| strategy_id | string | 实验编号 |
| rebalance_date | date | 调仓日 |
| period_end | date | 持有期结束 |
| gross_return | float | 成本前收益 |
| transaction_cost | float | 交易成本 |
| net_return | float | 成本后收益 |
| turnover | float | 单边换手 |
| benchmark_return | float/null | 基准收益 |

## audit_results

| 字段 | 类型 | 说明 |
|---|---|---|
| check_id | string | 检查编号 |
| table_name | string | 被检查表 |
| severity | string | `info/warn/error` |
| passed | bool | 是否通过 |
| observed | float/string/null | 实际值 |
| threshold | float/string/null | 阈值 |
| details | string/null | 详细说明 |

