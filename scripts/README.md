# scripts

这个目录保存开发和运维辅助脚本。

- `start-docker.sh` 用于检查 Docker 是否运行，并启动项目的 docker-compose 服务。

这里适合放一次性或辅助性的自动化脚本。核心业务逻辑仍应放在对应模块目录中，例如 `ingestion/`、`etl/`、`data_quality/`。
