"""
Check pending jobs and collect results for any that have completed.

Reads all files under pending/<platform>/*.json.
For each batch where all jobs are done, appends results to data/<platform>/results.csv
and removes the pending file.

Designed to run on a schedule (e.g., every 6 hours) until results arrive,
regardless of how long the queue is.

Usage:
    uv run python scripts/collect_results.py
"""

import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.record_incident import classify_error, record_incident

FIELDNAMES = [
    "run_date", "platform", "backend", "input_bits", "circuit_length",
    "shots", "counts_json", "success_probability", "job_id",
    "job_start_time", "job_end_time", "sdk_version", "notes",
]

# Pending batches older than this are timed out and recorded as queue_timeout incidents.
MAX_PENDING_DAYS = 14


def append_results(platform: str, results: list[dict]) -> None:
    out_path = Path("data") / platform / "results.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not out_path.exists()
    with out_path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})
    print(f"  Wrote {len(results)} rows to {out_path}")


def is_timed_out(pending: dict) -> bool:
    submitted_at = pending.get("submitted_at")
    if not submitted_at:
        return False
    try:
        submitted = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        age_days = (datetime.now(UTC) - submitted).days
        return age_days >= MAX_PENDING_DAYS
    except (ValueError, TypeError):
        return False


def main() -> None:
    pending_root = Path("pending")
    if not pending_root.exists():
        print("No pending directory found. Nothing to collect.")
        return

    pending_files = sorted(pending_root.glob("*/*.json"))
    if not pending_files:
        print("No pending jobs found.")
        return

    print(f"Found {len(pending_files)} pending batch(es).")
    any_still_waiting = False

    for pending_path in pending_files:
        platform_name = pending_path.parent.name
        print(f"\n=== {platform_name} / {pending_path.name} ===")

        pending = json.loads(pending_path.read_text())

        # Queue timeout: batch has been waiting too long
        if is_timed_out(pending):
            msg = f"Pending batch {pending_path.name} exceeded {MAX_PENDING_DAYS}-day timeout"
            print(f"  TIMEOUT: {msg}")
            record_incident(
                platform=pending.get("platform", platform_name),
                incident_type="queue_timeout",
                error_message=msg,
                notes=f"Submitted at {pending.get('submitted_at', 'unknown')}; {len(pending.get('jobs', []))} jobs",
                incident_date=pending.get("run_date"),
            )
            pending_path.unlink()
            continue

        try:
            module = __import__(f"benchmarks.{platform_name}", fromlist=["collect"])
            results = module.collect(pending)
        except RuntimeError as e:
            print(f"  FAILED: {e}")
            record_incident(
                platform=pending.get("platform", platform_name),
                incident_type=classify_error(e),
                error_message=str(e),
                incident_date=pending.get("run_date"),
            )
            pending_path.unlink()
            continue
        except Exception as e:
            print(f"  ERROR: {e}")
            record_incident(
                platform=pending.get("platform", platform_name),
                incident_type="automation_error",
                error_message=str(e),
                incident_date=pending.get("run_date"),
            )
            raise

        if results is None:
            print("  Still waiting.")
            any_still_waiting = True
        else:
            append_results(pending["platform"], results)
            pending_path.unlink()
            print(f"  Done. Removed {pending_path}")

    if any_still_waiting:
        print("\nSome batches are still pending. Re-run this script later.")
    else:
        print("\nAll pending batches collected.")


if __name__ == "__main__":
    main()
