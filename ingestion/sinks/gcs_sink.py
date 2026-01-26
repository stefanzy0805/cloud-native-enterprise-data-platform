from typing import List, Dict


def write_to_gcs(
    records: List[Dict],
    run_date: str,
    bucket: str | None = None,
    prefix: str = "raw/github_events",
) -> None:
    if not bucket:
        raise ValueError("GCS bucket must be provided")
    raise NotImplementedError("GCS sink not implemented yet")
