"""Build the BikeFlow course presentation from verified project artifacts."""
import json
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables" / "BikeFlow_课程汇报.pptx"
GREEN = RGBColor(20, 117, 94)
INK = RGBColor(35, 48, 53)
MUTED = RGBColor(91, 107, 112)
PAPER = RGBColor(247, 249, 247)
PALE_GREEN = RGBColor(224, 240, 233)
BLUE = RGBColor(59, 119, 165)
CORAL = RGBColor(217, 111, 83)
WHITE = RGBColor(255, 255, 255)
FONT = "Microsoft YaHei"


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def set_text(box, text, size=18, color=INK, bold=False, align=None):
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    for index, line in enumerate(str(text).split("\n")):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.font.name = FONT
        paragraph.font.size = Pt(size)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = color
        paragraph.space_after = Pt(8)
        if align is not None:
            paragraph.alignment = align
    return box


def textbox(slide, x, y, w, h, text, size=18, color=INK, bold=False, align=None):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    box.text_frame.margin_left = Inches(0.03)
    box.text_frame.margin_right = Inches(0.03)
    box.text_frame.margin_top = Inches(0.02)
    box.text_frame.margin_bottom = Inches(0.02)
    return set_text(box, text, size, color, bold, align)


def rect(slide, x, y, w, h, fill, line=None, radius=False):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.fill.background() if line is None else None
    if line is not None:
        shape.line.color.rgb = line
    if radius:
        shape.adjustments[0] = 0.08
    return shape


def new_slide(prs, title, kicker="BIKEFLOW"):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = PAPER
    textbox(slide, 0.65, 0.34, 3.5, 0.28, kicker, 10, GREEN, True)
    textbox(slide, 0.65, 0.76, 12.0, 0.62, title, 27, INK, True)
    rect(slide, 0.65, 1.49, 0.72, 0.05, GREEN)
    textbox(slide, 0.65, 7.12, 10.8, 0.2, "CS4303 大数据处理课程项目  |  真实数据实验", 9, MUTED)
    textbox(slide, 12.1, 7.08, 0.55, 0.25, str(len(prs.slides)), 10, MUTED, align=PP_ALIGN.RIGHT)
    return slide


def add_metric(slide, x, y, w, value, label, accent=GREEN):
    rect(slide, x, y, w, 1.2, WHITE, radius=True)
    rect(slide, x, y, 0.06, 1.2, accent)
    textbox(slide, x + 0.2, y + 0.13, w - 0.35, 0.47, value, 23, accent, True)
    textbox(slide, x + 0.2, y + 0.68, w - 0.35, 0.32, label, 12, MUTED)


def add_bullets(slide, x, y, w, items, size=18, gap=0.75):
    for index, item in enumerate(items):
        yy = y + index * gap
        rect(slide, x, yy + 0.08, 0.13, 0.13, GREEN)
        textbox(slide, x + 0.28, yy, w - 0.28, gap, item, size, INK)


