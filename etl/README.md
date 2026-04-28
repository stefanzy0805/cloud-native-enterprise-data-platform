# etl

这个目录用于放置数据加载和转换逻辑。

当前已有 `github_load/`，用于处理 GitHub 数据加载相关代码。根据根目录 README 和 `Makefile` 的设计，这一层还承担从 raw 到 staging、serving 的转换职责，适合放 BigQuery、Spark 或 SQL-based transformation 代码。

它是 ingestion 之后、data_quality 之前的核心处理层。
