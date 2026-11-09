# BikeFlow

共享单车行程的需求分析、站点聚类与短时预测课程项目。此目录包含源代码、运行配置、测试和数据来源说明；原始数据、模型文件与运行产物未包含。

## 本地运行

1. 安装 requirements.txt 中的依赖。
2. 运行 python jobs/generate_sample_data.py 生成开发样本。
3. 运行 python jobs/pipeline.py 执行分析。
4. 运行 streamlit run dashboard/app.py 查看结果。

真实数据的获取与转换方法见 docs/data_sources.md。Hadoop、Spark、Hive 和 HBase 的运行说明见 cluster/README.md。
