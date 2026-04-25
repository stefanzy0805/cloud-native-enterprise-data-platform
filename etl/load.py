"""
ETL Step 1: Load raw JSONL files from GCS into BigQuery raw dataset.

Usage:
    python -m etl.load --date 2024-01-15 --project gcp-lab-data-engineering
"""
import argparse
import logging
from datetime import datetime

from google.cloud import bigquery

logger = logging.getLogger(__name__)


def load_gcs_to_bq(
    project_id: str,
    run_date: str,
    source_bucket: str,
    prefix: str = "raw/github_events",
    dataset: str = "raw",
    table: str = "github_events",
) -> int:
    """
    Load JSONL files from GCS into BigQuery raw table using a load job.

    Strategy: WRITE_APPEND — supports idempotent re-runs when source files
    are immutable (GCS objects are append-only per run_date partition).
    """
    client = bigquery.Client(project=project_id)

    source_uri = f"gs://{source_bucket}/{prefix}/dt={run_date}/*.jsonl"
    destination = f"{project_id}.{dataset}.{table}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=False,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        # Partition decorator: load only into the correct day partition
        time_partitioning=bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="_ingested_at",
        ),
        ignore_unknown_values=True,
        max_bad_records=100,
    )

    table_ref = bigquery.TableReference.from_string(destination)
    load_job = client.load_table_from_uri(
        source_uri,
        table_ref,
        job_config=job_config,
    )

    logger.info(f"Load job started: {load_job.job_id} | source={source_uri}")
    load_job.result()  # Wait for completion

    table_obj = client.get_table(table_ref)
    logger.info(
        f"Load complete | job={load_job.job_id} | "
        f"rows_loaded={load_job.output_rows} | "
        f"total_rows={table_obj.num_rows}"
    )
    return load_job.output_rows


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Load raw GCS data into BigQuery")
    parser.add_argument("--date",    required=True, help="YYYY-MM-DD")
    parser.add_argument("--project", default="gcp-lab-data-engineering")
    parser.add_argument("--bucket",  default=None, help="Override raw GCS bucket name")
    args = parser.parse_args()

    bucket = args.bucket or f"{args.project}-datalake-raw"
    rows = load_gcs_to_bq(
        project_id=args.project,
        run_date=args.date,
        source_bucket=bucket,
    )
    print(f"Loaded {rows} rows for {args.date}")


if __name__ == "__main__":
    main()
