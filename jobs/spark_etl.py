"""Spark SQL version of the core ETL. Run with spark-submit in the course cluster."""
import argparse
from pyspark.sql import SparkSession, functions as F, Window


def main(args):
    spark = SparkSession.builder.appName("BikeFlow-ETL").enableHiveSupport().getOrCreate()
    trips = spark.read.option("header", True).option("inferSchema", True).csv(args.trips)
    weather = spark.read.option("header", True).option("inferSchema", True).csv(args.weather)
    trips = (trips.withColumn("started_at", F.to_timestamp("started_at"))
                  .withColumn("ended_at", F.to_timestamp("ended_at"))
                  .withColumn("duration_min", (F.col("ended_at").cast("long") - F.col("started_at").cast("long")) / 60)
                  .filter(F.col("duration_min").between(1, 1440))
                  .filter(F.col("ride_id").isNotNull() & (F.length(F.trim("ride_id")) > 0))
                  .filter(F.col("start_station_id").isNotNull() & F.col("end_station_id").isNotNull())
                  .dropDuplicates(["ride_id"])
                  .withColumn("event_date", F.to_date("started_at"))
                  .withColumn("event_hour", F.hour("started_at"))
                  .withColumn("day_of_week", F.dayofweek("started_at") - 1)
                  .withColumn("is_weekend", (F.col("day_of_week") >= 5).cast("int"))
                  .withColumn("weather_time", F.date_trunc("hour", "started_at")))
    weather = weather.withColumn("weather_time", F.date_trunc("hour", "weather_time"))
    clean = trips.join(weather, "weather_time", "left").withColumn(
        "weather_missing", F.when(F.col("temperature").isNull(), 1).otherwise(0))
    clean.write.mode("overwrite").partitionBy("event_date").parquet(args.output)
    if args.clean_csv:
        clean.coalesce(8).write.mode("overwrite").option("header", True).csv(args.clean_csv)
    pickups = (clean.groupBy(F.col("start_station_id").alias("station_id"), "event_date", "event_hour")
               .agg(F.count("ride_id").alias("pickup_count"),
                    F.sum("duration_min").alias("total_duration_min"), F.avg("duration_min").alias("avg_duration_min"),
                    F.sum((F.col("member_type") == "member").cast("int")).alias("member_count"),
                    F.sum((F.col("member_type") == "casual").cast("int")).alias("casual_count")))
    dropoffs = (clean.withColumn("dropoff_date", F.to_date("ended_at"))
                .withColumn("dropoff_hour", F.hour("ended_at"))
                .groupBy(F.col("end_station_id").alias("station_id"),
                         F.col("dropoff_date").alias("event_date"),
                         F.col("dropoff_hour").alias("event_hour"))
                .agg(F.count("ride_id").alias("dropoff_count")))
    observed = pickups.join(dropoffs, ["station_id", "event_date", "event_hour"], "full")
    weather_hourly = (weather.withColumn("timestamp", F.date_trunc("hour", "weather_time"))
                      .select("timestamp", "temperature", "precipitation")
                      .dropDuplicates(["timestamp"]))
    bounds = clean.agg(F.min("started_at").alias("first_trip"), F.max("ended_at").alias("last_trip")).first()
    first_hour = bounds["first_trip"].replace(minute=0, second=0, microsecond=0)
    last_hour = bounds["last_trip"].replace(minute=0, second=0, microsecond=0)
    hours = (spark.range(1)
             .select(F.explode(F.sequence(F.lit(first_hour).cast("timestamp"),
                                          F.lit(last_hour).cast("timestamp"),
                                          F.expr("INTERVAL 1 HOUR"))).alias("timestamp"))
             .withColumn("event_date", F.to_date("timestamp"))
             .withColumn("event_hour", F.hour("timestamp")))
    station_starts = clean.select(F.col("start_station_id").alias("station_id"),
                                  F.col("start_lat").alias("station_lat"),
                                  F.col("start_lng").alias("station_lng"))
    station_ends = clean.select(F.col("end_station_id").alias("station_id"),
                                F.col("end_lat").alias("station_lat"),
                                F.col("end_lng").alias("station_lng"))
    stations = (station_starts.unionByName(station_ends).groupBy("station_id")
                .agg(F.avg("station_lat").alias("station_lat"), F.avg("station_lng").alias("station_lng")))
    hourly = (stations.crossJoin(hours)
              .join(observed, ["station_id", "event_date", "event_hour"], "left")
              .join(weather_hourly, ["timestamp"], "left")
              .na.fill(0, subset=["pickup_count", "dropoff_count", "total_duration_min", "member_count", "casual_count"]))
    w = Window.partitionBy("station_id").orderBy("timestamp")
    hourly = hourly.withColumn("lag_1", F.lag("pickup_count", 1).over(w)).withColumn("lag_24", F.lag("pickup_count", 24).over(w))
    hourly.repartition(48, "event_date", "event_hour").write.mode("overwrite").partitionBy("event_date", "event_hour").parquet(args.hourly)
    spark.stop()


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--trips", required=True); p.add_argument("--weather", required=True); p.add_argument("--output", required=True); p.add_argument("--hourly", required=True); p.add_argument("--clean-csv")
    main(p.parse_args())

