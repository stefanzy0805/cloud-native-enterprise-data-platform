# docker

这个目录保存 Docker 相关辅助文件。

- `.env.example` 提供本地容器环境变量示例。
- `postgres/` 保存 PostgreSQL 初始化脚本。
- `images/` 保存离线镜像或安装包类文件，体积通常较大。

根目录的 `docker-compose.yml` 会引用这里的文件来启动开发容器和本地 PostgreSQL 服务。
