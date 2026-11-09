"""Local implementation of the BikeFlow ETL, analytics and modelling pipeline."""
from pathlib import Path
import json
import argparse
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def _read(path):
    return pd.read_csv(path, dtype={
        "ride_id": "string", "start_station_id": "string",
        "end_station_id": "string", "member_type": "string",
    })


def clean_and_join(trips, weather):
    df = trips.copy()
    quality = {"input_rows": int(len(df)), "rejects": {}}
    df["started_at"] = pd.to_datetime(df["started_at"], errors="coerce", format="mixed")
    df["ended_at"] = pd.to_datetime(df["ended_at"], errors="coerce", format="mixed")
    df["duration_min"] = (df["ended_at"] - df["started_at"]).dt.total_seconds() / 60
    reject_reason = pd.Series(pd.NA, index=df.index, dtype="string")

    def mark(mask, reason):
        selected = mask.fillna(False) & reject_reason.isna()
        quality["rejects"][reason] = int(selected.sum())
        reject_reason.loc[selected] = reason

    ride_id = df["ride_id"].astype("string").str.strip()
    mark(ride_id.isna() | ride_id.eq(""), "missing_ride_id")
    mark(df["ride_id"].duplicated(keep="first"), "duplicate_ride_id")
    mark(df["started_at"].isna(), "invalid_started_at")
    mark(df["ended_at"].isna(), "invalid_ended_at")
    valid_duration = df["duration_min"].between(1, 1440)
    mark(df["started_at"].notna() & df["ended_at"].notna() & ~valid_duration, "invalid_duration")
    mark(df["start_station_id"].isna(), "missing_start_station_id")
    mark(df["end_station_id"].isna(), "missing_end_station_id")
    valid = reject_reason.isna()
    quality["rejected_rows"] = int((~valid).sum())
    df = df.loc[valid].copy()
    df["event_date"] = df["started_at"].dt.date.astype(str)
    df["event_hour"] = df["started_at"].dt.hour
    df["day_of_week"] = df["started_at"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["member_type"] = df["member_type"].fillna("unknown").str.lower()
    w = weather.copy()
    w["weather_time"] = pd.to_datetime(w["weather_time"], errors="coerce").dt.floor("h")
    df["weather_time"] = df["started_at"].dt.floor("h")
    df = df.merge(w, on="weather_time", how="left")
    weather_cols = ["temperature", "precipitation", "wind_speed"]
    df["weather_missing"] = df[weather_cols].isna().any(axis=1).astype(int)
    quality["output_rows"] = int(len(df))
    quality["retention_rate"] = round(len(df) / max(quality["input_rows"], 1), 6)
    quality["null_rates"] = {c: round(float(df[c].isna().mean()), 6) for c in weather_cols}
    quality["weather_match_rate"] = round(float(1 - df["weather_missing"].mean()), 6)
    return df, quality


def build_hourly(df):
    keys = ["start_station_id", "event_date", "event_hour"]
    pickups = df.groupby(keys, as_index=False).agg(
        pickup_count=("ride_id", "count"),
        total_duration_min=("duration_min", "sum"), avg_duration_min=("duration_min", "mean"),
        member_count=("member_type", lambda s: int((s == "member").sum())),
        casual_count=("member_type", lambda s: int((s == "casual").sum())),
    ).rename(columns={"start_station_id": "station_id"})
    pickups["timestamp"] = pd.to_datetime(pickups["event_date"]) + pd.to_timedelta(pickups["event_hour"], unit="h")
    endings = df.assign(
        event_date=df["ended_at"].dt.strftime("%Y-%m-%d"), event_hour=df["ended_at"].dt.hour,
    )
    dropoffs = endings.groupby(["end_station_id", "event_date", "event_hour"], as_index=False).agg(
        dropoff_count=("ride_id", "count"),
    ).rename(columns={"end_station_id": "station_id"})
    dropoffs["timestamp"] = pd.to_datetime(dropoffs["event_date"]) + pd.to_timedelta(dropoffs["event_hour"], unit="h")
    observed = pickups.merge(dropoffs, on=["station_id", "event_date", "event_hour", "timestamp"], how="outer")
    timestamps = pd.date_range(df["started_at"].min().floor("h"), df["ended_at"].max().floor("h"), freq="h")
    wx = df.groupby(["event_date", "event_hour"], as_index=False).agg(
        temperature=("temperature", "mean"), precipitation=("precipitation", "mean"),
    )
    wx["timestamp"] = pd.to_datetime(wx["event_date"]) + pd.to_timedelta(wx["event_hour"], unit="h")
    wx = wx.set_index("timestamp").reindex(timestamps)
    wx[["temperature", "precipitation"]] = wx[["temperature", "precipitation"]].interpolate(
        method="time", limit_direction="both"
    )
    wx = wx.reset_index(names="timestamp")[["timestamp", "temperature", "precipitation"]]
    stations = pd.concat([
        df[["start_station_id"]].rename(columns={"start_station_id": "station_id"}),
        df[["end_station_id"]].rename(columns={"end_station_id": "station_id"}),
    ]).dropna().drop_duplicates()
    if {"start_lat", "start_lng"}.issubset(df.columns):
        start_locations = df[["start_station_id", "start_lat", "start_lng"]].rename(
            columns={"start_station_id": "station_id", "start_lat": "station_lat", "start_lng": "station_lng"})
        end_locations = df[["end_station_id", "end_lat", "end_lng"]].rename(
            columns={"end_station_id": "station_id", "end_lat": "station_lat", "end_lng": "station_lng"})
        locations = pd.concat([start_locations, end_locations]).groupby("station_id", as_index=False).mean()
        stations = stations.merge(locations, on="station_id", how="left")
    grid = stations.merge(pd.DataFrame({"timestamp": timestamps}), how="cross")
    grid["event_date"] = grid["timestamp"].dt.strftime("%Y-%m-%d")
    grid["event_hour"] = grid["timestamp"].dt.hour
    hourly = (grid.merge(observed, on=["station_id", "event_date", "event_hour", "timestamp"], how="left")
              .merge(wx, on="timestamp", how="left"))
    count_cols = ["pickup_count", "dropoff_count", "total_duration_min", "member_count", "casual_count"]
    hourly[count_cols] = hourly[count_cols].fillna(0)
    hourly[["pickup_count", "dropoff_count", "member_count", "casual_count"]] = hourly[
        ["pickup_count", "dropoff_count", "member_count", "casual_count"]
    ].astype("int64")
    hourly = hourly.sort_values(["station_id", "timestamp"])
    hourly["lag_1"] = hourly.groupby("station_id")["pickup_count"].shift(1)
    hourly["lag_24"] = hourly.groupby("station_id")["pickup_count"].shift(24)
    hourly["rolling_24"] = hourly.groupby("station_id")["pickup_count"].transform(lambda s: s.shift(1).rolling(24, min_periods=1).mean())
    hourly["day_of_week"] = hourly["timestamp"].dt.dayofweek
    hourly["is_weekend"] = (hourly["day_of_week"] >= 5).astype(int)
    hourly["hour_sin"] = np.sin(2 * np.pi * hourly["event_hour"] / 24)
    hourly["hour_cos"] = np.cos(2 * np.pi * hourly["event_hour"] / 24)
    return hourly


def cluster_stations(df, seed=42):
    daily = df.groupby(["station_id", "event_date"], as_index=False).agg(
        daily_pickup=("pickup_count", "sum"), daily_dropoff=("dropoff_count", "sum"),
    )
    f = daily.groupby("station_id", as_index=False).agg(
        avg_daily_pickup=("daily_pickup", "mean"), avg_daily_dropoff=("daily_dropoff", "mean"),
    )
    total_members = df.groupby("station_id")["member_count"].sum()
    total_casual = df.groupby("station_id")["casual_count"].sum()
    f["member_ratio"] = total_members.values / np.maximum(total_members.values + total_casual.values, 1)
    avg_duration = df.groupby("station_id")["avg_duration_min"].mean()
    f["avg_duration_min"] = f["station_id"].map(avg_duration).fillna(0)
    morning = df[df["event_hour"].isin([7, 8, 9])].groupby("station_id")["pickup_count"].sum()
    total_pickups = df.groupby("station_id")["pickup_count"].sum()
    f["morning_peak_ratio"] = f["station_id"].map(morning).fillna(0) / np.maximum(f["station_id"].map(total_pickups), 1)
    if {"station_lat", "station_lng"}.issubset(df.columns):
        locations = df.groupby("station_id", as_index=False).agg(
            station_lat=("station_lat", "first"), station_lng=("station_lng", "first"),
        )
        f = f.merge(locations, on="station_id", how="left")
    cols = ["avg_daily_pickup", "avg_daily_dropoff", "member_ratio", "avg_duration_min", "morning_peak_ratio"]
    x = StandardScaler().fit_transform(np.log1p(f[cols].clip(lower=0)))
    k = min(4, max(2, len(f) // 2))
    model = KMeans(n_clusters=k, random_state=seed, n_init=20).fit(x)
    f["cluster_id"] = model.labels_
    score = float(silhouette_score(x, model.labels_)) if k > 1 and len(f) > k else 0.0
    return f, {"k": k, "silhouette": round(score, 6)}


def train_forecast(hourly, seed=42):
    data = hourly.dropna(subset=["lag_1", "lag_24", "rolling_24", "temperature", "precipitation"]).copy().sort_values("timestamp")
    if len(data) < 30:
        raise ValueError("Not enough hourly rows after lag features for model training")
    cutoff = data["timestamp"].quantile(0.85)
    train, test = data[data["timestamp"] < cutoff], data[data["timestamp"] >= cutoff]
    num = ["lag_1", "lag_24", "rolling_24", "temperature", "precipitation", "hour_sin", "hour_cos", "is_weekend"]
    cat = ["station_id", "event_hour"]
    prep = ColumnTransformer([("num", StandardScaler(), num), ("cat", OneHotEncoder(handle_unknown="ignore"), cat)])
    pipe = Pipeline([("prep", prep), ("model", LinearRegression())])
    pipe.fit(train[num + cat], train["pickup_count"])
    pred = np.maximum(0, pipe.predict(test[num + cat]))
    baseline = test["lag_24"].to_numpy()
    metrics = {
        "train_rows": int(len(train)), "test_rows": int(len(test)),
        "train_end": str(train["timestamp"].max()), "test_start": str(test["timestamp"].min()),
        "mae": round(float(mean_absolute_error(test["pickup_count"], pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(test["pickup_count"], pred))), 4),
        "r2": round(float(r2_score(test["pickup_count"], pred)), 4),
        "baseline_mae": round(float(mean_absolute_error(test["pickup_count"], baseline)), 4),
        "baseline_rmse": round(float(np.sqrt(mean_squared_error(test["pickup_count"], baseline))), 4),
    }
    forecasts = test[["station_id", "timestamp", "pickup_count"]].copy()
    forecasts["predicted_pickup"] = pred.round(3)
    forecasts["lower_bound"] = np.maximum(0, forecasts["predicted_pickup"] - metrics["rmse"])
    forecasts["upper_bound"] = forecasts["predicted_pickup"] + metrics["rmse"]
    return forecasts, metrics


def run(raw_trip, raw_weather, output_dir="data/processed", artifacts_dir="artifacts"):
    out, art = Path(output_dir), Path(artifacts_dir)
    out.mkdir(parents=True, exist_ok=True); art.mkdir(parents=True, exist_ok=True)
    clean, quality = clean_and_join(_read(raw_trip), _read(raw_weather))
    hourly = build_hourly(clean)
    features, cluster_metrics = cluster_stations(hourly)
    forecasts, model_metrics = train_forecast(hourly)
    clean.to_csv(out / "ride_fact.csv", index=False)
    hourly.to_csv(out / "station_hourly.csv", index=False)
    features.to_csv(out / "station_features.csv", index=False)
    forecasts.to_csv(art / "forecasts.csv", index=False)
    features.to_csv(art / "clusters.csv", index=False)
    quality["cluster"] = cluster_metrics
    quality["output_columns"] = list(clean.columns)
    (art / "data_quality.json").write_text(json.dumps(quality, indent=2, ensure_ascii=False), encoding="utf-8")
    (art / "metrics.json").write_text(json.dumps({"cluster": cluster_metrics, "forecast": model_metrics}, indent=2), encoding="utf-8")
    return quality, model_metrics


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--trip", default="data/raw/trips.csv"); p.add_argument("--weather", default="data/raw/weather.csv")
    args = p.parse_args(); q, m = run(args.trip, args.weather); print(json.dumps({"quality": q, "metrics": m}, ensure_ascii=False, indent=2))

