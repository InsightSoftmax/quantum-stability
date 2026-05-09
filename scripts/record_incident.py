"""
Helper for recording platform incidents to incidents/<platform>/incidents.csv.

Incident types:
  platform_offline    — QPU was unreachable or explicitly offline/retired
  automation_error    — our code, credentials, or infrastructure failed
  planned_transition  — known platform change (retirement, upgrade, replacement)
  queue_timeout       — jobs submitted but never completed within the timeout window
"""

import csv
from datetime import date
from pathlib import Path

INCIDENT_FIELDNAMES = ["incident_date", "platform", "type", "error_message", "notes"]
INCIDENT_TYPES = {"platform_offline", "automation_error", "planned_transition", "queue_timeout"}

_OFFLINE_KEYWORDS = [
    "offline", "not available", "unavailable", "retired", "device_retired",
    "deviceretired", "deviceoffline", "no devices available", "maintenance",
]


def classify_error(exc: Exception) -> str:
    """Heuristically classify an exception as platform_offline or automation_error."""
    msg = str(exc).lower()
    type_name = type(exc).__name__.lower()
    if any(kw in msg for kw in _OFFLINE_KEYWORDS) or any(kw in type_name for kw in _OFFLINE_KEYWORDS):
        return "platform_offline"
    return "automation_error"


def record_incident(
    platform: str,
    incident_type: str,
    error_message: str = "",
    notes: str = "",
    incident_date: str | None = None,
) -> Path:
    """
    Append one incident row to incidents/<platform>/incidents.csv.
    Creates the file (with header) if it doesn't exist yet.
    Returns the path written.
    """
    if incident_type not in INCIDENT_TYPES:
        raise ValueError(f"Unknown incident type {incident_type!r}. Must be one of {INCIDENT_TYPES}")

    if incident_date is None:
        incident_date = date.today().isoformat()

    out_path = Path("incidents") / platform / "incidents.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not out_path.exists() or out_path.stat().st_size == 0

    with out_path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=INCIDENT_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "incident_date": incident_date,
            "platform": platform,
            "type": incident_type,
            "error_message": str(error_message)[:500],
            "notes": notes,
        })

    print(f"  Recorded {incident_type} incident for {platform} on {incident_date}")
    return out_path