def build():
    quality = read_json("artifacts/data_quality.json")
    pandas_metrics = read_json("artifacts/metrics.json")
    spark_metrics = read_json("artifacts/spark_mllib_metrics.json")
    spark_check = read_json("artifacts/cluster_run/spark_verification.json")

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = PAPER
    rect(slide, 8.7, 0, 4.63, 7.5, GREEN)
    textbox(slide, 0.85, 0.8, 5.7, 0.35, "CS4303  |  BIG DATA PROCESSING", 12, GREEN, True)
    textbox(slide, 0.85, 1.65, 6.8, 1.05, "BikeFlow", 42, INK, True)
    textbox(slide, 0.87, 2.8, 6.5, 1.2, "共享单车需求分析\n与站点画像", 28, INK, True)
    textbox(slide, 0.9, 4.42, 6.4, 0.9, "从真实行程数据到站点小时统计、聚类和短时需求回测", 18, MUTED)
    textbox(slide, 0.9, 6.55, 6.2, 0.3, "Citi Bike 2024 Q1  |  Pandas + Spark SQL + MLlib", 12, MUTED)
    for i, (big, small, color) in enumerate([
        ("6.65M", "清洗后行程", PALE_GREEN),
        ("2,314", "站点", RGBColor(221, 235, 245)),
        ("1.84", "MLlib RMSE", RGBColor(248, 229, 219)),
    ]):
        yy = 1.45 + i * 1.55
        rect(slide, 9.25, yy, 3.4, 1.08, color, radius=True)
        textbox(slide, 9.55, yy + 0.12, 2.7, 0.42, big, 26, INK, True)
        textbox(slide, 9.55, yy + 0.62, 2.7, 0.25, small, 12, MUTED)

    slide = new_slide(prs, "从运营问题出发：何时、何地、需要多少车？")
    cards = [
        (0.8, "需求节律", "比较小时、星期和天气\n下的取车变化", GREEN),
        (4.65, "站点分层", "识别使用模式相近的\n站点群组", BLUE),
        (8.5, "提前预估", "用历史需求估计未来\n小时的站点出发量", CORAL),
    ]
    for x, title, desc, color in cards:
        rect(slide, x, 2.0, 3.45, 2.75, WHITE, radius=True)
        rect(slide, x, 2.0, 3.45, 0.12, color)
        textbox(slide, x + 0.25, 2.42, 2.95, 0.45, title, 21, color, True)
        textbox(slide, x + 0.25, 3.15, 2.9, 1.0, desc, 17, INK)
    textbox(slide, 0.9, 5.55, 11.2, 0.7, "项目重点：数据预处理与 Spark 分析、数据挖掘与机器学习。", 18, MUTED)

    slide = new_slide(prs, "数据规模与来源")
    add_metric(slide, 0.8, 2.0, 2.8, "6,672,881", "标准化行程", GREEN)
    add_metric(slide, 3.8, 2.0, 2.8, "6,653,987", "清洗后行程", BLUE)
    add_metric(slide, 6.8, 2.0, 2.8, "2,314", "站点全集", CORAL)
    add_metric(slide, 9.8, 2.0, 2.8, "2,184", "逐小时天气点", GREEN)
    add_bullets(slide, 1.0, 4.0, 11.2, [
        "行程：Citi Bike 2024 年 1 至 3 月官方月度归档，50 万行分块标准化。",
        "天气：Open-Meteo 纽约市历史逐小时气温、降水和风速。",
        "归档含跨月骑行，实际记录范围为 2023-12-31 13:50 至 2024-03-31 23:57。",
    ], 15, 0.65)

    slide = new_slide(prs, "端到端处理链路")
    stages = [
        (0.8, "公开 CSV / JSON", "Citi Bike\nOpen-Meteo", GREEN),
        (3.25, "标准化与清洗", "字段统一\n质量规则", BLUE),
        (5.7, "Spark SQL", "事实表\n站点小时表", CORAL),
        (8.15, "分析与建模", "Hive SQL 设计\nKMeans / 回归", GREEN),
        (10.6, "结果展示", "Dashboard\n报告与证据", BLUE),
    ]
    for x, title, desc, color in stages:
        rect(slide, x, 2.45, 1.95, 1.82, WHITE, radius=True)
        rect(slide, x, 2.45, 1.95, 0.1, color)
        textbox(slide, x + 0.12, 2.78, 1.72, 0.42, title, 15, color, True, PP_ALIGN.CENTER)
        textbox(slide, x + 0.12, 3.35, 1.72, 0.72, desc, 12, MUTED, align=PP_ALIGN.CENTER)
    for x in (2.87, 5.32, 7.77, 10.22):
        textbox(slide, x, 3.08, 0.32, 0.35, "→", 21, MUTED, True, PP_ALIGN.CENTER)
    textbox(slide, 1.0, 5.18, 11.1, 0.85,
            "H800 使用 Spark 3.5.5 local[8] 执行真实数据作业；输出写在个人目录的本地文件系统。", 16, INK)
    textbox(slide, 1.0, 6.02, 11.1, 0.48,
            "课程 Docker 集群另行验证 Hadoop/YARN、HBase 与 Hive；H800 Spark 未使用 GPU。", 13, CORAL, True)

    slide = new_slide(prs, "数据质量：规则透明，账目可核验")
    add_metric(slide, 0.9, 2.0, 3.1, "99.7169%", "行程保留率", GREEN)
    add_metric(slide, 4.35, 2.0, 3.1, "18,894", "拒绝记录", CORAL)
    add_metric(slide, 7.8, 2.0, 3.1, "99.9945%", "天气匹配率", BLUE)
    textbox(slide, 1.0, 3.75, 5.0, 0.4, "拒绝原因", 18, INK, True)
    add_bullets(slide, 1.0, 4.28, 5.2, [
        "无效时长：2,123",
        "缺少出发站：5,806",
        "缺少到达站：10,965",
    ], 15, 0.55)
    rect(slide, 7.0, 3.72, 5.0, 1.95, PALE_GREEN, radius=True)
    textbox(slide, 7.35, 4.05, 4.3, 1.2,
            "清洗 6,653,987 条\npickup 总量 = dropoff 总量\n两侧均对账到每条有效行程", 17, GREEN, True)

    slide = new_slide(prs, "站点小时表：分别刻画出发与到达")
    rect(slide, 0.95, 2.05, 5.2, 1.35, RGBColor(221, 235, 245), radius=True)
    textbox(slide, 1.25, 2.3, 4.55, 0.5, "Pickup = 按出发站 × 开始小时计数", 17, BLUE, True)
    rect(slide, 7.05, 2.05, 5.2, 1.35, RGBColor(248, 229, 219), radius=True)
    textbox(slide, 7.35, 2.3, 4.55, 0.5, "Dropoff = 按到达站 × 结束小时计数", 17, CORAL, True)
    textbox(slide, 6.25, 2.48, 0.6, 0.4, "+", 23, MUTED, True, PP_ALIGN.CENTER)
    add_bullets(slide, 1.1, 4.15, 11.2, [
        "按站点全集与连续小时构造完整网格；零出发小时计为 0，支持 lag-24 特征。",
        "最终网格：5,079,230 行 × 2,314 个站点；输出 2,195 个日期/小时分区文件。",
        "Spark 分区文件数从 19,755 降低到 2,195，减轻后续扫描小文件开销。",
    ], 15, 0.65)

    slide = new_slide(prs, "站点画像：需求、客群和时段偏好")
    feature_names = ["平均每日出发量", "平均每日到达量", "会员比例", "平均骑行时长", "早高峰比例"]
    feature_colors = [GREEN, BLUE, CORAL, GREEN, BLUE]
    for index, (name, color) in enumerate(zip(feature_names, feature_colors)):
        x = 0.9 + (index % 3) * 4.05
        y = 2.0 + (index // 3) * 1.55
        rect(slide, x, y, 3.55, 1.05, WHITE, radius=True)
        rect(slide, x, y, 0.08, 1.05, color)
        textbox(slide, x + 0.22, y + 0.3, 3.0, 0.42, name, 16, INK, True)
    rect(slide, 0.9, 5.55, 11.5, 0.76, PALE_GREEN, radius=True)
    textbox(slide, 1.15, 5.72, 11.0, 0.42,
            "Pandas K=4（silhouette 0.3376）  |  Spark MLlib 自动选 K=3（silhouette 0.6413）", 15, GREEN, True)
    textbox(slide, 1.0, 6.42, 11.0, 0.35, "聚类用于探索性站点分层，运营收益仍需结合调度成本验证。", 12, MUTED)

    slide = new_slide(prs, "短时需求回测：两套实现均优于 lag-24")
    chart_data = CategoryChartData()
    chart_data.categories = ["Pandas", "Spark MLlib"]
    chart_data.add_series("模型 RMSE", [pandas_metrics["forecast"]["rmse"], spark_metrics["rmse"]])
    chart_data.add_series("lag-24 基线 RMSE", [pandas_metrics["forecast"]["baseline_rmse"], spark_metrics["baseline_rmse"]])
    chart = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.85), Inches(2.0), Inches(7.0), Inches(4.25), chart_data).chart
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.value_axis.minimum_scale = 0
    chart.value_axis.has_major_gridlines = True
    chart.category_axis.tick_labels.font.name = FONT
    chart.category_axis.tick_labels.font.size = Pt(12)
    chart.value_axis.tick_labels.font.name = FONT
    chart.value_axis.tick_labels.font.size = Pt(11)
    chart.series[0].format.fill.solid()
    chart.series[0].format.fill.fore_color.rgb = GREEN
    chart.series[1].format.fill.solid()
    chart.series[1].format.fill.fore_color.rgb = CORAL
    textbox(slide, 8.2, 2.1, 4.0, 0.45, "按时间顺序切分测试集", 18, INK, True)
    textbox(slide, 8.2, 2.8, 4.15, 2.0,
            f"Pandas\nMAE {pandas_metrics['forecast']['mae']:.4f}  |  R² {pandas_metrics['forecast']['r2']:.4f}\n\nSpark MLlib\nMAE {spark_metrics['mae']:.4f}  |  R² {spark_metrics['r2']:.4f}", 15, MUTED)
    textbox(slide, 8.2, 5.22, 4.15, 0.76, "两引擎测试行数略有差异，分别与自身基线比较。", 12, CORAL, True)

    slide = new_slide(prs, "课程集群验证结果")
    left = [
        "Hadoop/YARN：2 个 DataNode、2 个 NodeManager；Streaming 作业状态 SUCCEEDED。",
        "MapReduce：读取 178,502 行，输出 8,661 个站点小时分组，pickup 合计 89,255。",
        "HDFS：原始数据副本因子 2，fsck 状态 HEALTHY。",
    ]
    right = [
        "HBase：三节点服务就绪；ImportTsv 导入 8,661 行，Bad Lines=0。",
        "Hive：HiveServer2、MySQL metastore、bikeflow 外部表和 Beeline 查询已验证。",
        "数据口径：课程集群使用仓库样例数据；H800 另有 665 万条全量 Spark 结果。",
    ]
    textbox(slide, 0.95, 2.05, 5.3, 0.4, "Hadoop / YARN / HDFS", 19, GREEN, True)
    add_bullets(slide, 0.95, 2.62, 5.5, left, 14, 0.95)
    textbox(slide, 7.0, 2.05, 5.1, 0.4, "HBase / Hive", 19, CORAL, True)
    add_bullets(slide, 7.0, 2.62, 5.35, right, 14, 0.95)
    textbox(slide, 1.0, 6.15, 11.2, 0.55, "结论：Hadoop 生态链路已完成可复核验证，证据保存在 cluster/evidence/。", 16, INK, True)

    slide = new_slide(prs, "复现入口、成员与资源")
    add_bullets(slide, 1.0, 2.0, 11.2, [
        "复现入口：README.md、docs/runbook.md；完整说明：docs/项目报告_BikeFlow.md。",
        "结果证据：artifacts/ 下的数据质量、Spark 核验、MLlib 指标和预测结果文件。",
        "成员分工：单人完成，负责选题、数据、清洗、Spark、Hadoop/HBase/Hive、Dashboard、PPT。",
        "公开数据：Citi Bike system-data；天气：Open-Meteo historical weather API。",
        "代码资源：随本次课程作业目录提供；当前无独立代码仓库或网盘链接。",
    ], 15, 0.78)
    rect(slide, 1.0, 6.2, 11.1, 0.6, PALE_GREEN, radius=True)
    textbox(slide, 1.25, 6.3, 10.6, 0.35, "谢谢", 19, GREEN, True, PP_ALIGN.CENTER)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
