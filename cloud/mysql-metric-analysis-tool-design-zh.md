# MySQL 故障诊断 Skill 编排与分析能力迁移设计

## 1. 文档定位

本文描述原 MySQL 故障诊断能力迁移到 Hermes 后的功能边界和 Skill 编排方式，重点回答：

- 哪些能力迁移到 Hermes。
- 哪些能力继续复用 DAS、RDS 或原服务。
- MySQL Skill 如何组织诊断流程。
- 通用时序分析能力如何被 MySQL 和其他数据库服务复用。

CES 数据获取、缓存、DatasetStore、分析算法和 CLI 的内部实现统一由
[CES 时序数据与通用分析能力设计](./ces-timeseries-analysis-design-zh.md)定义，本文不重复描述。

## 2. 需求背景

原 MySQL 故障诊断由一套 Python 代码实现，内部同时包含诊断流程、服务查询和数据分析逻辑。迁移到 Hermes 时，不整体迁移原诊断服务，只迁移其中可以跨数据库服务复用的数据分析能力。

迁移后的职责划分如下：

- MySQL Skill 承载诊断流程和能力选择规则。
- DAS、RDS 已提供的能力直接复用。
- DAS、RDS 未提供的确定性查询能力由原服务开放接口并注册到 MCP。
- 数据库内部状态优先使用 Hermes 插件的 `query_sql` tool 查询。
- 原 Python 代码中的通用时序分析逻辑迁移到 `metric-timeseries-analysis` Skill。
- CES 拉数、时序数据落盘、缓存和算法执行全部封装在通用分析能力内部。

这个划分解决两个问题：

1. 避免将 MySQL 专属诊断流程和通用数值分析耦合在一起。
2. 避免 LLM 通过 terminal 或多个 tool 搬运大段时序数据。

## 3. 目标与边界

### 3.1 目标

- 通过 Skill 编排恢复原服务类似的 MySQL 故障诊断能力。
- 只迁移滑动窗口、异常检测、统计和趋势预测等通用分析逻辑。
- 优先复用 DAS、RDS 和 `query_sql`，避免重复建设。
- 让 MySQL、PostgreSQL、Redis 等 service-category 复用同一套时序分析能力。
- 让 Hermes Agent 和其他引擎都可以按稳定的 Skill 和分析合约进行编排。
- 向 LLM 返回小体积、结构化的诊断证据。

### 3.2 非目标

- 不迁移完整的 `MysqlDiagnosisEngine`。
- 不提供单体 `mysql_diagnose` tool 作为当前迁移前提。
- 不在 Skill 中实现数值算法。
- 不让 Skill 构造 CES 原始请求、管理 DatasetStore 或处理缓存。
- 不让 LLM 接收、复制或传递完整时序数据。
- 不重复实现 DAS、RDS 已经提供的能力。

## 4. 功能方案

### 4.1 整体方案设计

```text
用户或外部引擎
      |
      v
Hermes Agent
      |
      | 触发 MySQL service-category Skill
      v
MySQL 故障诊断编排
      |
      +-------------------+-------------------+------------------+
      |                   |                   |                  |
      v                   v                   v                  v
  DAS tools           RDS tools        原服务 MCP tools     query_sql
      |                   |                   |                  |
      +-------------------+-------------------+------------------+
                              |
                              | 需要时序判断时
                              v
                    通用时序分析能力
                              |
                              v
                       AnalysisResult
                              |
                              v
              汇总根因、证据、置信度和建议
```

MySQL Skill 只编排诊断语义能力。CES、MCP CLI、原始 datapoints、缓存和文件存储均位于通用分析能力内部，对 MySQL Skill 透明。

### 4.2 功能分层

| 层级 | 主要职责 | 对下层的依赖 |
| --- | --- | --- |
| MySQL service-category | 定义 MySQL 诊断场景、边界和 Skill 列表 | 各诊断 Skill |
| MySQL 诊断 Skill | 识别故障场景、编排证据、汇总结论 | DAS、RDS、MCP、`query_sql`、通用分析 |
| 诊断证据 tool | 返回实例、SQL、参数、事件、复制等确定性证据 | 对应服务接口 |
| 通用时序分析能力 | 返回趋势、异常、基线和预测结果 | 内部 CES 获取与分析实现 |

