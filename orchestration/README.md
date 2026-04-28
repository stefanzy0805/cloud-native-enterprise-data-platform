# orchestration

这个目录负责 pipeline 编排。

- `pipeline.py` 串联每日数据流程：GitHub API 采集、raw 数据质量检查、加载到 BigQuery、raw 到 staging/serving 转换、staging 和 serving 数据质量检查。
- 支持 `--dry-run`，可以在不写入数据的情况下检查执行路径。

它是把各个独立模块组织成端到端数据管道的入口。
