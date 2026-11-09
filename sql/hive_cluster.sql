CREATE DATABASE IF NOT EXISTS bikeflow;
USE bikeflow;

DROP TABLE IF EXISTS station_hourly;
CREATE EXTERNAL TABLE station_hourly (
  station_id STRING,
  pickup_count BIGINT,
  dropoff_count BIGINT,
  total_duration_min DOUBLE,
  avg_duration_min DOUBLE,
  member_count BIGINT,
  casual_count BIGINT,
  temperature DOUBLE,
  precipitation DOUBLE,
  lag_1 BIGINT,
  lag_24 BIGINT
)
PARTITIONED BY (event_date DATE, event_hour INT)
STORED AS PARQUET
LOCATION 'hdfs:///bikeflow/curated/station_hourly';

MSCK REPAIR TABLE station_hourly;

SELECT event_date, SUM(pickup_count) AS rides
FROM station_hourly
GROUP BY event_date
ORDER BY event_date;

SELECT station_id, SUM(pickup_count) AS pickups,
       SUM(member_count) / SUM(pickup_count) AS member_ratio
FROM station_hourly
GROUP BY station_id
ORDER BY pickups DESC
LIMIT 20;

SELECT event_hour, AVG(pickup_count) AS avg_pickups,
       AVG(precipitation) AS avg_precipitation
FROM station_hourly
GROUP BY event_hour
ORDER BY event_hour;

SELECT COUNT(*) AS rows, COUNT(DISTINCT station_id) AS stations
FROM station_hourly;

