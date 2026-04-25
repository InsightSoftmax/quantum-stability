"""
Data loader: AQT IBEX results.
Reads data/aqt/results.csv (relative to repo root) and outputs processed JSON.
"""
import json
import sys
from pathlib import Path

import pandas as pd

repo_root = Path(__file__).parents[3]
csv_path = repo_root / "data" / "aqt" / "results.csv"

if not csv_path.exists():
    json.dump({"runs": [], "circuits": [], "by_length": [], "by_input": []}, sys.stdout)
    sys.exit(0)

df = pd.read_csv(csv_path, parse_dates=["run_date"], dtype={"input_bits": str})

# Exclude simulator/dry-run rows
df = df[~df["notes"].fillna("").str.contains("dry_run|simulator")]

if df.empty:
    json.dump({"runs": [], "circuits": [], "by_length": [], "by_input": []}, sys.stdout)
    sys.exit(0)

# Per-run aggregates (one row per run_date)
runs = (
    df.groupby("run_date")["success_probability"]
    .agg(mean_success="mean", std_success="std", n_circuits="count")
    .reset_index()
    .sort_values("run_date")
)
runs["run_date"] = runs["run_date"].dt.strftime("%Y-%m-%d")
runs["mean_success"] = runs["mean_success"].round(4)
runs["std_success"] = runs["std_success"].fillna(0).round(4)

# Per-circuit detail (for breakdowns)
circuits = df[["run_date", "input_bits", "circuit_length", "success_probability", "job_end_time"]].copy()
circuits["run_date"] = circuits["run_date"].dt.strftime("%Y-%m-%d")
circuits["job_end_time"] = None  # AQT doesn't record job timing

# Aggregated by circuit length
by_length = (
    df.groupby("circuit_length")["success_probability"]
    .agg(mean_success="mean", std_success="std", n="count", median="median")
    .reset_index()
    .rename(columns={"circuit_length": "length"})
)
by_length["std_success"] = by_length["std_success"].fillna(0)
by_length = by_length.round(4)

# Aggregated by input state
by_input = (
    df.groupby("input_bits")["success_probability"]
    .agg(mean_success="mean", std_success="std", n="count")
    .reset_index()
)
by_input["std_success"] = by_input["std_success"].fillna(0)
by_input = by_input.round(4)

output = {
    "platform": "aqt",
    "backend": "IBEX",
    "runs": runs.to_dict(orient="records"),
    "circuits": circuits.to_dict(orient="records"),
    "by_length": by_length.to_dict(orient="records"),
    "by_input": by_input.to_dict(orient="records"),
}

json.dump(output, sys.stdout)
