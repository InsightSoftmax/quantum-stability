"""
Submit benchmark circuits to all enabled platforms.

Saves a pending JSON file per platform run to pending/<platform>/<run_date>.json.
Does NOT wait for results — the collect_results.py script handles that.

Usage:
    uv run python scripts/submit_benchmark.py                  # real QPU
    uv run python scripts/submit_benchmark.py --dry-run        # local simulator, no cloud
    uv run python scripts/submit_benchmark.py --simulator      # cloud simulator (SV1 / AQT simulator_noise)
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.record_incident import classify_error, record_incident

# Platforms to run. Currently Rigetti and AQT are run manually by Arash —
# uncomment here once the GitHub Actions workflow is wired up end-to-end.
ENABLED_PLATFORMS = [
    "rigetti_braket",  # active: Rigetti Ankaa-3 via AWS Braket (us-west-1)
    "aqt_qiskit",      # active: AQT via qiskit-aqt-provider; requires AQT_API_KEY secret
    # "ionq_braket",   # paused: budget
    # "ibm_qiskit",    # pending: locate Sami's notebook and existing results
]


def get_platforms() -> list[str]:
    env = os.environ.get("PLATFORM", "").strip()
    if env:
        return [p.strip() for p in env.split(",") if p.strip()]
    return ENABLED_PLATFORMS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Submit benchmark circuits")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run", action="store_true",
        default=os.environ.get("DRY_RUN", "false").lower() == "true",
        help="Run against local simulators only (no cloud calls, no cost)",
    )
    mode.add_argument(
        "--simulator", action="store_true",
        default=os.environ.get("USE_SIMULATOR", "false").lower() == "true",
        help="Run against cloud simulators (Braket SV1 / AQT simulator_noise); "
             "requires credentials but no QPU cost",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    platforms = get_platforms()
    run_date = date.today().isoformat()

    if not platforms:
        print("No platforms enabled. Edit ENABLED_PLATFORMS in scripts/submit_benchmark.py")
        return

    mode = "dry-run" if args.dry_run else "simulator" if args.simulator else "QPU"
    print(f"Submitting benchmarks for: {platforms}")
    print(f"Run date: {run_date}  |  Mode: {mode}")

    failed = []
    for platform_name in platforms:
        print(f"\n=== {platform_name} ===")
        try:
            module = __import__(f"benchmarks.{platform_name}", fromlist=["submit"])
            pending = module.submit(
                n_circuits=10, shots=100,
                dry_run=args.dry_run,
                use_simulator=args.simulator,
            )

            out_path = Path("pending") / platform_name / f"{run_date}.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(pending, indent=2, default=str))
            print(f"  Saved {len(pending['jobs'])} job IDs to {out_path}")

        except Exception as e:
            print(f"  ERROR: {e}")
            # Use the platform key from the module if available, else fall back to module name
            try:
                mod = __import__(f"benchmarks.{platform_name}", fromlist=["PLATFORM"])
                platform_key = mod.PLATFORM
            except Exception:
                platform_key = platform_name
            record_incident(
                platform=platform_key,
                incident_type=classify_error(e),
                error_message=str(e),
                incident_date=run_date,
            )
            failed.append(platform_name)

    if failed:
        print(f"\nFailed platforms: {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main()
