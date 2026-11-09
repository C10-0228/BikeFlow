"""Verify Spark Parquet output and execute Hive-compatible SQL analytics."""
import argparse
import json
from pyspark.sql import SparkSession


def main(args):
    spark = SparkSession.builder.appName("BikeFlow-Verify-SQL").getOrCreate()
    rides = spark.read.parquet(args.rides)
    hourly = spark.read.parquet(args.hourly)
    rides.createOrReplaceTempView("ride_fact")
    hourly.createOrReplaceTempView("station_hourly")
    verify = {
        "ride_rows": rides.count(),
        "hourly_rows": hourly.count(),
        "station_count": hourly.select("station_id").distinct().count(),
        "pickup_total": hourly.agg({"pickup_count": "sum"}).first()[0],
        "dropoff_total": hourly.agg({"dropoff_count": "sum"}).first()[0],
        "min_date": str(rides.agg({"started_at": "min"}).first()[0]),
        "max_date": str(rides.agg({"started_at": "max"}).first()[0]),
    }
    daily = spark.sql("""
        SELECT event_date, COUNT(*) AS rides,
               ROUND(AVG(duration_min), 2) AS avg_duration_min,
               ROUND(AVG(CASE WHEN member_type='member' THEN 1.0 ELSE 0.0 END), 4) AS member_ratio
        FROM ride_fact GROUP BY event_date ORDER BY event_date
    """)
    top_stations = spark.sql("""
        SELECT station_id, SUM(pickup_count) AS pickups
        FROM station_hourly GROUP BY station_id ORDER BY pickups DESC LIMIT 10
    """)
    daily.write.mode("overwrite").option("header", True).csv(args.daily)
    top_stations.write.mode("overwrite").option("header", True).csv(args.top_stations)
    with open(args.report, "w") as f:
        json.dump(verify, f, indent=2)
    print(json.dumps(verify, indent=2))
    print("Top stations:")
    top_stations.show(10, truncate=False)
    spark.stop()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--rides", required=True)
    p.add_argument("--hourly", required=True)
    p.add_argument("--daily", required=True)
    p.add_argument("--top-stations", required=True)
    p.add_argument("--report", required=True)
    main(p.parse_args())

