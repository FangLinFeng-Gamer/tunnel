---
name: analyze-metric-timeseries
description: 分析数据库和云服务诊断中的云监控指标时序数据，包括滑动窗口阈值频次、突增/突降异常、中位数与 p75 基线、相邻点方向计数上升趋势和趋势预测。适用于诊断流程需要基于 CES 或类似监控数据生成指标证据，且不应将原始数据点放入模型上下文的场景。
---

# 分析指标时序数据

当服务诊断流程需要对监控指标时序数据做紧凑分析时使用这个 skill。通过内置脚本传入 `MetricAnalysisSpec`，并使用返回的 `AnalysisResult` 作为诊断证据。

调用方传入紧凑的 `MetricAnalysisSpec`，不要传入原始数据点。内置脚本负责获取、缓存、规范化并分析指标时序数据，最终打印紧凑的 JSON `AnalysisResult`。

构造 CLI 输入或解释 CLI 输出前，必须阅读 [references/analysis-contract.zh-CN.md](references/analysis-contract.zh-CN.md)。其中定义了完整的 `MetricAnalysisSpec`、profile 参数、`AnalysisResult` 和错误 JSON 契约。

## 脚本

运行：

```bash
python skills/metric-timeseries-analysis/analyze-metric-timeseries/scripts/analyze_metric_timeseries.py \
  analyze --args '{"region":"cn-north-4","project_id":"project-xxx","metric":{"namespace":"SYS.RDS","metric_name":"cpu_util","dimensions":[{"name":"instance_id","value":"rds-xxx"}]},"time_window":{"from":1784160000000,"to":1784764800000},"period":3600,"analysis":{"profile":"trend_prediction"}}'
```

`--args` 接收 `MetricAnalysisSpec` JSON 对象字符串，不是文件路径。调用方 skill 将对象序列化为紧凑 JSON 后直接传入，不需要创建临时 spec 文件。

CES 获取是内置脚本的内部实现。不要把 MCP CLI 命令、CES 原始查询或原始数据点放进 `MetricAnalysisSpec`。

不要凭记忆猜 profile 参数，直接用 CLI 查看：

```bash
python skills/metric-timeseries-analysis/analyze-metric-timeseries/scripts/analyze_metric_timeseries.py profiles
python skills/metric-timeseries-analysis/analyze-metric-timeseries/scripts/analyze_metric_timeseries.py profile trend_prediction
python skills/metric-timeseries-analysis/analyze-metric-timeseries/scripts/analyze_metric_timeseries.py profile sliding_window_threshold_frequency_detection --help
```

## MetricAnalysisSpec

```json
{
  "region": "cn-north-4",
  "project_id": "project-xxx",
  "metric": {
    "namespace": "SYS.RDS",
    "metric_name": "cpu_util",
    "dimensions": [
      {
        "name": "instance_id",
        "value": "rds-xxx"
      }
    ]
  },
  "time_window": {
    "from": 1784200000000,
    "to": 1784210000000
  },
  "period": 300,
  "analysis": {
    "profile": "rising_trend_detection"
  }
}
```

调用方不传 CES 聚合方式。脚本固定查询并读取 `average` 值。

`metric.dimensions` 按华为云 CES `MetricInfo.dimensions` 结构填写：数组，每个元素是 `{ "name": "...", "value": "..." }`。`dimensions[].name` 必须填写目标 CES 指标要求的维度 key。上面示例里的 `instance_id` 只是示例，只有当该指标的 CES 文档定义维度名为 `instance_id` 时才可以这样填。

脚本会校验 CES 字段限制，并拒绝 profile 未声明的参数、错误 JSON 类型及违反参数约束的值。缓存策略是内部服务配置，不属于 `MetricAnalysisSpec`。

`analysis.profile` 是必填字段。按下表选择 profile：

| Profile | 适用场景 | 关键参数 |
| --- | --- | --- |
| `sliding_window_threshold_frequency_detection` | 统计滑动窗口内指标越过阈值的频次。适用于“CPU 有多少窗口持续高于 80%”这类判断。 | `threshold` 必填；`direction` 为 `above` 或 `below`；`window_points`；`min_frequency`。 |
| `spike_drop_detection` | 过滤正常小波动后，检测残差或平滑趋势中的突增、突降箱线图异常。适用于异常突变证据。 | 可选 `box_scale`、`direction`、`window_size`、`residual_sen` 和 `nonzero`。 |
| `median_p75_statistics` | 对序列进行中值平滑后计算分布基线。适用于需要中位数和 p75 的诊断判断。 | `smoothing_time` 可选，单位秒，默认 900 秒。 |
| `rising_trend_detection` | 比较相邻数据点的上升和下降次数。适用于需要上升、下降或无明显方向证据的场景。 | 无额外参数。 |
| `trend_prediction` | 使用至少七天历史数据，通过 Prophet 预测未来 168 个小时值。 | 无额外参数。 |

对于 `sliding_window_threshold_frequency_detection`，需要包含：

```json
{
  "analysis": {
    "profile": "sliding_window_threshold_frequency_detection",
    "threshold": 80,
    "direction": "above",
    "window_points": 5,
    "min_frequency": 3
  }
}
```

## 结果契约

脚本只打印紧凑 JSON，不能打印原始数据点。

```json
{
  "success": true,
  "metric_name": "cpu_util",
  "profile": "trend_prediction",
  "summary": "Forecasted the next seven days with Prophet.",
  "findings": [
    {
      "kind": "upward_trend",
      "severity": "warning",
      "metric_name": "cpu_util",
      "confidence": 1.0,
      "evidence": {
        "forecast_hours": 168,
        "start_time": 1784768400000,
        "end_time": 1785369600000,
        "first_predicted_value": 40.2,
        "last_predicted_value": 53.8,
        "min_predicted_value": 39.5,
        "max_predicted_value": 56.1,
        "mean_predicted_value": 47.3,
        "change": 13.6,
        "change_ratio": 0.3383,
        "direction": "upward"
      }
    }
  ],
  "forecast": {
    "forecast_hours": 168,
    "start_time": 1784768400000,
    "end_time": 1785369600000,
    "first_predicted_value": 40.2,
    "last_predicted_value": 53.8,
    "min_predicted_value": 39.5,
    "max_predicted_value": 56.1,
    "mean_predicted_value": 47.3,
    "change": 13.6,
    "change_ratio": 0.3383,
    "direction": "upward"
  }
}
```

## 服务类 Skill 使用规则

- 只有在需要时序判断时才调用这个 skill/script。
- 服务类 skill 不要直接调用 CES 原始 API。
- 不要在 prompt、tool result 或最终回答中包含原始数据点。
- 使用脚本输出中的 `summary`、`findings`，以及可选的 `statistics` 或 `forecast` 作为证据。
- 如果脚本返回 `data_fetch_failed`，停止并说明当前环境中的内部 CES MCP CLI adapter 执行失败。
- 如果脚本返回 `query_too_large`，缩小时间范围、增大 `period`，或按指标/时间拆分请求。

完整 `MetricAnalysisSpec`、`AnalysisResult`、缓存行为和错误契约见 [references/analysis-contract.zh-CN.md](references/analysis-contract.zh-CN.md)。英文原版见 [references/analysis-contract.md](references/analysis-contract.md)。
