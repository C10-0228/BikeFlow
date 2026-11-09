"""Generate a deterministic local dataset for development and demonstration."""
from pathlib import Path
import numpy as np
import pandas as pd


def generate(out_dir="data/raw", days=90, seed=42):
    rng = np.random.default_rng(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stations = [
        ("S001", "Central Park", 40.767, -73.971),
        ("S002", "Union Square", 40.735, -73.990),
        ("S003", "Hudson River", 40.745, -74.010),
        ("S004", "Brooklyn Bridge", 40.706, -73.997),
        ("S005", "Columbus Circle", 40.768, -73.982),
        ("S006", "East Village", 40.726, -73.981),
        ("S007", "Williamsburg", 40.714, -73.961),
        ("S008", "Chelsea", 40.746, -74.001),
    ]
    start = pd.Timestamp("2024-01-01", tz="America/New_York")
    hours = pd.date_range(start, periods=days * 24, freq="h")
    weather = []
    for ts in hours:
        temp = 8 + 10 * np.sin((ts.dayofyear - 15) / 365 * 2 * np.pi) + rng.normal(0, 3)
        rain = max(0, rng.gamma(1.2, 0.8) - 0.5) if rng.random() < 0.18 else 0.0
        weather.append([ts.tz_convert(None), round(temp, 2), round(rain, 2), round(rng.uniform(5, 28), 2)])
    weather_df = pd.DataFrame(weather, columns=["weather_time", "temperature", "precipitation", "wind_speed"])
    weather_by_hour = weather_df.set_index("weather_time")
    weather_df.to_csv(out / "weather.csv", index=False)

    records = []
    ride_num = 0
    station_weights = np.array([1.4, 1.7, 1.0, 0.8, 1.2, 1.0, 1.1, 1.3])
    for ts in hours:
        work_peak = 1.8 if ts.hour in (8, 9, 17, 18) else 0.65 if ts.hour < 6 else 1.0
        weekend = 1.25 if ts.dayofweek >= 5 else 1.0
        weather_key = ts.tz_convert(None).floor("h")
        rain = float(weather_by_hour.loc[weather_key, "precipitation"])
        rain_factor = 0.55 if rain > 0.5 else 1.0
        for idx, (sid, name, lat, lng) in enumerate(stations):
            n = max(0, int(rng.poisson(8 * station_weights[idx] * work_peak * weekend * rain_factor)))
            for _ in range(n):
                ride_num += 1
                end_idx = int(rng.choice(len(stations), p=station_weights / station_weights.sum()))
                duration = float(np.clip(rng.lognormal(2.7, 0.45), 1, 120))
                started = ts + pd.to_timedelta(int(rng.integers(0, 60)), unit="m")
                ended = started + pd.to_timedelta(float(duration), unit="m")
                end = stations[end_idx]
                records.append([
                    f"R{ride_num:08d}", "classic_bike", started.tz_localize(None), ended.tz_localize(None),
                    sid, name, end[0], end[1], lat + rng.normal(0, .0002), lng + rng.normal(0, .0002),
                    end[2] + rng.normal(0, .0002), end[3] + rng.normal(0, .0002),
                    "member" if rng.random() < 0.68 else "casual",
                ])
    cols = ["ride_id", "rideable_type", "started_at", "ended_at", "start_station_id", "start_station_name", "end_station_id", "end_station_name", "start_lat", "start_lng", "end_lat", "end_lng", "member_type"]
    rides = pd.DataFrame(records, columns=cols)
    rides.to_csv(out / "trips.csv", index=False)
    return rides, weather_df


if __name__ == "__main__":
    rides, weather = generate()
    print(f"generated {len(rides):,} rides and {len(weather):,} weather rows")

