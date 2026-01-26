import argparse
from typing import List, Dict
import time
import requests
from datetime import datetime
from typing import Optional


GITHUB_EVENTS_API = "https://api.github.com/events"
DEFAULT_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "cloud-native-enterprise-data-platform",
}


def _get_next_link(link_header: Optional[str]) -> Optional[str]:
    """
    Parse GitHub Link header and return next page URL if exists.
    """
    if not link_header:
        return None

    parts = link_header.split(",")
    for part in parts:
        section = part.split(";")
        if len(section) < 2:
            continue
        url_part = section[0].strip()
        rel_part = section[1].strip()
        if rel_part == 'rel="next"':
            return url_part.strip("<>")

    return None


def fetch_events(run_date: str, limit: Optional[int] = None) -> List[Dict]:
    """
    Fetch GitHub public events with pagination and basic rate limit handling.
    """
    events: List[Dict] = []
    url: Optional[str] = GITHUB_EVENTS_API

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    while url:
        resp = session.get(url, timeout=30)

        # ---- Rate limit handling ----
        if resp.status_code == 403 and "X-RateLimit-Remaining" in resp.headers:
            reset_ts = int(resp.headers.get("X-RateLimit-Reset", "0"))
            sleep_seconds = max(reset_ts - int(time.time()), 1)
            print(f"Rate limit hit. Sleeping {sleep_seconds}s...")
            time.sleep(sleep_seconds)
            continue

        resp.raise_for_status()

        page_events = resp.json()
        if not isinstance(page_events, list):
            break

        for ev in page_events:
            # optional ingestion timestamp (very useful later)
            ev["_ingested_at"] = datetime.utcnow().isoformat()
            events.append(ev)

            if limit and len(events) >= limit:
                return events

        # ---- pagination ----
        url = _get_next_link(resp.headers.get("Link"))

        # safety sleep to be nice to API
        time.sleep(0.5)

    return events

def write_raw(records: List[Dict], sink: str, run_date: str, **kwargs) -> None:
    if sink == "local":
        from ingestion.sinks.local_sink import write_to_local
        write_to_local(records, run_date=run_date, **kwargs)
    elif sink == "gcs":
        from ingestion.sinks.gcs_sink import write_to_gcs
        write_to_gcs(records, run_date=run_date, **kwargs)
    else:
        raise ValueError(f"Unsupported sink: {sink}")


def main() -> None:
    parser = argparse.ArgumentParser(description="API ingestion to raw layer")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--sink", default="local", choices=["local", "gcs"])
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    records = fetch_events(args.date, args.limit)
    write_raw(records, sink=args.sink, run_date=args.date)


if __name__ == "__main__":
    main()
