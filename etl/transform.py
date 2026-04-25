"""
ETL Step 2 & 3: SQL-based transforms inside BigQuery.

raw → staging: normalise fields, deduplicate, add processing metadata.
staging → serving: aggregate daily stats and top repos.

Usage:
    python -m etl.transform --date 2024-01-15 --project gcp-lab-data-engineering
"""
import argparse
import logging
from datetime import datetime

from google.cloud import bigquery

logger = logging.getLogger(__name__)

# -------------------------------------------------------
# SQL Templates
# -------------------------------------------------------

SQL_RAW_TO_STAGING = """
MERGE `{project}.staging.github_events` T
USING (
    SELECT
        id                                       AS event_id,
        type                                     AS event_type,
        DATE(TIMESTAMP(created_at))              AS event_date,
        TIMESTAMP(created_at)                    AS event_ts,
        JSON_VALUE(actor, '$.login')             AS actor_login,
        JSON_VALUE(repo,  '$.name')              AS repo_name,
        public                                   AS is_public,
        TIMESTAMP(_ingested_at)                  AS _ingested_at,
        CURRENT_TIMESTAMP()                      AS _processed_at
    FROM `{project}.raw.github_events`
    WHERE DATE(_ingested_at) = '{run_date}'
      AND id IS NOT NULL
      AND created_at IS NOT NULL
) S
ON T.event_id = S.event_id AND T.event_date = S.event_date
WHEN NOT MATCHED THEN INSERT VALUES (
    S.event_id, S.event_type, S.event_date, S.event_ts,
    S.actor_login, S.repo_name, S.is_public,
    S._ingested_at, S._processed_at
)
"""

SQL_STAGING_TO_DAILY_STATS = """
MERGE `{project}.serving.daily_event_stats` T
USING (
    SELECT
        event_date,
        event_type,
        COUNT(*)                 AS event_count,
        COUNT(DISTINCT actor_login) AS unique_actors,
        COUNT(DISTINCT repo_name)   AS unique_repos,
        CURRENT_TIMESTAMP()      AS _updated_at
    FROM `{project}.staging.github_events`
    WHERE event_date = '{run_date}'
    GROUP BY event_date, event_type
) S
ON T.event_date = S.event_date AND T.event_type = S.event_type
WHEN MATCHED THEN UPDATE SET
    event_count   = S.event_count,
    unique_actors = S.unique_actors,
    unique_repos  = S.unique_repos,
    _updated_at   = S._updated_at
WHEN NOT MATCHED THEN INSERT VALUES (
    S.event_date, S.event_type, S.event_count,
    S.unique_actors, S.unique_repos, S._updated_at
)
"""

SQL_STAGING_TO_TOP_REPOS = """
MERGE `{project}.serving.top_repos_daily` T
USING (
    SELECT
        event_date,
        repo_name,
        COUNT(*)                    AS event_count,
        COUNT(DISTINCT actor_login) AS unique_actors,
        STRING_AGG(DISTINCT event_type, ', ' ORDER BY event_type) AS event_types,
        CURRENT_TIMESTAMP()         AS _updated_at
    FROM `{project}.staging.github_events`
    WHERE event_date = '{run_date}'
    GROUP BY event_date, repo_name
    QUALIFY RANK() OVER (PARTITION BY event_date ORDER BY COUNT(*) DESC) <= 100
) S
ON T.event_date = S.event_date AND T.repo_name = S.repo_name
WHEN MATCHED THEN UPDATE SET
    event_count   = S.event_count,
    unique_actors = S.unique_actors,
    event_types   = S.event_types,
    _updated_at   = S._updated_at
WHEN NOT MATCHED THEN INSERT VALUES (
    S.event_date, S.repo_name, S.event_count,
    S.unique_actors, S.event_types, S._updated_at
)
"""


def run_query(client: bigquery.Client, sql: str, step_name: str) -> int:
    """Execute a BigQuery SQL statement and return rows affected."""
    logger.info(f"Running: {step_name}")
    job = client.query(sql)
    job.result()
    rows = job.num_dml_affected_rows or 0
    logger.info(f"Done: {step_name} | rows_affected={rows}")
    return rows


def run_transforms(project_id: str, run_date: str) -> dict:
    client = bigquery.Client(project=project_id)
    ctx = {"project": project_id, "run_date": run_date}

    stats = {}
    stats["raw_to_staging"] = run_query(
        client, SQL_RAW_TO_STAGING.format(**ctx), "raw → staging"
    )
    stats["staging_to_daily_stats"] = run_query(
        client, SQL_STAGING_TO_DAILY_STATS.format(**ctx), "staging → serving.daily_event_stats"
    )
    stats["staging_to_top_repos"] = run_query(
        client, SQL_STAGING_TO_TOP_REPOS.format(**ctx), "staging → serving.top_repos_daily"
    )
    return stats


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Transform raw data through staging to serving")
    parser.add_argument("--date",    required=True, help="YYYY-MM-DD")
    parser.add_argument("--project", default="gcp-lab-data-engineering")
    args = parser.parse_args()

    stats = run_transforms(args.project, args.date)
    for step, rows in stats.items():
        print(f"  {step}: {rows} rows")


if __name__ == "__main__":
    main()
