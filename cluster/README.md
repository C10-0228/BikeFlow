# 课程集群脚本

本目录保留 BikeFlow 项目用到的 H800 Spark、Hadoop Streaming 与 HBase 相关脚本。运行环境和数据文件需要由使用者自行配置。课程提供的 Docker 镜像、集群日志、原始数据和含示例密码的 Docker 配置未随代码公开。

- run_h800_spark.sh：在 H800 节点以 Spark local 模式运行 ETL 或 MLlib 作业。
- run_h800_streaming.sh：在本地 Hadoop runner 下执行 Streaming。
- run_hadoop_stage.sh：将代码和准备好的标准化数据复制到课程 Hadoop 容器。
- hbase_init.txt：HBase 建表与样例写入语句。

真实数据来源和字段处理见 ../docs/data_sources.md。脚本中的路径及环境变量需按实际运行机器调整。
