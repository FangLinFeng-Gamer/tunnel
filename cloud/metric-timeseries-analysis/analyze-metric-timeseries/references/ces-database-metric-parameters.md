# CES Database Metric Parameters

Use this reference only to fill the database-specific parts of
`MetricAnalysisSpec.metric`:

```text
metric.namespace
metric.metric_name
metric.dimensions
```

For `region`, `project_id`, the time window, `period`, and analysis options, use
`analysis-contract.md`.

The source service list is the Huawei Cloud CES
[Supported Services](https://support.huaweicloud.com/api-ces/ces_03_0059.html)
page. Its database category links to each service's current metric catalog.
For RDS for MySQL, use the bundled
[metric ID catalog](rds-mysql-metric-catalog.md) to select an exact ID without
loading the full vendor table.

## Filling Rules

1. Identify the exact database product, deployment type, and measurement level:
   instance, node, component, shard, or proxy.
2. Select `metric.namespace` from the service table below. Do not infer it from
   another database product.
3. Open the linked service metric catalog and copy the exact metric ID into
   `metric.metric_name`. Do not use the display name and do not invent an ID.
4. Copy every dimension key in the exact order shown in that metric row. The keys
   in the table below are a lookup aid, not a replacement for the selected metric
   row.
5. Fill each dimension `value` with the corresponding instance, node, component,
   shard, or proxy ID from a trusted service API result or the management
   console. Do not use a resource name, `project_id`, or a parent ID in place of
   the documented value.
6. For a multi-level metric, include all parent dimensions. Keep level 0 first,
   followed by level 1 and deeper levels.
7. If the product type, metric ID, dimension key, or dimension value remains
   unknown, leave it unresolved and ask for all unresolved values together. Do
   not try alternate parameter names against the analysis CLI.

## Database Service Lookup

| Database service | `metric.namespace` | Dimension guidance | Official metric catalog |
| --- | --- | --- | --- |
| RDS for MySQL, single-node or primary/standby | `SYS.RDS` | Common instance metrics use `rds_cluster_id`. | [Bundled RDS for MySQL metric IDs](rds-mysql-metric-catalog.md) |
| RDS for MySQL cluster edition | `SYS.RDS_MYSQL_CLUSTER` | Node metrics commonly use `rds_cluster_id,rds_instance_id`. | [Bundled RDS for MySQL metric IDs](rds-mysql-metric-catalog.md) |
| Database proxy for RDS for MySQL or TaurusDB | `SYS.DBPROXY` | Proxy node metrics use `dbproxy_instance_id,dbproxy_node_id`; verify the selected row. | [Bundled RDS for MySQL proxy metric IDs](rds-mysql-metric-catalog.md), [TaurusDB metrics](https://support.huaweicloud.com/usermanual-taurusdb/taurusdb_03_0085.html) |
| RDS for MariaDB | `SYS.RDS` | Instance metrics use `mariadb_cluster_id`. | [RDS for MariaDB metrics](https://support.huaweicloud.com/usermanual-rds-mariadb/maria_03_0087.html) |
| RDS for PostgreSQL | `SYS.RDS` | Instance metrics use `postgresql_cluster_id`. | [RDS for PostgreSQL metrics](https://support.huaweicloud.com/usermanual-rds-pg/rds_pg_06_0001.html) |
| RDS for SQL Server | `SYS.RDS` | Instance metrics use `rds_cluster_sqlserver_id`. | [RDS for SQL Server metrics](https://support.huaweicloud.com/usermanual-rds-mssql/rds_sqlserver_06_0001.html) |
| Document Database Service DDS | `SYS.DDS` | Depending on the metric row, use `mongodb_node_id` or `mongodb_instance_id,mongodb_node_id`. | [DDS metrics](https://support.huaweicloud.com/usermanual-dds/dds_03_0026.html) |
| Distributed Cache Service DCS | `SYS.DCS` | Instance metrics use `dcs_instance_id`; node metrics add the row-specific `dcs_cluster_redis_node`, `dcs_cluster_proxy_node`, or `dcs_cluster_proxy2_node`. Memcached uses `dcs_memcached_instance_id`. | [DCS metrics](https://support.huaweicloud.com/usermanual-dcs/dcs-ug-0713011.html) |
| Distributed Database Middleware DDM | `SYS.DDMS` | The selected row uses `instance_id`, `node_id`, or a documented hierarchy. | [DDM metrics](https://support.huaweicloud.com/usermanual-ddm/ddm_03_0051.html) |
| GeminiDB Cassandra | `SYS.NoSQL` | Node metrics commonly use `cassandra_cluster_id,cassandra_node_id`. | [GeminiDB Cassandra metrics](https://support.huaweicloud.com/intl/zh-cn/cassandraug-nosql/nosql_03_0011.html) |
| GeminiDB Mongo | `SYS.NoSQL` | Use `mongodb_cluster_id` for the instance level and add `mongodb_node_id` for node-level metrics as documented. | [GeminiDB Mongo metrics](https://support.huaweicloud.com/intl/zh-cn/mongoug-nosql/nosql_08_0106.html) |
| GeminiDB Influx | `SYS.NoSQL` | Node metrics commonly use `influxdb_cluster_id,influxdb_node_id`. | [GeminiDB Influx metrics](https://support.huaweicloud.com/intl/zh-cn/influxug-nosql/nosql_09_0036.html) |
| GeminiDB Redis | `SYS.NoSQL` | Instance metrics use `redis_cluster_id`; node metrics use `redis_cluster_id,redis_node_id`. | [GeminiDB Redis metrics](https://support.huaweicloud.com/redisug-nosql/nosql_10_0036.html) |
| GeminiDB DynamoDB-compatible API | `SYS.NoSQL` | Node metrics commonly use `cassandra_cluster_id,cassandra_node_id`. | [GeminiDB DynamoDB-compatible metrics](https://support.huaweicloud.com/dynamodbug-nosql/nosql_dynamodb_0147.html) |
| TaurusDB | `SYS.GAUSSDB` | Node metrics commonly use `gaussdb_mysql_instance_id,gaussdb_mysql_node_id`. | [TaurusDB metrics](https://support.huaweicloud.com/usermanual-taurusdb/taurusdb_03_0085.html) |
| GaussDB | `SYS.GAUSSDBV5` | Depending on the row, use `gaussdbv5_instance_id`; add `gaussdbv5_node_id` and `gaussdbv5_component_id` for deeper levels. | [GaussDB metrics](https://support.huaweicloud.com/usermanual-gaussdb/gaussdb_01_238.html) |
| Data Replication Service DRS | `SYS.DRS` | Depending on the row, use `instance_id` or `instance_id,node_id`. | [DRS metrics](https://support.huaweicloud.com/realtimemig-drs/drs_03_0106.html) |

## Dimension Encoding

Convert the ordered dimension keys and IDs into the batch-query array:

```json
[
  {"name": "<level-0-key>", "value": "<level-0-id>"},
  {"name": "<level-1-key>", "value": "<level-1-id>"}
]
```

For example, an RDS for MySQL cluster node metric whose row declares
`rds_cluster_id,rds_instance_id` is encoded as:

```json
[
  {"name": "rds_cluster_id", "value": "<RDS-instance-id>"},
  {"name": "rds_instance_id", "value": "<RDS-node-id>"}
]
```

This example does not authorize those keys for another metric or database
service. Always verify the selected metric row.
