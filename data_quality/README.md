# data_quality

这个目录负责数据质量检查。

- `checks.py` 定义 raw、staging、serving 三层的 BigQuery SQL 断言。
- 每个检查遵循“查询返回失败行”的模式：返回空结果表示通过，返回数据表示检查失败。
- 检查分为 `CRITICAL` 和 `WARNING` 两类，关键失败会中断 pipeline，警告适合记录和观测。

它在整体流程中用于验证采集结果、转换结果和服务层聚合结果是否可信。
