"""Run station KMeans and time-split demand regression with Spark MLlib."""
import argparse
import json
from pyspark.sql import SparkSession, Window, functions as F
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StandardScaler, StringIndexer, OneHotEncoder
from pyspark.ml.clustering import KMeans
from pyspark.ml.regression import LinearRegression
from pyspark.ml.evaluation import RegressionEvaluator, ClusteringEvaluator


def main(args):
    spark = SparkSession.builder.appName("BikeFlow-MLlib").getOrCreate()
    hourly = spark.read.parquet(args.hourly)

    daily = (hourly.groupBy("station_id", "event_date")
             .agg(F.sum("pickup_count").alias("daily_pickup"), F.sum("dropoff_count").alias("daily_dropoff"))
             .groupBy("station_id")
             .agg(F.avg("daily_pickup").alias("avg_pickup"), F.avg("daily_dropoff").alias("avg_dropoff")))
    activity = hourly.groupBy("station_id").agg(
        F.coalesce(F.avg("avg_duration_min"), F.lit(0)).alias("avg_duration"), F.sum("member_count").alias("members"),
        F.sum("casual_count").alias("casuals"), F.sum("pickup_count").alias("total_pickups"),
        F.sum(F.when(F.col("event_hour").isin([7, 8, 9]), F.col("pickup_count")).otherwise(0)).alias("morning_pickups"),
        F.first("station_lat", ignorenulls=True).alias("station_lat"),
        F.first("station_lng", ignorenulls=True).alias("station_lng"))
    station = (daily.join(activity, "station_id")
        .withColumn("member_ratio", F.col("members") / F.greatest(F.col("members") + F.col("casuals"), F.lit(1)))
        .withColumn("morning_ratio", F.col("morning_pickups") / F.greatest(F.col("total_pickups"), F.lit(1))))
    station_cols = ["avg_pickup", "avg_dropoff", "avg_duration", "member_ratio", "morning_ratio"]
    station_vec = VectorAssembler(inputCols=station_cols, outputCol="raw_features", handleInvalid="keep")
    scaler = StandardScaler(inputCol="raw_features", outputCol="features", withMean=True, withStd=True)
    station_features = scaler.fit(station_vec.transform(station)).transform(station_vec.transform(station))
    evaluator_cluster = ClusteringEvaluator(featuresCol="features", predictionCol="cluster_id")
    scores = []
    fitted = []
    for k in range(2, min(4, station.count() - 1) + 1):
        estimator = KMeans(k=k, seed=42, featuresCol="features", predictionCol="cluster_id")
        km_model = estimator.fit(station_features)
        clustered_k = km_model.transform(station_features)
        score = evaluator_cluster.evaluate(clustered_k)
        scores.append({"k": k, "silhouette": score})
        fitted.append((score, km_model, clustered_k))
    silhouette, kmeans_model, clustered = max(fitted, key=lambda item: item[0])
    best_k = kmeans_model.getK()
    clustered.select("station_id", "cluster_id", "station_lat", "station_lng", *station_cols).write.mode("overwrite").option("header", True).csv(args.clusters)

    frame = (hourly.withColumn("timestamp", F.to_timestamp(F.concat_ws(" ", F.col("event_date").cast("string"), F.format_string("%02d:00:00", F.col("event_hour")))))
             .withColumn("hour_sin", F.sin(2 * F.lit(3.141592653589793) * F.col("event_hour") / 24))
             .withColumn("hour_cos", F.cos(2 * F.lit(3.141592653589793) * F.col("event_hour") / 24))
             .withColumn("is_weekend", (F.dayofweek("timestamp").isin([1, 7])).cast("double")))
    w = Window.partitionBy("station_id").orderBy("timestamp").rowsBetween(-24, -1)
    frame = frame.withColumn("rolling_24", F.avg("pickup_count").over(w))
    frame = frame.join(clustered.select("station_id", "cluster_id"), "station_id", "left")
    frame = frame.dropna(subset=["lag_1", "lag_24", "temperature", "precipitation"])
    station_index = StringIndexer(inputCol="station_id", outputCol="station_idx", handleInvalid="keep")
    station_ohe = OneHotEncoder(inputCol="station_idx", outputCol="station_vec")
    assembler = VectorAssembler(inputCols=["lag_1", "lag_24", "rolling_24", "temperature", "precipitation", "hour_sin", "hour_cos", "is_weekend", "station_vec"], outputCol="raw_features", handleInvalid="keep")
    scale = StandardScaler(inputCol="raw_features", outputCol="features", withMean=False, withStd=True)
    reg = LinearRegression(featuresCol="features", labelCol="pickup_count", predictionCol="prediction", maxIter=50, regParam=0.05, elasticNetParam=0.1)
    pipeline = Pipeline(stages=[station_index, station_ohe, assembler, scale, reg])
    split_epoch = frame.select(F.unix_timestamp("timestamp").alias("epoch")).approxQuantile("epoch", [0.85], 0.001)[0]
    train = frame.filter(F.unix_timestamp("timestamp") < F.lit(split_epoch))
    test = frame.filter(F.unix_timestamp("timestamp") >= F.lit(split_epoch))
    model = pipeline.fit(train)
    predictions = model.transform(test).withColumn("predicted_pickup", F.greatest(F.col("prediction"), F.lit(0)))
    evaluator = RegressionEvaluator(labelCol="pickup_count", predictionCol="predicted_pickup")
    mae = evaluator.setMetricName("mae").evaluate(predictions)
    rmse = evaluator.setMetricName("rmse").evaluate(predictions)
    r2 = evaluator.setMetricName("r2").evaluate(predictions)
    baseline = test.withColumn("baseline", F.col("lag_24").cast("double"))
    baseline_mae = RegressionEvaluator(labelCol="pickup_count", predictionCol="baseline", metricName="mae").evaluate(baseline)
    baseline_rmse = RegressionEvaluator(labelCol="pickup_count", predictionCol="baseline", metricName="rmse").evaluate(baseline)
    predictions.select("station_id", "timestamp", "pickup_count", "predicted_pickup", "cluster_id").write.mode("overwrite").parquet(args.forecasts)
    model.write().overwrite().save(args.model)
    metrics = {
        "engine": "Spark MLlib", "train_rows": train.count(), "test_rows": test.count(),
        "split_epoch": split_epoch, "mae": mae, "rmse": rmse, "r2": r2,
        "baseline_mae": baseline_mae, "baseline_rmse": baseline_rmse,
        "cluster_k": best_k, "cluster_silhouette": silhouette, "cluster_candidates": scores,
    }
    with open(args.metrics, "w") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps(metrics, indent=2))
    spark.stop()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--hourly", required=True); p.add_argument("--clusters", required=True)
    p.add_argument("--forecasts", required=True); p.add_argument("--model", required=True); p.add_argument("--metrics", required=True)
    main(p.parse_args())

