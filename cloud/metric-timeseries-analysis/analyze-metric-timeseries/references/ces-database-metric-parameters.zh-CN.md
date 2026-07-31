# CES 数据库指标参数填写

本 reference 只用于填写 `MetricAnalysisSpec.metric` 中与数据库服务相关的字段：

```text
metric.namespace
metric.metric_name
metric.dimensions
```

`region`、`project_id`、时间窗口、`period` 和分析算法参数仍以
`analysis-contract.zh-CN.md` 为准。

服务范围来自华为云 CES
[支持监控的服务列表](https://support.huaweicloud.com/api-ces/ces_03_0059.html)
中的“数据库”分类；该页面链接到各数据库服务当前的监控指标文档。
对于 RDS for MySQL，使用内置的
[指标 ID 目录](rds-mysql-metric-catalog.zh-CN.md)选择准确指标，无需加载完整厂商表格。

## 填写规则

1. 先确定准确的数据库产品、部署形态和测量层级：实例、节点、组件、分片或代理。
2. 从下表选择 `metric.namespace`，不得根据其他数据库产品的参数类推。
3. 打开对应监控指标文档，将“指标 ID”列中的准确指标 ID 填入
   `metric.metric_name`。不得填写中文指标名称，也不得自行拼接指标 ID。
4. 在同一个指标行中读取“维度”列，按照该指标所在行给出的准确顺序填写全部
   dimension key。下表中的维度仅用于定位，不能替代具体指标行。
5. 每个 dimension 的 `value` 必须是可信服务 API 结果或管理控制台中的对应实例
   ID、节点 ID、组件 ID、分片 ID 或代理 ID。不得使用资源名称、`project_id`
   或错误层级的父资源 ID 代替。
6. 多层维度必须包含全部父级：0 层在前，随后依次填写 1 层及更深层级。
7. 产品类型、指标 ID、维度 key 或维度 value 仍不明确时，将其保留为缺失项，
   一次性向用户询问全部未确定值；不得用不同参数名称反复调用分析 CLI。

## 数据库服务参数表

| 数据库服务 | `metric.namespace` | 维度填写说明 | 官方监控指标文档 |
| --- | --- | --- | --- |
| RDS for MySQL 单机或主备实例 | `SYS.RDS` | 常见实例指标使用 `rds_cluster_id`。 | [内置 RDS for MySQL 指标 ID](rds-mysql-metric-catalog.zh-CN.md) |
| RDS for MySQL 集群版 | `SYS.RDS_MYSQL_CLUSTER` | 节点指标通常使用 `rds_cluster_id,rds_instance_id`。 | [内置 RDS for MySQL 指标 ID](rds-mysql-metric-catalog.zh-CN.md) |
| RDS for MySQL 或 TaurusDB 数据库代理 | `SYS.DBPROXY` | 代理节点指标使用 `dbproxy_instance_id,dbproxy_node_id`，仍须核对指标行。 | [内置 RDS for MySQL 代理指标 ID](rds-mysql-metric-catalog.zh-CN.md)、[TaurusDB](https://support.huaweicloud.com/usermanual-taurusdb/taurusdb_03_0085.html) |
| RDS for MariaDB | `SYS.RDS` | 实例指标使用 `mariadb_cluster_id`。 | [RDS for MariaDB](https://support.huaweicloud.com/usermanual-rds-mariadb/maria_03_0087.html) |
| RDS for PostgreSQL | `SYS.RDS` | 实例指标使用 `postgresql_cluster_id`。 | [RDS for PostgreSQL](https://support.huaweicloud.com/usermanual-rds-pg/rds_pg_06_0001.html) |
| RDS for SQL Server | `SYS.RDS` | 实例指标使用 `rds_cluster_sqlserver_id`。 | [RDS for SQL Server](https://support.huaweicloud.com/usermanual-rds-mssql/rds_sqlserver_06_0001.html) |
| 文档数据库服务 DDS | `SYS.DDS` | 按指标行使用 `mongodb_node_id` 或 `mongodb_instance_id,mongodb_node_id`。 | [DDS](https://support.huaweicloud.com/usermanual-dds/dds_03_0026.html) |
| 分布式缓存服务 DCS | `SYS.DCS` | 实例指标使用 `dcs_instance_id`；节点指标按指标行增加 `dcs_cluster_redis_node`、`dcs_cluster_proxy_node` 或 `dcs_cluster_proxy2_node`；Memcached 使用 `dcs_memcached_instance_id`。 | [DCS](https://support.huaweicloud.com/usermanual-dcs/dcs-ug-0713011.html) |
| 分布式数据库中间件 DDM | `SYS.DDMS` | 按指标行使用 `instance_id`、`node_id` 或文档指定的层级组合。 | [DDM](https://support.huaweicloud.com/usermanual-ddm/ddm_03_0051.html) |
| GeminiDB Cassandra | `SYS.NoSQL` | 节点指标通常使用 `cassandra_cluster_id,cassandra_node_id`。 | [GeminiDB Cassandra](https://support.huaweicloud.com/intl/zh-cn/cassandraug-nosql/nosql_03_0011.html) |
| GeminiDB Mongo | `SYS.NoSQL` | 实例层使用 `mongodb_cluster_id`；节点指标按文档增加 `mongodb_node_id`。 | [GeminiDB Mongo](https://support.huaweicloud.com/intl/zh-cn/mongoug-nosql/nosql_08_0106.html) |
| GeminiDB Influx | `SYS.NoSQL` | 节点指标通常使用 `influxdb_cluster_id,influxdb_node_id`。 | [GeminiDB Influx](https://support.huaweicloud.com/intl/zh-cn/influxug-nosql/nosql_09_0036.html) |
| GeminiDB Redis | `SYS.NoSQL` | 实例指标使用 `redis_cluster_id`；节点指标使用 `redis_cluster_id,redis_node_id`。 | [GeminiDB Redis](https://support.huaweicloud.com/redisug-nosql/nosql_10_0036.html) |
| GeminiDB 兼容 DynamoDB 接口 | `SYS.NoSQL` | 节点指标通常使用 `cassandra_cluster_id,cassandra_node_id`。 | [GeminiDB 兼容 DynamoDB 接口](https://support.huaweicloud.com/dynamodbug-nosql/nosql_dynamodb_0147.html) |
| TaurusDB | `SYS.GAUSSDB` | 节点指标通常使用 `gaussdb_mysql_instance_id,gaussdb_mysql_node_id`。 | [TaurusDB](https://support.huaweicloud.com/usermanual-taurusdb/taurusdb_03_0085.html) |
| GaussDB | `SYS.GAUSSDBV5` | 按指标行使用 `gaussdbv5_instance_id`；更深层级增加 `gaussdbv5_node_id` 和 `gaussdbv5_component_id`。 | [GaussDB](https://support.huaweicloud.com/usermanual-gaussdb/gaussdb_01_238.html) |
| 数据复制服务 DRS | `SYS.DRS` | 按指标行使用 `instance_id` 或 `instance_id,node_id`。 | [DRS](https://support.huaweicloud.com/realtimemig-drs/drs_03_0106.html) |

## Dimensions 编码

将指标行中的有序维度 key 和对应 ID 转成批量查询使用的数组：

```json
[
  {"name": "<0层维度key>", "value": "<0层资源ID>"},
  {"name": "<1层维度key>", "value": "<1层资源ID>"}
]
```

例如，某个 RDS for MySQL 集群节点指标的维度列为
`rds_cluster_id,rds_instance_id`，则填写为：

```json
[
  {"name": "rds_cluster_id", "value": "<RDS实例ID>"},
  {"name": "rds_instance_id", "value": "<RDS节点ID>"}
]
```

该示例不能用于证明其他指标或其他数据库服务也使用相同维度；最终必须核对所选
指标所在行。
