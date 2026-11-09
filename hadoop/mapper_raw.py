#!/usr/bin/env python3
"""Map raw BikeFlow trip CSV rows to station-hour pickup aggregates."""
import csv
import sys
from datetime import datetime

reader = csv.DictReader(sys.stdin)
for row in reader:
    try:
        started = datetime.fromisoformat(row["started_at"])
        ended = datetime.fromisoformat(row["ended_at"])
        duration = (ended - started).total_seconds() / 60
        station = row["start_station_id"].strip()
        member = int(row["member_type"].strip().lower() == "member")
        if not station or not 1 <= duration <= 1440:
            continue
    except (KeyError, TypeError, ValueError):
        continue
    print(f"{station}\t{started:%Y-%m-%d %H}\t1\t{duration}\t{member}")
