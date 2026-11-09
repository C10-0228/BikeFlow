#!/usr/bin/env python3
import csv, sys
FIELDS = [
    "weather_time", "ride_id", "rideable_type", "started_at", "ended_at",
    "start_station_id", "start_station_name", "end_station_id", "end_station_name",
    "start_lat", "start_lng", "end_lat", "end_lng", "member_type", "duration_min",
    "event_date", "event_hour", "day_of_week", "is_weekend", "temperature",
    "precipitation", "wind_speed", "weather_missing",
]

for row in csv.DictReader(sys.stdin, fieldnames=FIELDS):
    try:
        if row["ride_id"] == "ride_id":
            continue
        station = row["start_station_id"].strip()
        hour = row["started_at"][:13]
        duration = float(row["duration_min"])
        member = int(row["member_type"] == "member")
        if not station or len(hour) != 13:
            continue
    except (KeyError, TypeError, ValueError):
        continue
    print(f"{station}\t{hour}\t1\t{duration}\t{member}")

