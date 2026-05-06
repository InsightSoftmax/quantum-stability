"""
Data loader: IQM Garnet (via AWS Braket) results.
"""
import json
import sys
from pathlib import Path

import pandas as pd

repo_root = Path(__file__).parents[3]
csv_path = repo_root / "data" / "iqm_braket" / "results.csv"

if not csv_path.exists():
    json.dump({"runs": [], "circuits": [], "by_length": [], "by_input": [], "incidents": []}, sys.stdout)
    sys.exit(0)

df = pd.read_csv(csv_path, parse_dates=["run_date"], dtype={"input_bits": str})
df = df[~df["notes"].fillna("").str.contains("dry_run|simulator")]

if df.empty:
    json.dump({"runs": [], "circuits": [], "by_length": [], "by_input": [], "incidents": []}, sys.stdout)
    sys.exit(0)

runs = (
    df.groupby("run_date")["success_probability"]
    .agg(mean_success="mean", std_success="std", n_circuits="count")
    .reset_index()
    .sort_values("run_date")
)
runs["run_date"] = runs["run_date"].dt.strftime("%Y-%m-%d")
runs["mean_success"] = runs["mean_success"].round(4)
runs["std_success"] = runs["std_success"].fillna(0).round(4)

circuits = df[["run_date", "input_bits", "circuit_length", "success_probability", "job_end_time"]].copy()
circuits["run_date"] = circuits["run_date"].dt.strftime("%Y-%m-%d")
circuits = circuits.astype(object).where(pd.notnull(circuits), None)

by_length = (
    df.groupby("circuit_length")["success_probability"]
    .agg(mean_success="mean", std_success="std", n="count", median="median")
    .reset_index()
    .rename(columns={"circuit_length": "length"})
).round(4)

by_input = (
    df.groupby("input_bits")["success_probability"]
    .agg(mean_success="mean", std_success="std", n="count")
    .reset_index()
).round(4)

inc_path = repo_root / "incidents" / "iqm_braket" / "incidents.csv"
incidents = pd.read_csv(inc_path, dtype=str).fillna("").to_dict(orient="records") if inc_path.exists() else []

output = {
    "platform": "iqm_braket",
    "backend": "IQM Garnet",
    "runs": runs.to_dict(orient="records"),
    "circuits": circuits.to_dict(orient="records"),
    "by_length": by_length.to_dict(orient="records"),
    "by_input": by_input.to_dict(orient="records"),
    "incidents": incidents,
}

json.dump(output, sys.stdout)
