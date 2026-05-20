"""
Data loader: cross-platform summary for the overview page.
"""
import json
import sys
from pathlib import Path

import pandas as pd

repo_root = Path(__file__).parents[3]

PLATFORMS = {
    "aqt":             {"backend": "IBEX",          "status": "active",     "cost_per_run_usd": 25.07},
    "ibm_brisbane":    {"backend": "Brisbane",      "status": "historical", "cost_per_run_usd": None,
                        "csv_key": "ibm_brisbane"},
    "ibm_pittsburgh":  {"backend": "Pittsburgh",    "status": "active",     "cost_per_run_usd": 22.00,
                        "csv_key": "ibm_pittsburgh"},
    "ibm_marrakesh":   {"backend": "Marrakesh",     "status": "active",     "cost_per_run_usd": 27.00,
                        "csv_key": "ibm_marrakesh"},
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

    # Per-run workload duration: max(job_end_time) − min(job_start_time) per run
    timing_sparkline = []
    median_duration_min = None
    df_t = df[df["job_start_time"].notna() & df["job_end_time"].notna()].copy()
    if not df_t.empty:
        df_t["job_start_time"] = pd.to_datetime(df_t["job_start_time"], utc=True)
        df_t["job_end_time"] = pd.to_datetime(df_t["job_end_time"], utc=True)
        timing = (
            df_t.groupby("run_date")
            .apply(lambda g: (g["job_end_time"].max() - g["job_start_time"].min()).total_seconds() / 60,
                   include_groups=False)
            .reset_index()
        )
        timing.columns = ["run_date", "duration_min"]
        timing_sparkline = [
            {"date": row["run_date"].strftime("%Y-%m-%d"), "duration_min": round(float(row["duration_min"]), 3)}
            for _, row in timing.iterrows()
        ]
        median_duration_min = round(float(timing["duration_min"].median()), 3)

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
        "timing_sparkline": timing_sparkline,
        "median_duration_min": median_duration_min,
    })

json.dump(summary, sys.stdout)
