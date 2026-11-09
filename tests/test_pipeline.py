from pathlib import Path
import json
import subprocess
import sys
import zipfile
from datetime import timedelta

import pandas as pd
from jobs.generate_sample_data import generate
from jobs.pipeline import clean_and_join, build_hourly, cluster_stations, _read
from jobs.prepare_citibike_data import normalize_trips, normalize_weather
from jobs.verify_streaming_output import verify as verify_streaming


def test_cleaning_and_hourly(tmp_path):
    rides, weather = generate(tmp_path / "raw", days=3, seed=7)
    clean, quality = clean_and_join(rides, weather)
    hourly = build_hourly(clean)
    assert quality["output_rows"] == len(clean) > 0
    assert clean["duration_min"].between(1, 1440).all()
    assert hourly["pickup_count"].sum() == len(clean)
    assert hourly["dropoff_count"].sum() == len(clean)
    assert set(clean["end_station_id"]).issubset(set(hourly["station_id"]))
    assert hourly["timestamp"].max() == clean["ended_at"].max().floor("h")
    assert len(hourly) == hourly["station_id"].nunique() * hourly["timestamp"].nunique()
    station_rows = hourly[hourly["station_id"] == hourly["station_id"].iloc[0]].reset_index(drop=True)
    assert station_rows.loc[24, "lag_24"] == station_rows.loc[0, "pickup_count"]
    profiles, _ = cluster_stations(hourly)
    expected_daily_mean = hourly.groupby(["station_id", "event_date"])["pickup_count"].sum().groupby("station_id").mean()
    actual_daily_mean = profiles.set_index("station_id")["avg_daily_pickup"]
    pd.testing.assert_series_equal(actual_daily_mean.sort_index(), expected_daily_mean.sort_index(), check_names=False)
    assert profiles["station_lat"].notna().all()
    assert profiles["station_lng"].notna().all()


def test_prepare_public_data(tmp_path):
    source = pd.DataFrame([{
        "ride_id": "ride-1", "rideable_type": "classic_bike",
        "started_at": "2024-01-01 08:00:00", "ended_at": "2024-01-01 08:10:00",
        "start_station_id": "100", "start_station_name": "A",
        "end_station_id": "200", "end_station_name": "B",
        "start_lat": 40.7, "start_lng": -74.0, "end_lat": 40.8, "end_lng": -73.9,
        "member_casual": "Member",
    }])
    archive = tmp_path / "202401-citibike-tripdata.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("202401-citibike-tripdata.csv", source.to_csv(index=False))
    trips_output = tmp_path / "real" / "trips.csv"
    assert normalize_trips([archive], trips_output, chunksize=1) == 1
    trips = pd.read_csv(trips_output)
    assert trips.loc[0, "member_type"] == "member"
    assert trips.loc[0, "start_station_id"] == 100

    weather_source = tmp_path / "weather.json"
    weather_source.write_text(json.dumps({"hourly": {
        "time": ["2024-01-01T08:00"], "temperature_2m": [2.5],
        "precipitation": [0.0], "wind_speed_10m": [8.0],
    }}))
    weather_output = tmp_path / "real" / "weather.csv"
    assert normalize_weather(weather_source, weather_output) == 1
    weather = pd.read_csv(weather_output)
    assert list(weather.columns) == ["weather_time", "temperature", "precipitation", "wind_speed"]
    assert weather.loc[0, "temperature"] == 2.5


def test_cleaning_reports_exclusive_reject_reasons(tmp_path):
    rides, weather = generate(tmp_path / "raw", days=2, seed=8)
    rides = rides.iloc[:8].copy()
    rides["started_at"] = rides["started_at"].astype("string")
    rides["ended_at"] = rides["ended_at"].astype("string")
    rides.loc[rides.index[0], "started_at"] = "not-a-time"
    rides.loc[rides.index[1], "ended_at"] = "not-a-time"
    rides.loc[rides.index[2], "ended_at"] = str(pd.to_datetime(rides.loc[rides.index[2], "started_at"]) + timedelta(days=2))
    rides.loc[rides.index[3], "start_station_id"] = pd.NA
    rides.loc[rides.index[4], "end_station_id"] = pd.NA
    rides.loc[rides.index[5], "ride_id"] = ""
    rides.loc[rides.index[6], "ride_id"] = rides.loc[rides.index[7], "ride_id"]
    clean, quality = clean_and_join(rides, weather)
    assert quality["rejected_rows"] == 7
    assert sum(quality["rejects"].values()) == quality["rejected_rows"]
    assert set(quality["rejects"]) == {
        "invalid_started_at", "invalid_ended_at", "invalid_duration",
        "missing_start_station_id", "missing_end_station_id", "missing_ride_id", "duplicate_ride_id",
    }
    assert len(clean) == 1


def test_station_ids_are_read_as_strings(tmp_path):
    path = tmp_path / "mixed_station_ids.csv"
    pd.DataFrame({"start_station_id": ["7407.13", "unknown"]}).to_csv(path, index=False)
    loaded = _read(path)
    assert loaded["start_station_id"].tolist() == ["7407.13", "unknown"]


def test_streaming_mapper_handles_repeated_headers_and_reducer_sums():
    header = ("weather_time,ride_id,rideable_type,started_at,ended_at,start_station_id,"
              "start_station_name,end_station_id,end_station_name,start_lat,start_lng,end_lat,"
              "end_lng,member_type,duration_min,event_date,event_hour,day_of_week,is_weekend,"
              "temperature,precipitation,wind_speed,weather_missing\n")
    row_a = ("2024-01-01T08:00:00Z,r1,bike,2024-01-01T08:05:00Z,2024-01-01T08:15:00Z,"
             "100,Station A,200,Station B,40,-74,40.1,-73.9,member,10,2024-01-01,8,0,0,"
             "2,0,4,0\n")
    row_b = ("2024-01-01T08:00:00Z,r2,bike,2024-01-01T08:45:00Z,2024-01-01T09:00:00Z,"
             "100,Station A,200,Station B,40,-74,40.1,-73.9,casual,15,2024-01-01,8,0,0,"
             "2,0,4,0\n")
    mapper = Path(__file__).parents[1] / "hadoop/mapper.py"
    reducer = Path(__file__).parents[1] / "hadoop/reducer.py"
    mapped = subprocess.run(
        [sys.executable, str(mapper)], input=header + row_a + header + row_b,
        text=True, capture_output=True, check=True,
    ).stdout
    reduced = subprocess.run(
        [sys.executable, str(reducer)], input="".join(sorted(mapped.splitlines(True))),
        text=True, capture_output=True, check=True,
    ).stdout.strip()
    assert reduced == "100,2024-01-01T08,2,25.000,1"


def test_streaming_output_verification_checks_pickup_total(tmp_path):
    output = tmp_path / "streaming"
    output.mkdir()
    (output / "_SUCCESS").touch()
    (output / "part-00000").write_text("100,2024-01-01T08,2,25.000,1\t\n", encoding="utf-8")
    report = verify_streaming(output, expected_pickups=2)
    assert report["pickup_total_matches_clean_rides"] is True
    assert report["output_groups"] == 1

