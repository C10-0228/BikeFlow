"""BikeFlow Streamlit dashboard. Run with: streamlit run dashboard/app.py"""
from pathlib import Path
import json
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="BikeFlow", layout="wide")
st.title("BikeFlow 共享单车分析系统")

hourly_path = ROOT / "data/processed/station_hourly.csv"
forecast_path = ROOT / "artifacts/forecasts.csv"
cluster_path = ROOT / "artifacts/clusters.csv"
quality_path = ROOT / "artifacts/data_quality.json"
metrics_path = ROOT / "artifacts/metrics.json"
spark_metrics_path = ROOT / "artifacts/spark_mllib_metrics.json"
if not hourly_path.exists():
    st.error("尚未生成处理结果。请先运行：python jobs/generate_sample_data.py && python jobs/pipeline.py")
    st.stop()

hourly = pd.read_csv(hourly_path, parse_dates=["timestamp"], dtype={"station_id": "string"})
forecasts = pd.read_csv(forecast_path, parse_dates=["timestamp"], dtype={"station_id": "string"}) if forecast_path.exists() else pd.DataFrame()
clusters = pd.read_csv(cluster_path, dtype={"station_id": "string"}) if cluster_path.exists() else pd.DataFrame()
quality = json.loads(quality_path.read_text()) if quality_path.exists() else {}
metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
spark_metrics = json.loads(spark_metrics_path.read_text()) if spark_metrics_path.exists() else {}

tabs = st.tabs(["运营总览", "站点聚类", "站点地图", "短时预测", "数据质量"])
with tabs[0]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("骑行记录", f"{quality.get('output_rows', 0):,}")
    c2.metric("活跃站点", f"{hourly.station_id.nunique():,}")
    c3.metric("平均小时取车", f"{hourly.pickup_count.mean():.1f}")
    c4.metric("天气匹配率", f"{quality.get('weather_match_rate', 0) * 100:.1f}%")
    daily = hourly.groupby("event_date", as_index=False)["pickup_count"].sum()
    st.plotly_chart(px.line(daily, x="event_date", y="pickup_count", title="每日骑行量"), use_container_width=True)
    heat = hourly.pivot_table(index="event_hour", columns="day_of_week", values="pickup_count", aggfunc="mean")
    st.plotly_chart(px.imshow(heat, labels={"x": "星期（0=周一）", "y": "小时", "color": "平均取车量"}, title="小时-星期需求热力图"), use_container_width=True)
with tabs[1]:
    if clusters.empty:
        st.warning("暂无聚类结果")
    else:
        st.plotly_chart(px.scatter(clusters, x="avg_daily_pickup", y="member_ratio", color="cluster_id", hover_name="station_id", title="站点画像聚类"), use_container_width=True)
        st.dataframe(clusters.sort_values("avg_daily_pickup", ascending=False), use_container_width=True)
with tabs[2]:
    if clusters.empty or not {"station_lat", "station_lng"}.issubset(clusters.columns):
        st.warning("暂无站点坐标")
    else:
        locations = clusters.dropna(subset=["station_lat", "station_lng"]).copy()
        st.plotly_chart(px.scatter_geo(
            locations, lat="station_lat", lon="station_lng", color="cluster_id",
            hover_name="station_id", hover_data=["avg_daily_pickup", "member_ratio"],
            projection="mercator", fitbounds="locations", title="站点需求类型分布",
        ), use_container_width=True)
with tabs[3]:
    if forecasts.empty:
        st.warning("暂无预测结果")
    else:
        station = st.selectbox("选择站点", sorted(forecasts.station_id.unique()))
        view = forecasts[forecasts.station_id == station].sort_values("timestamp")
        st.plotly_chart(px.line(view, x="timestamp", y=["pickup_count", "predicted_pickup"], title=f"{station} 实际与预测"), use_container_width=True)
        st.dataframe(view.tail(20), use_container_width=True)
    comparison_rows = []
    forecast_metrics = metrics.get("forecast", {})
    if forecast_metrics:
        comparison_rows.append({
            "模型": "Scikit-learn", "聚类 K": metrics.get("cluster", {}).get("k"),
            "测试行数": forecast_metrics.get("test_rows"), "MAE": forecast_metrics.get("mae"),
            "RMSE": forecast_metrics.get("rmse"), "R²": forecast_metrics.get("r2"),
            "基线 RMSE": forecast_metrics.get("baseline_rmse"),
        })
    if spark_metrics:
        comparison_rows.append({
            "模型": "Spark MLlib", "聚类 K": spark_metrics.get("cluster_k"),
            "测试行数": spark_metrics.get("test_rows"), "MAE": spark_metrics.get("mae"),
            "RMSE": spark_metrics.get("rmse"), "R²": spark_metrics.get("r2"),
            "基线 RMSE": spark_metrics.get("baseline_rmse"),
        })
    if comparison_rows:
        st.subheader("模型与基线对比")
        st.dataframe(pd.DataFrame(comparison_rows), hide_index=True, use_container_width=True)
with tabs[4]:
    st.json(quality)
    st.json(metrics)
    if spark_metrics:
        st.json(spark_metrics)