分层原则：

- Skill 负责“何时调用什么能力”，tool 负责“确定性查询”，分析模块负责“数值计算”。
- Skill 和外部引擎只消费小体积 `ToolResult` 或 `AnalysisResult`。
- 通用能力的实现变化不应要求修改 MySQL Skill。

### 4.3 诊断流程

标准 MySQL 故障诊断流程如下：

```text
1. 识别故障现象、实例、节点和时间窗口。
2. 调用 DAS/RDS tool 获取服务原生证据。
3. 调用 query_sql 获取目标节点上可由 SQL 观测的状态。
4. 对 DAS/RDS/query_sql 无法提供的证据，调用原服务 MCP tool。
5. 需要趋势、异常、阈值频次、基线或预测时，调用通用时序分析能力。
6. 对所有 ToolResult 和 AnalysisResult 做关联判断。
7. 输出根因候选、证据链、置信度、影响和处理建议。
```

任何步骤都不向 LLM 返回完整监控时序、全量日志或大批 SQL 样本。大体积证据应由能力内部保存，并只返回摘要或 artifact 引用。

### 4.4 能力来源与迁移范围

#### 4.4.1 迁移到通用时序分析能力

| Profile | 原能力 | 典型用途 |
| --- | --- | --- |
| `sliding_window_threshold_frequency_detection` | 滑动窗口阈值频次检测 | 判断 CPU、连接数等指标在连续窗口内越过阈值的频次 |
| `spike_drop_detection` | 异常突增或突降检测 | 识别连接数、QPS、延迟等指标的突变 |
| `median_p75_statistics` | 中位数和 p75 分位数 | 构建正常基线或比较故障窗口 |
| `continuous_rising_prediction` | 持续上升预测 | 判断内存、磁盘、连接数等持续增长风险 |
| `trend_prediction` | 趋势预测 | 判断指标整体上升、下降或平稳趋势 |

Profile 参数和执行细节只在通用分析设计及 Skill CLI 帮助中维护，MySQL 文档不再复制。

#### 4.4.2 由原服务新增 MCP 接口

当前明确需要补齐的能力：

| 能力 | 用途 | 接口状态 |
| --- | --- | --- |
| MySQL 实例共享型/独享型查询 | 判断实例架构和资源隔离方式 | 由原服务开放接口并注册 MCP；tool 名称待服务注册后确定 |
| 数据库非标参数查询 | 识别偏离标准配置的参数 | 由原服务开放接口并注册 MCP；tool 名称待服务注册后确定 |

设计文档只定义能力，不在真实注册前虚构 MCP tool 名称。

#### 4.4.3 优先使用 `query_sql`

| 能力 | 可行性 | 约束 |
| --- | --- | --- |
| 是否使用内存表 | 可通过 SQL 查询 | 取决于账号权限和可访问 schema |
| 是否开启 `performance_schema` | 可通过系统变量查询 | 查询结果仅代表当前连接节点 |
| 主从复制是否异常 | 可查询 master 可见的复制状态 | 是否覆盖所有云服务诊断场景需结合 RDS/DAS 能力验证 |
| slave 是否开启 query cache | master 连接无法可靠代表 slave | 必须连接目标 slave，或改用 RDS/DAS/原服务 MCP 接口 |

`query_sql` 只能描述实际连接节点可见的状态。Skill 不得把 master 的查询结果当成 slave 节点配置。

#### 4.4.4 复用 DAS/RDS

以下类型能力优先从 DAS/RDS 获取：

- 实例状态、规格、容量和拓扑。
- 慢 SQL、Top SQL、SQL 画像和优化建议。
- 会话、连接和锁等待。
- 告警、事件、参数变更和操作记录。
- 备份、恢复和服务侧诊断结果。

