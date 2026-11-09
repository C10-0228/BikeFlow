from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables" / "BikeFlow_课程报告.docx"


def shade(cell, fill):
    pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    pr.append(shd)


def set_cell(cell, text, bold=False, color="27343A", size=9):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(str(text))
    r.bold = bold
    r.font.name = "Hiragino Sans GB"
    r.font.size = Pt(size)
    r.font.color.rgb = RGBColor.from_string(color)
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "Hiragino Sans GB")
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = "Table Grid"
    for i, h in enumerate(headers):
        set_cell(t.rows[0].cells[i], h, True, "FFFFFF", 9)
        shade(t.rows[0].cells[i], "146F5B")
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, value in enumerate(row):
            set_cell(cells[i], value, False, "27343A", 9)
            if ri % 2 == 1:
                shade(cells[i], "F0F5F3")
    if widths:
        for row in t.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Inches(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return t


def para(doc, text, style=None):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.12
    p.add_run(text)
    return p


def bullet(doc, text):
    return para(doc, text, "List Bullet")


def heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    p.add_run(text)
    return p


def build():
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Inches(0.72)
    sec.bottom_margin = Inches(0.68)
    sec.left_margin = Inches(0.82)
    sec.right_margin = Inches(0.82)
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Hiragino Sans GB"
    normal.font.size = Pt(10)
    normal.font.color.rgb = RGBColor(39, 52, 58)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Hiragino Sans GB")
    for name, size, color in [("Title", 26, "173C36"), ("Heading 1", 16, "146F5B"), ("Heading 2", 12, "3B77A5")]:
        st = styles[name]
        st.font.name = "Hiragino Sans GB"
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor.from_string(color)
        st._element.rPr.rFonts.set(qn("w:eastAsia"), "Hiragino Sans GB")

    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("BikeFlow 课程项目报告")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("共享单车时空需求分析、站点聚类与短时预测")
    r.font.size = Pt(13)
    r.font.color.rgb = RGBColor(91, 107, 112)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("CS4303 大数据处理课程项目 | 个人完成")
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(20, 111, 91)
    doc.add_paragraph()

    heading(doc, "摘要", 1)
    para(doc, "本项目面向共享单车运营中的站点需求分析问题，构建了从公开数据采集、质量清洗、天气关联、站点小时聚合，到站点聚类、短时需求预测和可视化展示的分析流程。分析数据为 Citi Bike 2024 年第一季度月度行程归档及纽约市逐小时天气。标准化行程共 6,672,881 条，经质量规则处理后保留 6,653,987 条，保留率为 99.7169%。")
    para(doc, "全量 Pandas 与 Spark SQL/MLlib 实验均完成。Pandas 回归模型测试 RMSE 为 1.8198，Spark MLlib 为 1.8444，均优于各自的 lag-24 基线（约 2.43）。此外，Hadoop Streaming 在 H800 local runner 上对全量清洗数据完成计算；课程 Hadoop/YARN、HBase、Hive 镜像在本地 Colima 集群完成了小样例验证。两类实验使用的数据规模和执行环境不同，报告分别列出，不将样例验证表述为全量集群计算。")
    para(doc, "关键词：共享单车；Spark SQL；MLlib；Hadoop Streaming；站点聚类；需求预测")

    heading(doc, "1 项目背景与研究目标", 1)
    para(doc, "共享单车运营需要了解不同站点在不同时段的使用差异，以安排车辆调度并降低缺车或积压风险。原始行程数据记录的是单次出行，无法直接表示站点每小时的供需变化；因此需要将行程、时间与天气信息转换为可分析的时空特征，再通过数据挖掘方法提取站点类型和需求规律。")
    para(doc, "本项目围绕三个问题展开：第一，取车需求随小时、星期和天气如何变化；第二，哪些站点的客群和时段使用模式相近；第三，基于历史需求和时序、天气特征的模型能否优于前一天同一小时的朴素预测。")
    bullet(doc, "建设可复现的数据处理流程，对行程记录进行规则化清洗、天气关联和站点小时级汇总。")
    bullet(doc, "以聚类形成站点画像，并用严格按时间顺序划分的测试集评估下一小时出发量预测。")
    bullet(doc, "将分析结果整理为图表与交互式 Dashboard，并用 Hadoop 生态组件验证批处理、存储与查询链路。")

    heading(doc, "2 数据来源与质量控制", 1)
    heading(doc, "2.1 数据来源与范围", 2)
    para(doc, "行程数据来自 Citi Bike 官方 202401、202402、202403 月度归档；天气数据来自 Open-Meteo 历史天气接口，位置为纽约市坐标（40.7128, -74.0060），字段包括气温、降水和风速。月度归档包含少量跨月行程，实际行程起止时间为 2023-12-31 13:50:28 至 2024-03-31 23:57:16。数据采用分块转换，真实数据与开发样例保存在不同目录。")
    heading(doc, "2.2 清洗规则", 2)
    para(doc, "处理流程解析开始和结束时间，计算骑行时长，并按互斥优先级标记缺失行程 ID、重复行程、无效时间、超出 1 至 1,440 分钟范围的时长，以及缺失起点或终点站点 ID 的记录。天气按行程开始时间向下取整到小时后左连接；未匹配天气的行程保留，并记录缺失标志，避免因辅助数据缺失而丢弃有效行程。")
    table(doc, ["质量指标", "结果", "说明"], [
        ["标准化输入", "6,672,881", "三个月官方归档"],
        ["清洗后保留", "6,653,987", "有效行程"],
        ["拒绝记录", "18,894", "保留率 99.7169%"],
        ["无效时长", "2,123", "时长规则"],
        ["缺失起点 / 终点站", "5,806 / 10,965", "按拒绝优先级互斥计数"],
        ["天气匹配率", "99.9945%", "未匹配天气行程仍保留"],
    ], [1.7, 1.6, 3.8])
    para(doc, "拒绝原因计数之和与拒绝总量一致，质量指标保存于 artifacts/data_quality.json。")

    heading(doc, "3 系统设计与实现", 1)
    heading(doc, "3.1 总体架构", 2)
    para(doc, "系统分为数据接入、清洗与转换、分析建模、结果存储和可视化五个环节。公开 CSV/JSON 经标准化后进入 Pandas 或 Spark 作业；Spark SQL 输出 Parquet 事实表和站点小时表；MLlib 与 Pandas 流程分别完成聚类和回归评估；Hadoop Streaming 生成独立的站点小时汇总；本地课程镜像集群进一步验证 HDFS/YARN、HBase 与 Hive 的组件协作。Dashboard 读取预先生成的指标和结果文件，不在页面请求时重新训练全量模型。")
    table(doc, ["模块", "实现", "主要产物"], [
        ["数据准备", "Python 分块转换、字段映射", "标准化行程与天气 CSV"],
        ["全量 ETL", "Pandas、Spark SQL 3.5.5", "清洗事实表、站点小时 Parquet"],
        ["分布式批处理", "Hadoop Streaming 3.3.6", "站点-小时汇总"],
        ["建模", "KMeans、线性回归、Spark MLlib", "站点分群、预测指标"],
        ["存储查询验证", "HDFS/YARN、HBase、Hive 课程镜像", "集群证据与查询输出"],
        ["结果展示", "Streamlit", "总览、趋势、地图、预测、质量视图"],
    ], [1.45, 2.7, 2.95])
    heading(doc, "3.2 站点小时数据建模", 2)
    para(doc, "出发量按出发站 ID 与行程开始小时统计，到达量按到达站 ID 与结束小时统计，分别生成后再合并。以站点全集和连续小时序列形成稠密网格；无行程组合的计数补零，天气和站点坐标作为辅助字段，并构造 lag-1、lag-24 等时序特征。这样的口径保证站点小时表中取车量和还车量分别能与有效行程总数对账。")
    heading(doc, "3.3 Hadoop Streaming", 2)
    para(doc, "Mapper 从 CSV 行中解析站点、开始小时、骑行时长和会员标志，将站点与小时作为复合键输出；Reducer 对同键行程累计次数、时长和会员数。全量 H800 实验由 8 个 reducer 处理清洗后的 6,653,987 条记录，产生 1,962,057 个键，pickup 总数对账为 6,653,987。该次 Hadoop Streaming 使用 local runner，不是 HDFS/YARN 多节点执行。")
    heading(doc, "3.4 聚类与需求预测", 2)
    para(doc, "站点聚类使用平均每日出发量、平均每日到达量、会员比例、平均时长和早高峰出发比例等特征。Pandas 版本对标准化特征使用 KMeans，固定 K=4；Spark MLlib 在 K=2、3、4 中依据 silhouette 选择 K=3。两套流程各自的特征处理和引擎实现不同，silhouette 只用于候选方案参考，不将数值差异直接解释为某一引擎更优。")
    para(doc, "预测目标为站点下一小时出发量，特征包含历史滞后需求、滚动均值、小时周期、星期与天气等变量。数据按时间排序后划分训练集和测试集，不随机打乱。基线为 lag-24，即前一天同一小时的需求。使用 MAE、RMSE 和 R² 评估回归结果。该实验是离线回测，不是线上实时预测。")

    heading(doc, "4 实验环境与执行方法", 1)
    table(doc, ["实验", "环境与数据", "执行口径"], [
        ["Pandas 全量", "H800 个人目录；真实季度数据", "CPU，离线批处理"],
        ["Spark SQL/MLlib 全量", "H800；Spark 3.5.5、Java 17", "local[8]，本地文件系统，CPU"],
        ["Hadoop Streaming 全量", "H800；Hadoop Streaming 3.3.6", "local runner，8 reducers"],
        ["课程 Hadoop 生态验证", "macOS Colima；课程 Hadoop/HBase/Hive 镜像", "约 178,501 行仓库样例；YARN/HDFS 多节点"],
    ], [1.7, 3.2, 2.2])
    para(doc, "H800 的 GPU 当时由其他任务占用，Spark 作业使用 CPU。课程镜像实验使用本机 Colima 虚拟机，启动 2 个 DataNode 和 2 个 NodeManager，并复用课程作业中已有镜像与数据卷。全量真实数据实验和课程组件验证是两套独立实验，不应合并其样本量或执行模式。")
    heading(doc, "5 实验结果与分析", 1)
    heading(doc, "5.1 全量数据处理核验", 2)
    table(doc, ["核验项", "结果"], [
        ["Spark 清洗行程", "6,653,987"],
        ["站点小时网格", "5,079,230 行、2,314 个站点"],
        ["pickup 总量", "6,653,987，与有效行程数一致"],
        ["dropoff 总量", "6,653,987，与有效行程数一致"],
        ["Parquet 分区文件", "2,195 个"],
    ], [2.3, 4.8])
    para(doc, "Pandas 与 Spark 的独立起点和终点聚合均与有效行程总量相符。Spark 输出按日期和小时组织；控制分区并减少小文件后，站点小时网格仍覆盖至最后一条行程的结束小时。")
    heading(doc, "5.2 模型回测", 2)
    table(doc, ["实现", "测试行数", "模型 MAE", "基线 MAE", "模型 RMSE", "基线 RMSE", "模型 R²"], [
        ["Pandas", "754,364", "0.9716", "1.1535", "1.8198", "2.4335", "0.6760"],
        ["Spark MLlib", "756,678", "0.9847", "1.1549", "1.8444", "2.4354", "0.6675"],
    ], [1.1, 1.0, 0.9, 0.9, 1.0, 1.0, 0.9])
    para(doc, "两种回归实现均在各自测试集上降低 MAE 与 RMSE。Spark 测试行数为 756,678，Pandas 为 754,364，因处理与样本边界存在少量差异，宜分别对比各自的 lag-24 基线，不据此将两种实现的微小指标差异归因为框架性能。")
    heading(doc, "5.3 本地课程集群验证", 2)
    para(doc, "本地课程镜像运行的输入为仓库内约 178,501 行开发样例，与 H800 的季度全量数据不同。HDFS 运行 2 个 DataNode，原始文件副本因子为 2，fsck 检查结果 HEALTHY；YARN 运行 2 个 NodeManager。Hadoop Streaming 作业读取 178,502 行（包含 CSV 表头），Mapper 输出 89,255 条有效记录，Reducer 归并为 8,661 个站点小时键，pickup 总量 89,255，作业状态 SUCCEEDED。")
    para(doc, "HBase 三节点服务启动后，表 bikeflow_station_hourly 通过 ImportTsv 导入 8,661 行，成功作业计数为 Map input records=8,661、Map output records=8,661、Bad Lines=0。HiveServer2、MySQL metastore、bikeflow 数据库和外部表 station_hourly_streaming 已建立，Beeline 的 LIMIT 查询返回样例。一次全表聚合运行期间 HiveServer2 连接中断，因此不报告全表 SQL 聚合值；现有 Hive 验证限于服务、建表与样例读取。详细日志位于 cluster/evidence/。")

    heading(doc, "6 可视化与成果", 1)
    para(doc, "Streamlit Dashboard 提供运营总览、趋势分析、站点地图、站点聚类、需求预测和数据质量相关视图。图表消费预计算结果，便于按站点及时间查看分析结果。项目代码中包含数据准备、Pandas 主流程、Spark ETL、MLlib、Streaming Mapper/Reducer、HBase 发布辅助脚本、Hive SQL、容器编排和运行手册。")
    para(doc, "成果包括 6,653,987 条清洗行程的全量分析结果、站点小时级数据集、站点聚类与预测指标、H800 Streaming 结果、课程镜像集群证据、Dashboard、10 页课程汇报 PPT 与本报告。自动化测试结果为 6 项通过。")

    heading(doc, "7 讨论与局限", 1)
    bullet(doc, "H800 Spark 使用 local[8] 和 CPU，没有使用 GPU，也不是 YARN 集群 Spark 执行。")
    bullet(doc, "全量 Hadoop Streaming 在 H800 使用 local runner；课程本地集群的 YARN/HDFS、HBase、Hive 验证使用开发样例数据，尚未将 660 多万条全量数据重新放入该课程集群完成端到端处理。")
    bullet(doc, "Hive 外部表样例查询已通过，但全表聚合未完成；HBase 导入的是样例的站点小时结果，不是完整的预测模型服务部署。")
    bullet(doc, "数据只覆盖 2024 年第一季度，季节代表性有限。天气输入使用历史观测值，实际上线预测需用未来天气预报或调整特征。")
    bullet(doc, "Silhouette 反映聚类内聚与分离程度，不直接代表调度收益；需要后续结合车辆调度成本、缺车率和服务水平评估运营价值。")

    heading(doc, "8 结论", 1)
    para(doc, "BikeFlow 完成了真实共享单车数据从标准化、质量控制、时空聚合到聚类和需求回测的完整分析流程。Spark SQL 全量处理与 Pandas 结果均通过行程总量对账；Pandas 与 Spark MLlib 回归模型在时间切分测试集上均优于 lag-24 基线。Hadoop Streaming 全量 local 处理验证了 Mapper/Reducer 逻辑，课程镜像集群进一步证明 HDFS/YARN、HBase 和 Hive 的基本服务链路可运行。报告明确区分本地样例集群与 H800 全量实验结果。")
    para(doc, "后续工作可将全量真实数据导入课程 HDFS/YARN 集群，重跑 Spark 与 Streaming；在 Hive 中完成可复核的完整聚合查询，在 HBase 中发布完整站点画像与预测记录；增加跨季节数据并通过调度成本指标验证模型的运营效益。")

    heading(doc, "9 成员分工与资源", 1)
    table(doc, ["成员", "承担工作"], [["单人完成", "选题与方案设计；数据采集、标准化和质量控制；Pandas 与 Spark SQL/MLlib 实现及实验；Hadoop/HBase/Hive 集群验证；Dashboard、结果分析、测试和汇报材料。"]], [1.2, 5.9])
    para(doc, "数据来源：Citi Bike System Data，https://citibikenyc.com/system-data；Open-Meteo Historical Weather API，https://open-meteo.com/en/docs/historical-weather-api。数据文件校验和、字段说明和转换流程见 docs/data_sources.md。")
    para(doc, "源代码、运行脚本、数据处理产物和集群证据随课程作业目录提供；当前没有独立代码仓库或网盘链接。主入口为 README.md，运行步骤见 docs/runbook.md，Hadoop 生态证据见 cluster/evidence/。")

    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer.add_run("CS4303 大数据处理课程项目 | BikeFlow")
    fr.font.size = Pt(8)
    fr.font.color.rgb = RGBColor(120, 132, 135)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
