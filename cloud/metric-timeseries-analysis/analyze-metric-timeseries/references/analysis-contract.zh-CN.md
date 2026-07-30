# 指标时序分析契约

这个 skill 是服务类 skill 可复用的通用能力。它把 CES 获取、dataset 持久化和缓存行为隐藏在一次紧凑的脚本调用后面。

通过 CLI 的 `--args` 参数直接传入 `MetricAnalysisSpec` JSON 对象字符串。`--args` 不是文件路径，调用方不创建临时 spec 文件。

CLI 输入：

```bash
python3 scripts/analyze_metric_timeseries.py \
  analyze --args '<MetricAnalysisSpec JSON>'
```

CLI 输出严格为一个紧凑 JSON 对象：分析完成时返回 `AnalysisResult`，失败时返回本文后面定义的错误对象。

上面的 CLI 是公开执行边界。调用方不得导入内部实现模块，也不得直接调用 profile 类。调用前必须从用户输入或可信 tool 结果中取得全部必填字段；存在无法确定的必填字段时，一次性向用户询问所有缺失字段，在用户提供前不得调用 CLI。

## 边界

服务类 skill 可见：

```text
MetricAnalysisSpec -> AnalysisResult
```

服务类 skill 不可见：

```text
CES 原始 API 响应
原始数据点
DatasetStore 实现
cache index
terminal 输出截断细节
```

## MetricAnalysisSpec

`time_window.from` 和 `time_window.to` 是 CLI 技术字段，不是面向用户的输入。调用方 skill 接收自然语言时间范围，并在构造该对象前将其解析为整数毫秒时间戳。

必填字段：

```text
region
project_id
metric.namespace
metric.metric_name
metric.dimensions
time_window.from
time_window.to
period
analysis.profile
```

可选字段：

```text
analysis profile options
```

调用方不传聚合方式，内部固定使用 CES `average` 聚合。

`metric.dimensions[].name` 不是固定值。必须使用目标 CES 指标文档定义的维度 key；只有当该指标定义维度名为 `instance_id` 时，才填写 `instance_id`。

脚本会在拉数前校验 CES 字段约束：`project_id` 长度为 1 到 64，时间戳处于 CES 毫秒范围内，namespace 和指标名称符合 CES 格式，每个指标包含 1 到 4 个维度。profile 参数同样采用严格校验：未知参数、错误 JSON 类型、非法枚举值和不一致的窗口参数都会被拒绝。

profile 参数可以直接用内置 CLI 查询：

```bash
python3 scripts/analyze_metric_timeseries.py profiles
python3 scripts/analyze_metric_timeseries.py profile <profile-name>
python3 scripts/analyze_metric_timeseries.py profile <profile-name> --help
```

`profile <profile-name>` 会输出 JSON，包含参数名、类型、默认值、可选值，以及可复制到 `MetricAnalysisSpec.analysis` 的 `example_analysis`。

各 profile 参数：

| Profile | 参数 |
| --- | --- |
| `sliding_window_threshold_frequency_detection` | `threshold` 必填；`direction`、`window_points`、`min_frequency` 可选。 |
| `spike_drop_detection` | `box_scale`、`direction`、`window_size`、`residual_sen` 和 `nonzero` 可选，默认值依次为 `3`、`up`、`3600`、`10` 和 `false`。 |
| `median_p75_statistics` | `smoothing_time` 可选，单位秒，必须是正整数，默认 `900`。 |
| `rising_trend_detection` | 无额外参数。 |
| `trend_prediction` | 无额外参数；要求指标历史数据跨度至少七天。 |

`median_p75_statistics` 根据 `ceil(smoothing_time / effective_period)` 计算奇数中值平滑窗口，在序列两端补零，对平滑后的序列计算中位数和 p75。`period = 1` 时，有效时间粒度按 60 秒计算。

`spike_drop_detection` 的 `window_size` 是平滑时长，单位秒。脚本先执行复制边界的均值平滑；当残差波动范围小于 `residual_sen` 时跳过异常检测。随后执行复制边界的中值平滑，分别对原序列与平滑序列的残差、平滑趋势的一阶差分进行箱线图异常检测。`direction` 可选 `up`、`down` 或 `all`；`box_scale` 控制 IQR 上下界；`nonzero=true` 表示估计上下界时排除零值。

`rising_trend_detection` 使用 `np.diff` 计算相邻数据点差值，并分别统计正差值和负差值数量。正差值更多时返回 `judge=true` 和上升趋势；负差值更多时返回下降趋势；数量相等时返回无明显趋势。零差值不参与方向大小比较。该 profile 不预测未来值。

它的 finding evidence 结构如下：

```json
{
  "kind": "rising_trend",
  "severity": "warning",
  "metric_name": "cpu_util",
  "confidence": 1.0,
  "evidence": {
    "judge": true,
    "trend": "upward",
    "increasing_count": 3,
    "decreasing_count": 1,
    "unchanged_count": 0,
    "comparison_count": 4
  }
}
```