若 DAS/RDS 已存在等价能力，原服务不再重复开放接口。

### 4.5 Skill 组织方式

MySQL service-category 使用以下目录：

```text
skills/
  mysql/
    DESCRIPTION.md
    <skill-name>/
      SKILL.md
      scripts/
      references/
```

`DESCRIPTION.md` 描述整个 MySQL category 能做什么、何时使用以及能力边界。每个 `<skill-name>/SKILL.md` 只描述一个诊断场景，例如 CPU 异常、连接数突增、慢 SQL 或复制异常。

单个 Skill 应包含：

- 触发条件和适用范围。
- 需要收集的上下文。
- DAS/RDS/MCP/`query_sql`/通用分析能力的选择顺序。
- 证据不足时的降级策略。
- 诊断结论必须包含的字段。

单个 Skill 不应包含：

- CES API 或 MCP CLI 命令。
- DatasetStore、cache key、TTL 或淘汰策略。
- 原始 datapoints 搬运步骤。
- 通用分析算法实现。

需要时序分析时，Skill 调用：

```bash
python skills/metric-timeseries-analysis/analyze-metric-timeseries/scripts/analyze_metric_timeseries.py \
  analyze --args '<MetricAnalysisSpec JSON>'
```

`--args` 后面是序列化后的 `MetricAnalysisSpec` JSON 对象字符串，不是文件路径。MySQL Skill 直接构造紧凑 JSON 并调用，不创建临时 spec 文件。

`MetricAnalysisSpec` 和 `AnalysisResult` 的唯一合约定义见通用分析 Skill 的
`references/analysis-contract.zh-CN.md`。

### 4.6 外部引擎复用

其他引擎可以采用两种方式：

1. 加载 MySQL Skill，复用完整故障诊断流程。
2. 直接调用通用时序分析能力，只获得某个指标的分析结果。

外部引擎依赖的是 Skill、诊断 tool 合约和 `MetricAnalysisSpec -> AnalysisResult` 合约，不依赖 Hermes 内部 Python 类、DatasetStore 路径或 CES tool 名称。

## 5. 详细功能设计

### 5.1 Skill 输入

诊断开始前至少确定：

- 数据库服务和实例标识。
- region、project 等服务定位信息。
- 故障现象和目标节点。
- 故障时间窗口；无法确定时由 Skill 引导用户补齐或选择合理默认窗口。
- 用户关心的影响，例如性能、连接、容量或可用性。

Skill 只把各能力所需的小体积参数传给对应 tool，不构造一个包含所有字段的超大通用请求。

### 5.2 证据选择规则

```text
服务控制面和服务诊断证据  -> DAS/RDS
数据库当前节点内部状态    -> query_sql
DAS/RDS 缺失的原服务能力  -> 原服务 MCP tool
趋势、异常、基线和预测    -> 通用时序分析能力
```

同一结论尽量由至少两个独立证据支持。例如 CPU 升高可以同时结合时序趋势、Top SQL、连接数和近期变更，而不是只依赖单个指标。

### 5.3 常见场景编排

| 场景 | 优先证据 | 可选时序分析 |
| --- | --- | --- |
| CPU 异常 | Top SQL、会话、实例事件、参数变更 | 阈值频次、突增检测、中位数/p75、趋势预测 |
| 连接数突增 | 会话、连接来源、应用变更、最大连接参数 | 突增检测、阈值频次、趋势预测 |
| 内存增长 | 内存表、buffer 配置、会话、实例规格 | 持续上升预测、中位数/p75 |
| 慢 SQL | DAS 慢 SQL、SQL 画像、执行计划 | 延迟指标突增、趋势和基线 |
| 主从复制异常 | RDS/DAS 复制状态、目标节点 SQL 状态、事件 | 延迟指标趋势和突增检测 |

该表只约束能力选择，不把每个场景固定成不可调整的线性流程。Skill 应根据已获得证据跳过无关步骤。

