"""
Pipeline Orchestrator — runs the full daily pipeline end-to-end.

Execution order:
  1. Ingest  : GitHub API → GCS raw
  2. DQ raw  : Validate raw layer
  3. Load BQ : GCS → BigQuery raw dataset
  4. Transform: raw → staging → serving (SQL MERGE)
  5. DQ staging
  6. DQ serving

Usage:
    python -m orchestration.pipeline --date 2024-01-15
    python -m orchestration.pipeline --date 2024-01-15 --dry-run
"""
import argparse
import logging
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# -------------------------------------------------------
# Step execution helper
# -------------------------------------------------------

@contextmanager
def step(name: str):
    """Log timing and re-raise with step context on failure."""
    start = datetime.now(timezone.utc)
    logger.info(f"▶ START  {name}")
    try:
        yield
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        logger.info(f"✓ DONE   {name} ({elapsed:.1f}s)")
    except Exception as exc:
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        logger.error(f"✗ FAILED {name} ({elapsed:.1f}s): {exc}")
        raise RuntimeError(f"Step '{name}' failed: {exc}") from exc


# -------------------------------------------------------
# Pipeline
# -------------------------------------------------------

def run_pipeline(
    run_date: str,
    project_id: str = "gcp-lab-data-engineering",
    raw_bucket: Optional[str] = None,
    event_limit: Optional[int] = None,
    dry_run: bool = False,
) -> dict:
    """
    Execute the full daily pipeline.

    Returns a summary dict with row counts and status.
    """
    run_id = str(uuid.uuid4())[:8]
    raw_bucket = raw_bucket or f"{project_id}-datalake-raw"

    logger.info(
        f"Pipeline starting | run_id={run_id} | date={run_date} | "
        f"project={project_id} | dry_run={dry_run}"
    )

    if dry_run:
        logger.info("DRY RUN — no data will be written or transformed")
        return {"run_id": run_id, "status": "dry_run", "date": run_date}

    summary = {"run_id": run_id, "date": run_date, "project": project_id}

    # --------------------------------------------------
    # Step 1: Ingest GitHub Events → GCS
    # --------------------------------------------------
    with step("1/6 ingest github events → GCS"):
        from ingestion.api_ingest import fetch_events, write_raw
        records = fetch_events(run_date=run_date, limit=event_limit)
        write_raw(records, sink="gcs", run_date=run_date, bucket=raw_bucket)
        summary["ingested_records"] = len(records)
        logger.info(f"Ingested {len(records)} events")

    # --------------------------------------------------
    # Step 2: DQ — raw layer
    # --------------------------------------------------
    with step("2/6 data quality — raw layer"):
        from data_quality.checks import run_checks, assert_no_critical_failures
        raw_results = run_checks(project_id, run_date, layer="raw")
        assert_no_critical_failures(raw_results)
        summary["dq_raw_passed"] = sum(1 for r in raw_results if r.passed)
        summary["dq_raw_total"]  = len(raw_results)

    # --------------------------------------------------
    # Step 3: Load GCS → BigQuery raw
    # --------------------------------------------------
    with step("3/6 load GCS → BigQuery raw"):
        from etl.load import load_gcs_to_bq
        rows_loaded = load_gcs_to_bq(
            project_id=project_id,
            run_date=run_date,
            source_bucket=raw_bucket,
        )
        summary["bq_loaded_rows"] = rows_loaded

    # --------------------------------------------------
    # Step 4: Transform raw → staging → serving
    # --------------------------------------------------
    with step("4/6 transform raw → staging → serving"):
        from etl.transform import run_transforms
        transform_stats = run_transforms(project_id, run_date)
        summary.update(transform_stats)

    # --------------------------------------------------
    # Step 5: DQ — staging layer
    # --------------------------------------------------
    with step("5/6 data quality — staging layer"):
        from data_quality.checks import run_checks, assert_no_critical_failures
        stg_results = run_checks(project_id, run_date, layer="staging")
        assert_no_critical_failures(stg_results)
        summary["dq_staging_passed"] = sum(1 for r in stg_results if r.passed)
        summary["dq_staging_total"]  = len(stg_results)

    # --------------------------------------------------
    # Step 6: DQ — serving layer
    # --------------------------------------------------
    with step("6/6 data quality — serving layer"):
        from data_quality.checks import run_checks, assert_no_critical_failures
        srv_results = run_checks(project_id, run_date, layer="serving")
        assert_no_critical_failures(srv_results)
        summary["dq_serving_passed"] = sum(1 for r in srv_results if r.passed)
        summary["dq_serving_total"]  = len(srv_results)

    summary["status"] = "success"
    logger.info(f"Pipeline complete | {summary}")
    return summary


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    parser = argparse.ArgumentParser(description="Run the GitHub Events daily pipeline")
    parser.add_argument("--date",    required=True, help="YYYY-MM-DD run date")
    parser.add_argument("--project", default="gcp-lab-data-engineering")
    parser.add_argument("--bucket",  default=None, help="Override raw GCS bucket")
    parser.add_argument("--limit",   type=int, default=None, help="Limit events fetched (for testing)")
    parser.add_argument("--dry-run", action="store_true", help="Print steps without executing")
    args = parser.parse_args()

    try:
        summary = run_pipeline(
            run_date=args.date,
            project_id=args.project,
            raw_bucket=args.bucket,
            event_limit=args.limit,
            dry_run=args.dry_run,
        )
        print("\n=== Pipeline Summary ===")
        for k, v in summary.items():
            print(f"  {k}: {v}")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
