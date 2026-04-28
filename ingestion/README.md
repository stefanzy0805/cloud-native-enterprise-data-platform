# ingestion

这个目录负责数据采集。

- `github_api/` 保存从 GitHub API 拉取数据的代码。
- `csv/` 用于 CSV 类数据源或本地文件采集。

采集层的目标是把外部数据源稳定写入 raw layer，后续再交给 ETL 和数据质量模块处理。
