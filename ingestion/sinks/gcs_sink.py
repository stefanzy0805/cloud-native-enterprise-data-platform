import json
import logging
from datetime import datetime
from typing import List, Dict

from google.cloud import storage

logger = logging.getLogger(__name__)


def write_to_gcs(
    records: List[Dict],
    run_date: str,
    bucket: str | None = None,
    prefix: str = "raw/github_events",
) -> str:
    """
    Write records to GCS as newline-delimited JSON (JSONL).

    Path: gs://{bucket}/{prefix}/dt={run_date}/{timestamp}.jsonl

    Returns the GCS URI of the written file.
    """
    if not bucket:
        raise ValueError("GCS bucket must be provided")
    if not records:
        logger.warning("No records to write, skipping GCS upload")
        return ""

    client = storage.Client()
    gcs_bucket = client.bucket(bucket)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    blob_name = f"{prefix}/dt={run_date}/{ts}.jsonl"
    blob = gcs_bucket.blob(blob_name)

    content = "\n".join(json.dumps(r, default=str) for r in records)
    blob.upload_from_string(content, content_type="application/x-ndjson")

    uri = f"gs://{bucket}/{blob_name}"
    logger.info(f"Wrote {len(records)} records to {uri}")
    return uri