`trend_prediction` 先将时间戳向下取整到小时，并对同一小时的值求平均；去除时区后使用 `Prophet(growth="linear", changepoint_range=0.9)` 拟合。模型通过 `include_history=false` 预测未来 168 个小时值。168 个派生预测点只在内部使用；`forecast` 和 finding evidence 只返回起止时间、首个/末个/最小/最大/平均预测值、总变化量、变化比例和方向。

## AnalysisResult

`AnalysisResult` 是脚本打印的紧凑 JSON 对象。服务类 skill 只应该消费这个对象作为指标证据。

成功结果的必备结构：

```json
{
  "success": true,
  "metric_name": "cpu_util",
  "profile": "trend_prediction",
  "summary": "Forecasted the next seven days with Prophet.",
  "findings": []
}
```

`findings` 始终是数组。事件检测类 profile 检测到事件时返回结构化记录，未检测到时返回空数组；统计和趋势类 profile 返回对应的结构化摘要记录。

可选字段：

```text
statistics             当前请求指标的紧凑统计结果。
forecast               当前请求指标的紧凑预测结果。
```

`trend_prediction.forecast` 字段：

```text
forecast_hours          固定为 168。
start_time              第一个预测点的毫秒时间戳。
end_time                最后一个预测点的毫秒时间戳。
first_predicted_value   第一个小时的 Prophet yhat。
last_predicted_value    最后一个小时的 Prophet yhat。
min_predicted_value     168 小时 yhat 最小值。
max_predicted_value     168 小时 yhat 最大值。
mean_predicted_value    168 小时 yhat 平均值。
change                  末个预测值减首个预测值。
change_ratio            change / abs(first_predicted_value)；首个预测值为零时返回 null。
direction               upward、downward 或 flat。
```

`median_p75_statistics` 返回：

```json
{
  "success": true,
  "metric_name": "cpu_util",
  "profile": "median_p75_statistics",
  "summary": "Computed median and p75 statistics for the requested metric.",
  "findings": [
    {
      "kind": "distribution_summary",
      "severity": "info",
      "metric_name": "cpu_util",
      "confidence": 1.0,
      "evidence": {
        "count": 4,
        "min": 10.0,
        "max": 40.0,
        "median": 25.0,
        "p75": 30.0
      }
    }
  ],
  "statistics": {
    "count": 4,
    "min": 10.0,
    "max": 40.0,
    "median": 25.0,
    "p75": 30.0
  }
}
```

该 profile 中，`count`、`min`、`max`描述有效输入序列；`median`、`p75`基于两端补零并进行中值平滑后的序列计算。

成功结果采用 LLM 可见字段白名单。`AnalysisResult` 不能包含原始数据点、`analysis_id`、`dataset_ref`、缓存状态、文件路径、hash、字节数，也不能包含内部 `statistics_by_metric` / `forecast_by_metric` 映射。运维和缓存元数据只保留在内部日志、DatasetStore 和 cache index。

## CES 查询限制

脚本会强制执行华为云 CES 批量查询指标数据接口限制：

```text
metrics_count <= 500
metrics_count * (to - from) / period <= 3000
序列化后的 CES 请求体 <= 512KB
```

当 `period = 1` 时，脚本遵循 CES API 行为，在该限制计算中将有效周期视为 60 秒。

## 缓存

脚本缓存 CES 时序 dataset，不缓存分析结果。

缓存 key：

```text
sha256(canonical normalized CES query)
```

纳入 key 的内容：

```text
project_id
region
namespace
metric name
CES MetricInfo 的 `{name, value}` 数组形式 dimensions
from/to
period
内部聚合方式（固定为 `average`）
normalization version
backend version
```

不纳入 key 的内容：

```text
用户自然语言
skill name
analysis profile
analysis options
dataset path
trace id
```

淘汰触发时机：

```text
1. cache get 时进行惰性淘汰：当 TTL、index、dataset path 或 sha256 校验失败时淘汰。
2. cache put 时进行容量淘汰：当 max bytes 或 max entries 超限时触发。先删除过期 entry，再删除 LRU entry。
```

缓存策略由服务统一管理，`MetricAnalysisSpec` 不能覆盖。容量统计包含每个 dataset 的全部持久化文件。同一 cache key 使用文件系统锁合并并发 miss：一个调用负责拉取 CES，其余调用复用写入后的 dataset。

默认缓存根目录：

```text
${HERMES_HOME:-$HOME/.hermes}/datasets/metric-analysis
```

## 错误契约

`query_too_large` 表示 CES 请求超过 API 数据点限制。

`data_fetch_failed` 表示内部 MCP CLI adapter 或后端命令执行失败。

`invalid_request` 表示 `MetricAnalysisSpec` 缺少必填字段或包含不支持的值。

`internal_error` 使用固定通用消息，不向 LLM 暴露异常类型、路径或后端细节。

所有错误都以紧凑 JSON 返回：

```json
{
  "success": false,
  "error": "query_too_large",
  "message": "metrics_count * (to - from) / period exceeds 3000"
}
```
