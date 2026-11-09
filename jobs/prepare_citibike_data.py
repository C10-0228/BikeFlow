"""Normalize Citi Bike monthly archives and Open-Meteo hourly weather data."""
from pathlib import Path
import argparse
import json
import zipfile

import pandas as pd


TRIP_COLUMNS = {
    "ride_id": "ride_id",
    "rideable_type": "rideable_type",
    "started_at": "started_at",
    "ended_at": "ended_at",
    "start_station_id": "start_station_id",
    "start_station_name": "start_station_name",
    "end_station_id": "end_station_id",
    "end_station_name": "end_station_name",
    "start_lat": "start_lat",
    "start_lng": "start_lng",
    "end_lat": "end_lat",
    "end_lng": "end_lng",
    "member_casual": "member_type",
}
REQUIRED_TRIP_COLUMNS = {
    "ride_id", "started_at", "ended_at", "start_station_id",
    "end_station_id", "member_casual",
}
TRIP_OUTPUT_COLUMNS = list(TRIP_COLUMNS.values())


def normalize_trips(archives, output, chunksize=500_000):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output.with_suffix(output.suffix + ".tmp")
    if temporary_output.exists():
        temporary_output.unlink()

    total = 0
    wrote_header = False
    for archive in sorted(map(Path, archives)):
        with zipfile.ZipFile(archive) as zf:
            csv_members = [name for name in zf.namelist() if name.lower().endswith(".csv")]
            if not csv_members:
                raise ValueError(f"No CSV found in {archive}")
            for member in sorted(csv_members):
                with zf.open(member) as stream:
                    header = pd.read_csv(stream, nrows=0).columns.tolist()
                missing = REQUIRED_TRIP_COLUMNS - set(header)
                if missing:
                    raise ValueError(f"{archive}:{member} is missing columns: {sorted(missing)}")
                usecols = [name for name in TRIP_COLUMNS if name in header]
                dtypes = {
                    name: "string"
                    for name in usecols
                    if name.endswith("_id") or name in {"ride_id", "member_casual"}
                }
                with zf.open(member) as stream:
                    for chunk in pd.read_csv(stream, usecols=usecols, dtype=dtypes, chunksize=chunksize):
                        chunk = chunk.rename(columns=TRIP_COLUMNS)
                        if "rideable_type" not in chunk:
                            chunk["rideable_type"] = "unknown"
                        for column in TRIP_OUTPUT_COLUMNS:
                            if column not in chunk:
                                chunk[column] = pd.NA
                        chunk["member_type"] = chunk["member_type"].str.lower()
                        chunk = chunk[TRIP_OUTPUT_COLUMNS]
                        chunk.to_csv(temporary_output, mode="a", index=False, header=not wrote_header)
                        wrote_header = True
                        total += len(chunk)
                print(f"normalized {archive.name}:{member}")
    if not wrote_header:
        raise ValueError("No trip rows found in the supplied archives")
    temporary_output.replace(output)
    return total


def normalize_weather(source, output):
    payload = json.loads(Path(source).read_text(encoding="utf-8"))
    hourly = payload["hourly"]
    frame = pd.DataFrame({
        "weather_time": hourly["time"],
        "temperature": hourly["temperature_2m"],
        "precipitation": hourly["precipitation"],
        "wind_speed": hourly["wind_speed_10m"],
    })
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    return len(frame)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trip-archives", nargs="+", required=True)
    parser.add_argument("--weather-json", required=True)
    parser.add_argument("--trips-output", default="data/raw/real/trips.csv")
    parser.add_argument("--weather-output", default="data/raw/real/weather.csv")
    parser.add_argument("--chunksize", type=int, default=500_000)
    args = parser.parse_args()

    trip_rows = normalize_trips(args.trip_archives, args.trips_output, args.chunksize)
    weather_rows = normalize_weather(args.weather_json, args.weather_output)
    print(json.dumps({"trip_rows": trip_rows, "weather_rows": weather_rows}, indent=2))


if __name__ == "__main__":
    main()
