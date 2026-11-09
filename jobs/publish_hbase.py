"""Publish ADS CSV results to HBase when happybase is installed in the cluster."""
import argparse
import csv
import happybase


def put_csv(path, table_name, key_fields, families, host):
    connection = happybase.Connection(host=host)
    table = connection.table(table_name)
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = "#".join(row[k] for k in key_fields).encode()
            values = {f"{family}:{column}".encode(): value.encode() for family, columns in families.items() for column, value in row.items() if column in columns and value != ""}
            table.put(key, values)
    connection.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--clusters", required=True); p.add_argument("--forecasts", required=True); p.add_argument("--host", default="localhost"); args = p.parse_args()
    put_csv(args.clusters, "bike_station_profile", ["station_id"], {"stat": ["avg_daily_pickup", "avg_daily_dropoff", "member_ratio", "cluster_id"]}, args.host)
    put_csv(args.forecasts, "bike_station_forecast", ["station_id", "timestamp"], {"p": ["predicted_pickup", "lower_bound", "upper_bound"]}, args.host)

