"""
Data loader: Rigetti Cepheus-1-108Q results (from April 2026 onwards).
Reads data/rigetti/results.csv and filters to Cepheus rows.
"""
import json
import sys
from pathlib import Path

import pandas as pd

repo_root = Path(__file__).parents[3]
csv_path = repo_root / "data" / "rigetti" / "results.csv"

if not csv_path.exists():
    json.dump({"runs": [], "circuits": [], "by_length": [], "by_input": [], "incidents": []}, sys.stdout)
    sys.exit(0)

df = pd.read_csv(csv_path, parse_dates=["run_date"], dtype={"input_bits": str})

# Exclude simulator/dry-run rows; filter to Cepheus device
df = df[~df["notes"].fillna("").str.contains("dry_run|simulator")]
df = df[df["backend"].str.contains("Cepheus", na=False)]

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

inc_path = repo_root / "incidents" / "rigetti" / "incidents.csv"
incidents = pd.read_csv(inc_path, dtype=str).fillna("").to_dict(orient="records") if inc_path.exists() else []

output = {
    "platform": "rigetti_cepheus",
    "backend": "Cepheus-1-108Q",
    "runs": runs.to_dict(orient="records"),
    "circuits": circuits.to_dict(orient="records"),
    "by_length": by_length.to_dict(orient="records"),
    "by_input": by_input.to_dict(orient="records"),
    "incidents": incidents,
}

json.dump(output, sys.stdout)
