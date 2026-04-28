import os  # 👉 用来处理文件夹（创建目录等）
import json  # 👉 把 Python dict 转成 JSON 字符串（写入文件）
import requests  # 👉 用来调用 API（发送 HTTP 请求）
from datetime import datetime, timezone  # 👉 获取当前时间（UTC，用于文件命名）
from zoneinfo import ZoneInfo  # Python 3.9+

# GitHub API 地址（获取 pandas repo 的 commits）
base_url = "https://api.github.com/repos/pandas-dev/pandas/commits"

# 👉 定义输出目录（你指定的路径）
output_dir = "data/raw/github_events"

# 👉 如果目录不存在，就自动创建（避免报错）
os.makedirs(output_dir, exist_ok=True)

# 👉 获取当前 UTC 日期（避免时区问题）
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# 👉 构造最终输出文件路径（按日期命名，避免覆盖历史数据）
output_file = f"{output_dir}/commits_{today}.jsonl"

max_pages = 15  # 👉 最多跑15页

# 👉 从第1页开始抓数据（分页控制）
page = 1

# 👉 打开文件准备写入（"w" = 覆盖写，每次运行都会重新生成当天文件）
with open(output_file, "w", encoding="utf-8") as f:
    
    while page <= max_pages:  # 👉 无限循环，直到我们手动 break（分页抓取常用模式）
        
        # 👉 构造 API 请求（每页100条，page 控制翻页）
        url = f"{base_url}?per_page=100&page={page}"

        # 👉 发送 HTTP GET 请求
        response = requests.get(url)

        # 👉 打印状态码（200=成功，用于调试）
        print("Status:", response.status_code)

        # 👉 打印剩余 API 次数（防止被限流）

        print("Remaining:", response.headers.get("X-RateLimit-Remaining"))
        reset_ts = int(response.headers.get("X-RateLimit-Reset"))
        print("Next Time Reset:",datetime.fromtimestamp(reset_ts, tz=timezone.utc).astimezone(ZoneInfo("America/Vancouver"))
)

        # 👉 如果请求失败（不是200），停止程序
        if response.status_code != 200:
            break

        # 👉 把 JSON 响应转成 Python 数据（list of dict）
        data = response.json()

        # 👉 如果这一页没有数据了，说明已经抓完所有数据
        if not data:
            break

        # 👉 打印当前处理进度（方便观察）
        print(f"Processing page {page}")

        # 👉 遍历这一页的每一条 commit（核心：逐条处理数据）
        for row in data:
            
            # 👉 从复杂 JSON 中提取我们需要的字段
            record = {
                "sha": row["sha"],  # 👉 commit 唯一ID
                "author": row["commit"]["author"]["name"],  # 👉 作者名字
                "date": row["commit"]["author"]["date"]  # 👉 提交时间
            }

            # 👉 把 dict 转成 JSON 字符串，并写入一行（JSONL格式）
            f.write(json.dumps(record) + "\n")

        # 👉 当前页处理完 → 翻到下一页
        page += 1

# 👉 程序结束后打印文件路径（确认输出位置）
print("Saved to:", output_file)