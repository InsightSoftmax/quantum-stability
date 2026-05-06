"""
Data loader: cross-platform summary for the overview page.
"""
import json
import sys
from pathlib import Path

import pandas as pd

repo_root = Path(__file__).parents[3]

PLATFORMS = {
    "aqt":        {"backend": "IBEX",     "status": "active",     "cost_per_run_usd": 25.07},
    "ibm":        {"backend": "Brisbane", "status": "historical", "cost_per_run_usd": None},
    "ionq":       {"backend": "Aria-1",  "status": "historical", "cost_per_run_usd": 33.00,
                   "csv_key": "ionq", "backend_filter": "Aria"},
    "ionq_forte_direct": {"backend": "Forte-1 (direct)", "status": "historical", "cost_per_run_usd": 259.00,
                          "csv_key": "ionq", "backend_filter": "Forte"},
    "ionq_forte_braket": {"backend": "Forte-1 (Braket)", "status": "active", "cost_per_run_usd": 83.00,
                          "csv_key": "ionq_braket"},
    "rigetti_ankaa":   {"backend": "Ankaa-3",        "status": "historical", "cost_per_run_usd": 3.90,
                        "csv_key": "rigetti", "backend_filter": "Ankaa"},
    "rigetti_cepheus": {"backend": "Cepheus-1-108Q", "status": "active",    "cost_per_run_usd": 3.43,
                        "csv_key": "rigetti", "backend_filter": "Cepheus"},
    "aqt_braket":      {"backend": "IBEX (Braket)", "status": "active",     "cost_per_run_usd": 26.50,
                        "csv_key": "aqt_braket"},
    "iqm_braket":      {"backend": "Garnet",        "status": "active",     "cost_per_run_usd": 4.45,
                        "csv_key": "iqm_braket"},
}

summary = []

for platform, meta in PLATFORMS.items():
    csv_key = meta.get("csv_key", platform)
    csv_path = repo_root / "data" / csv_key / "results.csv"
    if not csv_path.exists():
        summary.append({
            "platform": platform, "backend": meta["backend"], "status": meta["status"],
            "cost_per_run_usd": meta["cost_per_run_usd"],
            "latest_run": None, "latest_success": None, "overall_mean": None,
            "n_runs": 0, "n_circuits": 0, "sparkline": [],
        })
        continue

    df = pd.read_csv(csv_path, parse_dates=["run_date"], dtype={"input_bits": str})
    df = df[~df["notes"].fillna("").str.contains("dry_run|simulator")]

    backend_filter = meta.get("backend_filter")
    if backend_filter:
        df = df[df["backend"].str.contains(backend_filter, na=False)]

    if df.empty:
        summary.append({
            "platform": platform,
            "backend": meta["backend"],
            "status": meta["status"],
            "cost_per_run_usd": meta["cost_per_run_usd"],
            "latest_run": None,
            "latest_success": None,
            "overall_mean": None,
            "n_runs": 0,
            "n_circuits": 0,
            "sparkline": [],
        })
        continue

    runs = (
        df.groupby("run_date")["success_probability"]
        .agg(success_probability="mean", std_success="std")
        .reset_index()
        .sort_values("run_date")
    )
    runs["std_success"] = runs["std_success"].fillna(0.0)

    sparkline = [
        {
            "date": row["run_date"].strftime("%Y-%m-%d"),
            "value": round(float(row["success_probability"]), 4),
            "std": round(float(row["std_success"]), 4),
        }
        for _, row in runs.iterrows()
    ]

    latest_run = runs["run_date"].max()
    latest_success = runs.loc[runs["run_date"] == latest_run, "success_probability"].values[0]

    summary.append({
        "platform": platform,
        "backend": meta["backend"],
        "status": meta["status"],
        "cost_per_run_usd": meta["cost_per_run_usd"],
        "latest_run": latest_run.strftime("%Y-%m-%d"),
        "latest_success": round(float(latest_success), 4),
        "overall_mean": round(float(df["success_probability"].mean()), 4),
        "n_runs": int(runs.shape[0]),
        "n_circuits": int(df.shape[0]),
        "sparkline": sparkline,
    })

json.dump(summary, sys.stdout)