### 5.4 诊断结果

最终结果至少包含：

```text
summary             故障结论摘要
root_causes         按置信度排序的根因候选
evidence            支撑结论的 ToolResult / AnalysisResult 摘要
impact              已确认或可能影响
recommendations     处理建议及优先级
limitations         缺失证据、权限或节点可达性限制
```

不得把完整 datapoints、全量日志或未经脱敏的 SQL 文本放入最终回答。

### 5.5 错误与降级

- 单个非关键 tool 失败时，记录限制并继续收集其他证据。
- 关键证据缺失且无法形成可靠结论时，明确说明无法确认根因。
- 通用分析返回 `query_too_large` 时，缩短时间窗口或增大 period 后重试。
- 通用分析返回 `data_fetch_failed` 时，保留其他证据并说明监控数据不可用。
- `query_sql` 无权限或无法连接目标节点时，改用 DAS/RDS 或原服务 MCP 接口。
- 不因缓存 miss 或缓存写入失败改变 Skill 对外行为。

## 6. 具体实现细节

### 6.1 MySQL Skill 的实现边界

本设计在 Hermes 中只新增或维护以下类型文件：

```text
skills/mysql/DESCRIPTION.md
skills/mysql/<skill-name>/SKILL.md
skills/mysql/<skill-name>/references/*
skills/mysql/<skill-name>/scripts/*     # 仅用于小体积确定性辅助逻辑
```

通用分析代码继续位于：

```text
skills/metric-timeseries-analysis/analyze-metric-timeseries/
```

MySQL Skill 不复制该目录下的 Python 代码和契约。

### 6.2 Tool 结果要求

DAS、RDS、原服务 MCP 和 `query_sql` 的结果应尽量满足：

- JSON 结构稳定。
- 包含 `success`、`summary`、关键 findings 和必要的紧凑证据。
- 错误具有明确 code 和可重试语义。
- 大体积原始证据由服务侧保存，不进入 LLM 可见结果。
- tool 名称表达诊断语义，注册前不在 Skill 中写假名称。

### 6.3 依赖稳定性

- MySQL Skill 只依赖外部能力合约，不依赖 tool 的内部服务实现。
- 通用分析能力升级算法或缓存时，不修改 MySQL Skill。
- 诊断 tool 名称或 schema 变化时，只修改使用它的 Skill 或对应 reference。
- 新增数据库 service-category 时复用通用分析 Skill，不复制分析代码。

## 7. 迁移与交付

### 7.1 迁移阶段

1. 从原 Python 服务抽取五类通用时序分析能力。
2. 完成通用时序分析 Skill 及其 CES 数据获取、缓存和 DatasetStore。
3. 盘点 DAS/RDS 已有能力并建立诊断能力清单。
4. 由原服务补齐共享型/独享型查询和非标参数查询接口并注册 MCP。
5. 验证 `query_sql` 对内存表、`performance_schema` 和复制状态的覆盖范围。
6. 按场景编写 MySQL service-category Skills。
7. 通过典型故障案例验证证据链和诊断结果。

### 7.2 验收标准

- MySQL Skill 不直接出现 CES API、MCP CLI、DatasetStore 或 raw datapoints 操作。
- 五个分析 profile 可以由多个数据库 service-category 复用。
- DAS/RDS 已有能力不在原服务重复实现。
- slave 专属状态不会通过 master 查询结果误判。
- 任一诊断结果能够追溯到结构化证据。
- 外部引擎可按同一 Skill 和 tool 合约完成编排。
- 典型故障流程不会把大体积时序数据放入 LLM 上下文。

## 8. 待确认事项

- DAS/RDS 最终可复用的真实 tool 名称和 schema。
- 原服务新增接口注册后的真实 MCP tool 名称和 schema。
- `query_sql` 对主从复制异常的覆盖范围及目标节点连接能力。
- 是否需要为特定 MySQL 场景生成图表 artifact。
- 是否在 Skill 编排稳定后再封装单体 `mysql_diagnose` 入口。
