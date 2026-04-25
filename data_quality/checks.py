"""
Data Quality checks using BigQuery SQL assertions.

Each check is a SQL query that returns rows only when the check FAILS.
An empty result = check passed.

Usage:
    python -m data_quality.checks --date 2024-01-15 --layer staging
"""
import argparse
import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from google.cloud import bigquery

logger = logging.getLogger(__name__)


class Severity(Enum):
    CRITICAL = "CRITICAL"   # Failure → stop pipeline, alert oncall
    WARNING  = "WARNING"    # Failure → log alert, continue


@dataclass
class DQCheck:
    name: str
    description: str
    severity: Severity
    sql: str            # Must return rows only on FAILURE


@dataclass
class DQResult:
    check_name: str
    passed: bool
    severity: Severity
    failed_rows: int
    details: str = ""


# -------------------------------------------------------
# Raw layer checks
# -------------------------------------------------------
RAW_CHECKS = [
    DQCheck(
        name="raw_event_id_not_null",
        description="Event ID must not be null in raw table",
        severity=Severity.CRITICAL,
        sql="""
            SELECT COUNT(*) AS failed_rows
            FROM `{project}.raw.github_events`
            WHERE DATE(_ingested_at) = '{run_date}'
              AND id IS NULL
            HAVING COUNT(*) > 0
        """,
    ),
    DQCheck(
        name="raw_created_at_not_null",
        description="created_at must not be null",
        severity=Severity.CRITICAL,
        sql="""
            SELECT COUNT(*) AS failed_rows
            FROM `{project}.raw.github_events`
            WHERE DATE(_ingested_at) = '{run_date}'
              AND created_at IS NULL
            HAVING COUNT(*) > 0
        """,
    ),
    DQCheck(
        name="raw_minimum_row_count",
        description="Raw table must have at least 10 rows for the run date",
        severity=Severity.CRITICAL,
        sql="""
            SELECT COUNT(*) AS row_count
            FROM `{project}.raw.github_events`
            WHERE DATE(_ingested_at) = '{run_date}'
            HAVING COUNT(*) < 10
        """,
    ),
    DQCheck(
        name="raw_future_timestamps",
        description="created_at should not be in the future",
        severity=Severity.WARNING,
        sql="""
            SELECT COUNT(*) AS failed_rows
            FROM `{project}.raw.github_events`
            WHERE DATE(_ingested_at) = '{run_date}'
              AND TIMESTAMP(created_at) > CURRENT_TIMESTAMP()
            HAVING COUNT(*) > 0
        """,
    ),
]

# -------------------------------------------------------
# Staging layer checks
# -------------------------------------------------------
STAGING_CHECKS = [
    DQCheck(
        name="staging_no_duplicate_events",
        description="event_id must be unique within a day in staging",
        severity=Severity.CRITICAL,
        sql="""
            SELECT event_id, COUNT(*) AS cnt
            FROM `{project}.staging.github_events`
            WHERE event_date = '{run_date}'
            GROUP BY event_id
            HAVING COUNT(*) > 1
            LIMIT 10
        """,
    ),
    DQCheck(
        name="staging_event_type_not_null",
        description="event_type must not be null in staging",
        severity=Severity.CRITICAL,
        sql="""
            SELECT COUNT(*) AS failed_rows
            FROM `{project}.staging.github_events`
            WHERE event_date = '{run_date}'
              AND event_type IS NULL
            HAVING COUNT(*) > 0
        """,
    ),
    DQCheck(
        name="staging_known_event_types",
        description="event_type should be a known GitHub event type",
        severity=Severity.WARNING,
        sql="""
            SELECT event_type, COUNT(*) AS cnt
            FROM `{project}.staging.github_events`
            WHERE event_date = '{run_date}'
              AND event_type NOT IN (
                'PushEvent','PullRequestEvent','IssuesEvent','WatchEvent',
                'ForkEvent','CreateEvent','DeleteEvent','IssueCommentEvent',
                'ReleaseEvent','CommitCommentEvent','PullRequestReviewEvent',
                'PullRequestReviewCommentEvent','MemberEvent','PublicEvent',
                'GollumEvent','SponsorshipEvent'
              )
            GROUP BY event_type
            HAVING COUNT(*) > 0
        """,
    ),
    DQCheck(
        name="staging_row_count_vs_raw",
        description="Staging row count should be >= 90% of raw row count",
        severity=Severity.WARNING,
        sql="""
            WITH
              raw_cnt AS (
                SELECT COUNT(*) AS n FROM `{project}.raw.github_events`
                WHERE DATE(_ingested_at) = '{run_date}'
              ),
              stg_cnt AS (
                SELECT COUNT(*) AS n FROM `{project}.staging.github_events`
                WHERE event_date = '{run_date}'
              )
            SELECT raw_cnt.n AS raw_rows, stg_cnt.n AS staging_rows
            FROM raw_cnt, stg_cnt
            WHERE stg_cnt.n < raw_cnt.n * 0.9
        """,
    ),
]

