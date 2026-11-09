#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MASTER_DIR=/root/bikeflow
TRIP_FILE=${BIKEFLOW_TRIPS:-$ROOT/data/raw/real/trips.csv}
WEATHER_FILE=${BIKEFLOW_WEATHER:-$ROOT/data/raw/real/weather.csv}

if [[ ! -f "$TRIP_FILE" || ! -f "$WEATHER_FILE" ]]; then
  echo "Real trip/weather CSVs are missing. Set BIKEFLOW_TRIPS and BIKEFLOW_WEATHER to override." >&2
  exit 1
fi

docker exec master mkdir -p "$MASTER_DIR" /bikeflow/raw /bikeflow/curated /bikeflow/analytics /bikeflow/mr_output
docker exec master mkdir -p "$MASTER_DIR/raw"
docker cp "$TRIP_FILE" master:"$MASTER_DIR/raw/trips.csv"
docker cp "$WEATHER_FILE" master:"$MASTER_DIR/raw/weather.csv"
docker cp "$ROOT/jobs/." master:"$MASTER_DIR/jobs/"
docker cp "$ROOT/hadoop/." master:"$MASTER_DIR/hadoop/"
docker cp "$ROOT/sql/." master:"$MASTER_DIR/sql/"
docker cp "$ROOT/artifacts/." master:"$MASTER_DIR/artifacts/"

docker exec master hdfs dfs -mkdir -p /bikeflow/raw /bikeflow/curated /bikeflow/analytics
docker exec master hdfs dfs -put -f "$MASTER_DIR/raw/trips.csv" /bikeflow/raw/trips.csv
docker exec master hdfs dfs -put -f "$MASTER_DIR/raw/weather.csv" /bikeflow/raw/weather.csv

echo "BikeFlow files uploaded to master:$MASTER_DIR"
docker exec master hdfs dfs -ls -h /bikeflow/raw

