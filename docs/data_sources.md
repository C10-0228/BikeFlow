# 数据来源

## Citi Bike 行程记录

- 发布方：Citi Bike / Lyft
- 入口页：https://citibikenyc.com/system-data
- 归档目录：https://s3.amazonaws.com/tripdata/
- 本项目窗口：2024-01-01 至 2024-03-31，按月下载 202401、202402、202403 归档。
- 本地原始归档：`data/raw/citibike_source/`
- 标准化结果：`data/raw/real/trips.csv`
- 转换脚本：`jobs/prepare_citibike_data.py`
- 字段处理：保留行程、车辆、起止时间、站点 ID/名称、坐标和会员类型；将 `member_casual` 统一为 `member_type`。使用 50 万行分块读取，避免将压缩包或完整原始表一次性载入内存。
- 标准化行程数：6,672,881。
- 月度归档含跨月骑行记录；处理后的实际时间范围为 2023-12-31 13:50:28 至 2024-03-31 23:57:16（本地时间）。因此，归档月份是下载窗口，不能将每条行程都描述为严格落在 2024-01-01 至 2024-03-31。
- SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `202401-citibike-tripdata.zip` | `0a2e81eacd7bf3890712de8f2a1b56bda985c17d9e61b08acf5e7c7ec9f20eb0` |
| `202402-citibike-tripdata.zip` | `f0209d02b862ec7422ea251f55626c007c8289adb62230e870ed7da24ef77f05` |
| `202403-citibike-tripdata.zip` | `d1a58caa37a66bbe6477680f3fba283f6f638475855591a4a2e8b73dc4cf8470` |

## 天气

- 发布方：Open-Meteo
- 历史天气 API 文档：https://open-meteo.com/en/docs/historical-weather-api
- 查询位置：纽约市，纬度 40.7128，经度 -74.0060。
- 查询窗口：2024-01-01 至 2024-03-31，时区 `America/New_York`。
- 查询变量：`temperature_2m`、`precipitation`、`wind_speed_10m`。
- 原始响应：`data/raw/weather_source/open_meteo_nyc_2024q1.json`
- 标准化结果：`data/raw/real/weather.csv`
- 派生字段：依次对应 `weather_time`、`temperature`、`precipitation`、`wind_speed`。
- 原始响应 SHA-256：`ae600de833da6fdfc49b3ed7f3147b9435fa1e017f4d80af11e6294baece610a`。

## 样本数据

`data/raw/trips.csv` 和 `data/raw/weather.csv` 由 `jobs/generate_sample_data.py` 确定性生成，仅用于开发测试。季度真实数据使用独立的 `data/raw/real/` 路径，避免与样本混淆。

## Hadoop Streaming 运行依赖

- Maven 坐标：`org.apache.hadoop:hadoop-streaming:3.3.6`
- 下载地址：`https://repo.maven.apache.org/maven2/org/apache/hadoop/hadoop-streaming/3.3.6/hadoop-streaming-3.3.6.jar`
- JAR SHA-256：`be2389303a89ca4e45eaf2eb6ed7b5d219da2d9b4e106f5687575155450d6054`
- Hadoop 客户端 API/runtime JAR 由 H800 项目虚拟环境中的 PySpark 提供；运行方式和 local runner 限制见 `README.md`。