# -------------------------------------------------------
# Serving layer checks
# -------------------------------------------------------
SERVING_CHECKS = [
    DQCheck(
        name="serving_daily_stats_populated",
        description="serving.daily_event_stats must have rows for run date",
        severity=Severity.CRITICAL,
        sql="""
            SELECT COUNT(*) AS row_count
            FROM `{project}.serving.daily_event_stats`
            WHERE event_date = '{run_date}'
            HAVING COUNT(*) = 0
        """,
    ),
    DQCheck(
        name="serving_event_counts_positive",
        description="event_count must be positive",
        severity=Severity.CRITICAL,
        sql="""
            SELECT event_date, event_type, event_count
            FROM `{project}.serving.daily_event_stats`
            WHERE event_date = '{run_date}'
              AND event_count <= 0
        """,
    ),
]

LAYER_CHECKS = {
    "raw": RAW_CHECKS,
    "staging": STAGING_CHECKS,
    "serving": SERVING_CHECKS,
}


def run_checks(project_id: str, run_date: str, layer: str) -> List[DQResult]:
    checks = LAYER_CHECKS.get(layer)
    if not checks:
        raise ValueError(f"Unknown layer: {layer}. Choose from {list(LAYER_CHECKS)}")

    client = bigquery.Client(project=project_id)
    ctx = {"project": project_id, "run_date": run_date}

    results = []
    for check in checks:
        sql = check.sql.format(**ctx)
        try:
            rows = list(client.query(sql).result())
            passed = len(rows) == 0
            failed_rows = rows[0][0] if rows and len(rows[0]) > 0 else len(rows)
            result = DQResult(
                check_name=check.name,
                passed=passed,
                severity=check.severity,
                failed_rows=failed_rows if not passed else 0,
            )
        except Exception as e:
            result = DQResult(
                check_name=check.name,
                passed=False,
                severity=check.severity,
                failed_rows=-1,
                details=str(e),
            )

        status = "PASS" if result.passed else "FAIL"
        logger.info(
            f"[{status}] {check.name} | severity={check.severity.value}"
            + (f" | failed_rows={result.failed_rows}" if not result.passed else "")
        )
        results.append(result)

    return results


def assert_no_critical_failures(results: List[DQResult]) -> None:
    failures = [r for r in results if not r.passed and r.severity == Severity.CRITICAL]
    if failures:
        names = [r.check_name for r in failures]
        raise RuntimeError(f"CRITICAL DQ failures — pipeline halted: {names}")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Run data quality checks")
    parser.add_argument("--date",    required=True, help="YYYY-MM-DD")
    parser.add_argument("--layer",   required=True, choices=["raw", "staging", "serving"])
    parser.add_argument("--project", default="gcp-lab-data-engineering")
    parser.add_argument("--fail-on-critical", action="store_true", default=True)
    args = parser.parse_args()

    results = run_checks(args.project, args.date, args.layer)

    passed = sum(1 for r in results if r.passed)
    total  = len(results)
    print(f"\nDQ [{args.layer}] {args.date}: {passed}/{total} checks passed")

    if args.fail_on_critical:
        try:
            assert_no_critical_failures(results)
        except RuntimeError as e:
            print(f"ERROR: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
