import json  # 用来解析 JSON 数据（把字符串转成 Python dict）
import os    # 用来读取环境变量（DATABASE_URL 等）
from pathlib import Path  # 更安全地处理文件路径
import psycopg2  # Postgres 数据库连接库


def load_env() -> None:
    """
    从项目根目录加载 .env 文件，把里面的配置写入环境变量（os.environ）
    作用：让后续代码可以通过 os.getenv() 读取数据库配置
    """

    # ① 找到项目根目录（当前文件 → 往上两级）
    project_root = Path(__file__).resolve().parents[2]

    # ② 拼出 .env 文件路径
    env_path = project_root / ".env"

    # ③ 优先使用 python-dotenv（标准库）
    try:
        from dotenv import load_dotenv

        # 自动把 .env 中的 key=value 加载到 os.environ
        load_dotenv(env_path)
        return  # 成功后直接结束
    except ImportError:
        # 如果没安装 python-dotenv，就走下面手动解析逻辑
        pass

    # ④ 如果 .env 文件不存在，直接返回（不报错）
    if not env_path.exists():
        return

    # ⑤ 手动逐行读取 .env 文件
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        # 跳过：空行 / 注释 / 非 key=value 格式
        if not line or line.startswith("#") or "=" not in line:
            continue

        # ⑥ 拆分 key=value
        key, value = line.split("=", 1)
        key = key.strip()

        # 去掉可能的空格和引号（比如 "xxx" 或 'xxx'）
        value = value.strip().strip("'\"")

        # ⑦ 写入环境变量（如果已经存在就不覆盖）
        os.environ.setdefault(key, value)


def get_postgres_connection():
    """
    创建 Postgres 数据库连接
    优先使用 DATABASE_URL，否则使用分散配置（POSTGRES_*）
    """

    # ① 每次运行先加载 .env（保证环境变量存在）
    load_env()

    # ② 优先读取 DATABASE_URL（工程中最常见）
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # 如果存在 → 直接用 URL 连接（最简洁）
        return psycopg2.connect(database_url)

    # ③ fallback：使用单独配置项
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "postgres"),  # 数据库名（默认 postgres）
        user=os.getenv("POSTGRES_USER", "postgres"),  # 用户名
        password=os.getenv("POSTGRES_PASSWORD"),      # 密码（必须有）
        host=os.getenv("POSTGRES_HOST", "localhost"), # 主机
        port=os.getenv("POSTGRES_PORT", "5432"),      # 端口
    )


# =========================
# 主程序开始
# =========================

# ① 建立数据库连接
conn = get_postgres_connection()

# ② 创建 cursor（执行 SQL 用）
cursor = conn.cursor()

# ③ 定义要读取的 JSONL 文件路径
file_path = "data/raw/github_events/commits_2026-04-27.jsonl"

# ④ 打开文件逐行读取（JSONL = 每一行都是一个 JSON）
with open(file_path, "r") as f:
    for line in f:
        # 把 JSON 字符串转成 Python dict
        record = json.loads(line)

        # ⑤ 执行 SQL 插入数据
        cursor.execute(
            """
            INSERT INTO public.github_commits (sha, author, "date")
            VALUES (%s, %s, %s)
            ON CONFLICT (sha) DO NOTHING
            """,
            (
                record["sha"],    # commit hash（主键）
                record["author"], # 作者
                record["date"],   # 时间
            ),
        )

# ⑥ 提交事务（真正写入数据库）
conn.commit()

# ⑦ 关闭 cursor 和连接（释放资源）
cursor.close()
conn.close()