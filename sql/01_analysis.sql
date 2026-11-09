-- Hive version: create an external table over the curated Parquet output,
-- then use the same queries to produce dashboard aggregates.
SELECT event_date, SUM(pickup_count) AS rides
FROM bikeflow.dws_station_hourly
GROUP BY event_date
ORDER BY event_date;

SELECT station_id, SUM(pickup_count) AS pickups
FROM bikeflow.dws_station_hourly
GROUP BY station_id
ORDER BY pickups DESC
LIMIT 20;

