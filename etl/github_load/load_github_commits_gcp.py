import os  # 用来读取环境变量（GCP_PROJECT_ID、GOOGLE_APPLICATION_CREDENTIALS 等）
import uuid  # 用来生成临时表名，避免多次运行冲突
from pathlib import Path  # 更安全地处理文件路径

from google.cloud import bigquery  # BigQuery 客户端库
from google.api_core.exceptions import NotFound  # 判断 BigQuery 表是否存在


def load_env() -> None:
    """
    从项目根目录加载 .env 文件，把里面的配置写入环境变量（os.environ）
    作用：让后续代码可以通过 os.getenv() 读取 GCP 配置
    """

    # ① 找到项目根目录（当前文件 → 往上两级）
    project_root = Path(__file__).resolve().parents[2]

    # ② 拼出 .env 文件路径
    env_path = project_root / ".env"

    # ③ 优先使用 python-dotenv
    try:
        from dotenv import load_dotenv

        # 自动把 .env 中的 key=value 加载到 os.environ
        load_dotenv(env_path)
    except ImportError:
        # 如果没安装 python-dotenv，就走下面手动解析逻辑
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()

                # 跳过：空行 / 注释 / 非 key=value 格式
                if not line or line.startswith("#") or "=" not in line:
                    continue

                # 拆分 key=value
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")

                # 写入环境变量（如果已经存在就不覆盖）
                os.environ.setdefault(key, value)

    # ④ 如果 GOOGLE_APPLICATION_CREDENTIALS 是相对路径，转成绝对路径
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path and not Path(credentials_path).is_absolute():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(project_root / credentials_path)


def get_bigquery_client() -> bigquery.Client:
    """
    创建 BigQuery 客户端
    优先使用 GCP_PROJECT_ID，否则使用 GOOGLE_CLOUD_PROJECT
    """

    # ① 每次运行先加载 .env（保证环境变量存在）
    load_env()

    # ② 读取 GCP 项目 ID
    project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")

    if not project_id:
        raise ValueError("缺少 GCP_PROJECT_ID 或 GOOGLE_CLOUD_PROJECT 环境变量")

    # ③ 创建 BigQuery client
    return bigquery.Client(project=project_id)


def ensure_github_commits_table(client: bigquery.Client, table_id: str) -> None:
    """
    确保 BigQuery 目标表存在
    表结构对应 JSONL 中的 sha、author、date 三个字段
    """

    schema = [
        bigquery.SchemaField("sha", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("author", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("date", "TIMESTAMP", mode="NULLABLE"),
    ]

    try:
        # 如果表已经存在，直接返回
        client.get_table(table_id)
        return
    except NotFound:
        # 如果表不存在，就创建
        table = bigquery.Table(table_id, schema=schema)
        client.create_table(table)


# =========================
# 主程序开始
# =========================

# ① 建立 BigQuery 客户端
client = get_bigquery_client()

# ② 读取项目 ID，并定义要写入的 BigQuery 表
project_id = client.project
dataset_id = os.getenv("GCP_BIGQUERY_DATASET", "raw")
table_name = os.getenv("GCP_BIGQUERY_GITHUB_COMMITS_TABLE", "github_commits")
target_table_id = f"{project_id}.{dataset_id}.{table_name}"

# ③ 定义要读取的 JSONL 文件路径
file_path = "data/raw/github_events/commits_2026-04-27.jsonl"

# ④ 确保目标表存在
ensure_github_commits_table(client, target_table_id)

# ⑤ 创建临时表，用来先承接本次 JSONL 数据
temp_table_name = f"_tmp_github_commits_{uuid.uuid4().hex}"
temp_table_id = f"{project_id}.{dataset_id}.{temp_table_name}"

job_config = bigquery.LoadJobConfig(
    source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    schema=[
        bigquery.SchemaField("sha", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("author", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("date", "TIMESTAMP", mode="NULLABLE"),
    ],
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
)

try:
    # ⑥ 把本地 JSONL 文件加载到 BigQuery 临时表
    with open(file_path, "rb") as f:
        load_job = client.load_table_from_file(
            f,
            temp_table_id,
            job_config=job_config,
        )

    # 等待加载完成
    load_job.result()

    # ⑦ 用 MERGE 写入目标表，效果类似 Postgres 的 ON CONFLICT (sha) DO NOTHING
    merge_sql = f"""
    MERGE `{target_table_id}` AS target
    USING `{temp_table_id}` AS source
    ON target.sha = source.sha
    WHEN NOT MATCHED THEN
      INSERT (sha, author, date)
      VALUES (source.sha, source.author, source.date)
    """

    merge_job = client.query(merge_sql)
    merge_job.result()

    print(f"已写入 BigQuery 表：{target_table_id}")
    print(f"本次新增行数：{merge_job.num_dml_affected_rows}")
finally:
    # ⑧ 删除临时表，释放资源
    client.delete_table(temp_table_id, not_found_ok=True)
