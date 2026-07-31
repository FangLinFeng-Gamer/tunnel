# RDS for MySQL Metric ID Catalog

Use this reference to select the exact CES `metric.metric_name` for RDS for
MySQL instances or database proxies. Metric names remain in the official
Chinese wording so they can be matched exactly against the source catalog.

Source: Huawei Cloud
[RDS for MySQL supported monitoring metrics](https://support.huaweicloud.com/usermanual-rds-mysql/rds_06_0001.html),
updated 2026-06-24 and verified for this reference on 2026-07-31.

## Contents

- [Selection Rules](#selection-rules)
- [RDS for MySQL Instance Metrics](#rds-for-mysql-instance-metrics)
- [Database Proxy Metrics](#database-proxy-metrics)

## Selection Rules

- Put the metric ID, not the display name, in `metric.metric_name`.
- Single-node and primary/standby instances use namespace `SYS.RDS` and
  dimension `rds_cluster_id`.
- Cluster edition instances use namespace `SYS.RDS_MYSQL_CLUSTER` and ordered
  dimensions `rds_cluster_id,rds_instance_id`.
- `rds_threadpool_waiting_threads` is not supported for cluster edition.
- Database proxies use namespace `SYS.DBPROXY` and ordered dimensions
  `dbproxy_instance_id,dbproxy_node_id`.
- Confirm current availability in the official source when the selected metric
  is unavailable in a region, engine version, or deployment type.

## RDS for MySQL Instance Metrics

| Metric ID | Official metric name (zh-CN) |
| --- | --- |
| `rds001_cpu_util` | CPU使用率 |
| `rds002_mem_util` | 内存使用率 |
| `rds003_iops` | IOPS |
| `rds004_bytes_in` | 网络输入吞吐量 |
| `rds005_bytes_out` | 网络输出吞吐量 |
| `rds006_conn_count` | 数据库总连接数 |
| `rds007_conn_active_count` | 当前活跃连接数 |
| `rds008_qps` | QPS |
| `rds009_tps` | TPS |
| `rds010_innodb_buf_usage` | 缓冲池利用率 |
| `rds011_innodb_buf_hit` | 缓冲池命中率 |
| `rds012_innodb_buf_dirty` | 缓冲池脏块率 |
| `rds013_innodb_reads` | InnoDB读取吞吐量 |
| `rds014_innodb_writes` | InnoDB写入吞吐量 |
| `rds015_innodb_read_count` | InnoDB文件读取频率 |
| `rds016_innodb_write_count` | InnoDB文件写入频率 |
| `rds017_innodb_log_write_req_count` | InnoDB日志写请求频率 |
| `rds018_innodb_log_write_count` | InnoDB日志物理写频率 |
| `rds019_innodb_log_fsync_count` | InnoDB日志fsync()写频率 |
| `rds020_temp_tbl_rate` | 临时表创建速率 |
| `rds021_myisam_buf_usage` | Key Buffer利用率 |
| `rds022_myisam_buf_write_hit` | Key Buffer写命中率 |
| `rds023_myisam_buf_read_hit` | Key Buffer读命中率 |
| `rds024_myisam_disk_write_count` | MyISAM硬盘写入频率 |
| `rds025_myisam_disk_read_count` | MyISAM硬盘读取频率 |
| `rds026_myisam_buf_write_count` | MyISAM缓冲池写入频率 |
| `rds027_myisam_buf_read_count` | MyISAM缓冲池读取频率 |
| `rds028_comdml_del_count` | Delete语句执行频率 |
| `rds029_comdml_ins_count` | Insert语句执行频率 |
| `rds030_comdml_ins_sel_count` | Insert_Select语句执行频率 |
| `rds031_comdml_rep_count` | Replace语句执行频率 |
| `rds032_comdml_rep_sel_count` | Replace_Selection语句执行频率 |
| `rds033_comdml_sel_count` | Select语句执行频率 |
| `rds034_comdml_upd_count` | Update语句执行频率 |
| `rds035_innodb_del_row_count` | 行删除速率 |
| `rds036_innodb_ins_row_count` | 行插入速率 |
| `rds037_innodb_read_row_count` | 行读取速率 |
| `rds038_innodb_upd_row_count` | 行更新速率 |
| `rds039_disk_util` | 磁盘利用率 |
| `rds047_disk_total_size` | 磁盘总大小 |
| `rds048_disk_used_size` | 磁盘使用量 |
| `rds049_disk_read_throughput` | 硬盘读吞吐量 |
| `rds050_disk_write_throughput` | 硬盘写吞吐量 |
| `rds072_conn_usage` | 连接数使用率 |
| `rds173_replication_delay_avg` | 平均复制时延 |
| `rds073_replication_delay` | 实时复制时延 |
| `rds074_slow_queries` | 慢日志个数统计 |
| `rds075_avg_disk_ms_per_read` | 硬盘读耗时 |
| `rds076_avg_disk_ms_per_write` | 硬盘写耗时 |
| `rds077_vma` | VMA数量 |
| `rds078_threads` | 进程中线程数量 |
| `rds079_vm_hwm` | 进程的物理内存占用峰值 |
| `rds080_vm_peak` | 进程的虚拟内存占用峰值 |
| `rds081_vm_ioutils` | 磁盘I/O处于非空闲状态的时间百分比 |
| `rds082_semi_sync_tx_avg_wait_time` | 事务平均等待时间 |
| `sys_swap_usage` | swap利用率 |
| `rds_innodb_lock_waits` | 等待行锁事务数 |
| `rds_bytes_recv_rate` | 数据库每秒接收字节 |
| `rds_bytes_sent_rate` | 数据库每秒发送字节 |
| `rds_innodb_pages_read_rate` | innodb平均每秒读取的数据量 |
| `rds_innodb_pages_written_rate` | innodb平均每秒写入的数据量 |
| `rds_innodb_os_log_written_rate` | 平均每秒写入redo log的大小 |
| `rds_innodb_buffer_pool_read_requests_rate` | innodb_buffer_pool每秒读请求次数 |
| `rds_innodb_buffer_pool_write_requests_rate` | innodb_buffer_pool每秒写请求次数 |
| `rds_innodb_buffer_pool_pages_flushed_rate` | innodb_buffer_pool每秒页面刷新数 |
| `rds_innodb_log_waits_rate` | 因log buffer不足导致等待flush到磁盘次数 |
| `rds_created_tmp_tables_rate` | 每秒创建临时表数 |
| `rds_wait_thread_count` | 等待线程数 |
| `rds_threadpool_waiting_threads` | 线程池中等待线程数 |
| `rds_innodb_row_lock_time_avg` | 历史行锁平均等待时间 |
| `rds_innodb_row_lock_current_waits` | 当前行锁等待数 |
| `rds_mdl_lock_count` | MDL锁数量 |
| `rds_buffer_pool_wait_free` | 缓冲池空闲页等待次数 |
| `rds_conn_active_usage` | 活跃连接数使用率 |
| `rds_innodb_log_waits_count` | 日志等待次数 |
| `rds_long_transaction` | 长事务指标 |
| `rds_slave_io_running` | 复制IO线程状态 |
| `rds_slave_sql_running` | 复制SQL线程状态 |
| `rds_temp_table_usage` | 临时表空间大小 |
| `rds_pending_mdl_lock_count` | 等待状态的MDL锁数量 |
| `rds_aborted_clients` | 客户端异常关闭连接数 |
| `rds_aborted_connects` | 连接失败数 |
| `rds_prepared_stmt_count` | Prepared语句数目 |
| `rds_max_trx_modified_rows` | 事务修改最大行数 |
| `rds_binlog_size` | Binlog文件大小 |
| `rds_temp_file_size` | 临时文件大小 |
| `rds_bin_log_adding_speed` | Binlog增长速度 |
| `rds338_active_threads_usage` | 线程池线程利用率 |

## Database Proxy Metrics

| Metric ID | Official metric name (zh-CN) |
| --- | --- |
| `rds001_cpu_util` | CPU使用率 |
| `rds002_mem_util` | 内存使用率 |
| `rds004_bytes_in` | 网络输入吞吐量 |
| `rds005_bytes_out` | 网络输出吞吐量 |
| `rds_proxy_frontend_connections` | 前端连接数 |
| `rds_proxy_backend_connections` | 后端连接数 |
| `rds_proxy_average_response_time` | 平均响应时间 |
| `rds_proxy_query_per_seconds` | QPS |
| `rds_proxy_read_query_proportions` | 读占比 |
| `rds_proxy_write_query_proportions` | 写占比 |
| `rds_proxy_frontend_connection_creation` | 每秒平均创建前端连接数 |
| `rds_proxy_transaction_query` | 每秒平均事务中的查询数 |
| `rds_proxy_multi_statement_query` | 每秒平均多语句执行数 |
