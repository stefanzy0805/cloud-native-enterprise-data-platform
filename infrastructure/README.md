# infrastructure

这个目录保存基础设施即代码。

- `terraform/` 定义 GCP 资源，例如 GCS、BigQuery、Pub/Sub、IAM 等。

它的作用是用可复现的方式创建云端数据平台依赖资源，避免手工在控制台配置导致环境不可追踪。运行前通常需要先设置 GCP project、认证信息和 Terraform 变量。
