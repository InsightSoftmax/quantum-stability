"""
Backfill qpu_execution_sec for existing Rigetti rows from S3 result JSONs.

Each Rigetti Braket task result JSON contains:
    additionalMetadata.rigettiMetadata.nativeQuilMetadata.programDuration

programDuration is in microseconds and represents actual QPU execution time —
not including queue wait, S3 overhead, or any other infrastructure latency.

The script reads the Rigetti CSV, downloads each task's result.json from S3,
extracts programDuration, and rewrites the CSV with a populated qpu_execution_sec
column.  Rows already having a value are skipped.  ARNs from older Ankaa-3 runs
and Cepheus runs are both handled (both used the same bucket/prefix).

Prerequisites:
    AWS credentials with s3:GetObject on amazon-braket-isc-condenser-west

Usage:
    uv run python scripts/backfill_rigetti_execution_time.py [--dry-run]
"""

import argparse
import csv
import json
import sys
from pathlib import Path

BUCKET = "amazon-braket-isc-condenser-west"
PREFIX = "condenser-results"
CSV_PATH = Path("data/rigetti/results.csv")

FIELDNAMES = [
    "run_date", "platform", "backend", "input_bits", "circuit_length",
    "shots", "counts_json", "success_probability", "job_id",
    "job_start_time", "job_end_time", "qpu_execution_sec", "sdk_version", "notes",
]


def task_id_from_arn(arn: str) -> str:
    """Extract the UUID from a Braket task ARN."""
    return arn.split("/")[-1]


def fetch_program_duration(s3, task_id: str) -> float | None:
    key = f"{PREFIX}/{task_id}/results.json"
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=key)
        data = json.loads(obj["Body"].read())
        duration_us = (
            data.get("additionalMetadata", {})
            .get("rigettiMetadata", {})
            .get("nativeQuilMetadata", {})
            .get("programDuration")
        )
        if duration_us is None:
            return None
        return round(float(duration_us) / 1_000_000, 9)
    except s3.exceptions.NoSuchKey:
        print(f"  [missing] {task_id}", flush=True)
        return None
    except Exception as e:
        print(f"  [error] {task_id}: {e}", flush=True)
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be done without writing anything")
    args = parser.parse_args()

    import boto3
    s3 = boto3.client("s3", region_name="us-west-1")

    rows = list(csv.DictReader(CSV_PATH.open()))
    needs_backfill = [r for r in rows if not r.get("qpu_execution_sec")]
    print(f"{len(rows)} total rows, {len(needs_backfill)} need backfill")

    if not needs_backfill:
        print("Nothing to do.")
        return

    updated = 0
    for i, row in enumerate(rows):
        if row.get("qpu_execution_sec"):
            continue
        job_id = row.get("job_id", "")
        if not job_id or not job_id.startswith("arn:"):
            continue  # dry_run or simulator row — skip

        task_id = task_id_from_arn(job_id)
        qpu_sec = fetch_program_duration(s3, task_id)
        if qpu_sec is not None:
            row["qpu_execution_sec"] = qpu_sec
            updated += 1
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(rows)} processed, {updated} updated so far…", flush=True)

    print(f"\nBackfilled {updated} rows.")

    if args.dry_run:
        print("Dry run — not writing CSV.")
        return

    with CSV_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})

    print(f"Wrote {CSV_PATH}")


if __name__ == "__main__":
    main()
