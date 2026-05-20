"""
Fetch QPU execution time (seconds) for IBM Pittsburgh and IBM Marrakesh jobs.

Usage:
    uv run python scripts/fetch_ibm_costs.py

Required environment variables:
    IBM_QUANTUM_TOKEN            — IBM Cloud API key (shared by both platforms)
    IBM_QUANTUM_INSTANCE_PAYG    — CRN for the pay-as-you-go instance (Pittsburgh)
    IBM_QUANTUM_INSTANCE_OPEN    — CRN for the open-plan instance (Marrakesh)

Pricing note:
    IBM Standard Plan is approximately $1.60 per QPU second (verify against your
    actual billing dashboard — rates can change and may differ by plan tier).
    Multiply total_seconds × your $/second rate to estimate cost per run.
"""

import csv
import os
from collections import defaultdict

from qiskit_ibm_runtime import QiskitRuntimeService

DATA_FILES = {
    "ibm_pittsburgh": "data/ibm_pittsburgh/results.csv",
    "ibm_marrakesh": "data/ibm_marrakesh/results.csv",
}

INSTANCE_ENV = {
    "ibm_pittsburgh": "IBM_QUANTUM_INSTANCE_PAYG",
    "ibm_marrakesh": "IBM_QUANTUM_INSTANCE_OPEN",
}

APPROX_RATE_PER_SECOND = 1.60  # USD — verify against your IBM billing dashboard


def load_jobs_by_run_date(csv_path: str) -> dict[str, list[str]]:
    """Read a results CSV and return {run_date: [job_id, ...]}."""
    jobs_by_date: dict[str, list[str]] = defaultdict(list)
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            job_id = row.get("job_id", "").strip()
            run_date = row.get("run_date", "").strip()
            if job_id and run_date:
                jobs_by_date[run_date].append(job_id)
    return dict(jobs_by_date)


def fetch_metrics_for_platform(platform: str, jobs_by_date: dict[str, list[str]]) -> None:
    token = os.environ.get("IBM_QUANTUM_TOKEN", "")
    instance_env = INSTANCE_ENV[platform]
    instance = os.environ.get(instance_env, "")

    if not token:
        print(f"[{platform}] ERROR: IBM_QUANTUM_TOKEN not set — skipping.")
        return
    if not instance:
        print(f"[{platform}] ERROR: {instance_env} not set — skipping.")
        return

    print(f"\n{'=' * 60}")
    print(f"Platform: {platform}  (instance env: {instance_env})")
    print(f"{'=' * 60}")

    service = QiskitRuntimeService(channel="ibm_cloud", token=token, instance=instance)

    for run_date in sorted(jobs_by_date):
        job_ids = jobs_by_date[run_date]
        print(f"\n  Run date: {run_date}  ({len(job_ids)} jobs)")

        total_seconds = 0.0
        any_missing = False

        for job_id in job_ids:
            try:
                job = service.job(job_id)
                metrics = job.metrics()
                timestamps = metrics.get("timestamps", {})
                usage = metrics.get("usage", {})
                seconds = usage.get("seconds")

                if seconds is None:
                    print(f"    {job_id}  — seconds: N/A (no usage.seconds in metrics)")
                    any_missing = True
                else:
                    total_seconds += seconds
                    start = timestamps.get("running", "?")
                    end = timestamps.get("finished", "?")
                    print(f"    {job_id}  seconds={seconds:.3f}  [{start} → {end}]")

            except Exception as exc:
                print(f"    {job_id}  — ERROR: {exc}")
                any_missing = True

        if not any_missing:
            est_cost = total_seconds * APPROX_RATE_PER_SECOND
            print(
                f"\n  SUMMARY  run_date={run_date}  platform={platform}"
                f"  total_seconds={total_seconds:.3f}"
                f"  est_cost≈${est_cost:.2f} (@${APPROX_RATE_PER_SECOND}/s — verify against billing)"
            )
        else:
            print(
                f"\n  SUMMARY  run_date={run_date}  platform={platform}"
                f"  total_seconds={total_seconds:.3f} (partial — some jobs missing)"
            )


def main() -> None:
    # Resolve CSV paths relative to the repo root (parent of scripts/)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for platform, rel_path in DATA_FILES.items():
        csv_path = os.path.join(repo_root, rel_path)
        if not os.path.exists(csv_path):
            print(f"[{platform}] CSV not found: {csv_path} — skipping.")
            continue
        jobs_by_date = load_jobs_by_run_date(csv_path)
        if not jobs_by_date:
            print(f"[{platform}] No job IDs found in {csv_path} — skipping.")
            continue
        fetch_metrics_for_platform(platform, jobs_by_date)

    print("\nDone.")


if __name__ == "__main__":
    main()
