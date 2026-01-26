import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict


def write_to_local(
    records: List[Dict],
    run_date: str,
    base_dir: str = "data/raw/github_events",
) -> None:
    out_dir = Path(base_dir) / f"dt={run_date}"
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"events_{ts}.jsonl"

    with out_file.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
