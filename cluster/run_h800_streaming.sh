#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_ROOT="${HOME}/bikeflow-tools"
STREAMING_JAR="${TOOLS_ROOT}/hadoop-streaming-3.3.6.jar"
JAVA="${TOOLS_ROOT}/jre17/bin/java"
PYSPARK_JARS="${PROJECT_ROOT}/.venv/lib/python3.12/site-packages/pyspark/jars/*"
INPUT_PATH="${1:-data/spark/ride_clean_csv}"
OUTPUT_PATH="${2:-data/spark/streaming_station_hourly}"

if [[ ! -f "${STREAMING_JAR}" || ! -x "${JAVA}" ]]; then
  echo "Hadoop Streaming JAR or Java runtime is missing under ${TOOLS_ROOT}." >&2
  exit 1
fi
if [[ -e "${PROJECT_ROOT}/${OUTPUT_PATH}" ]]; then
  echo "Output already exists: ${OUTPUT_PATH}. Choose a new output path for this run." >&2
  exit 1
fi

export PATH="${PROJECT_ROOT}/.venv/bin:/usr/bin:/bin:${PATH}"
exec "${JAVA}" -cp "${STREAMING_JAR}:${PYSPARK_JARS}" \
  org.apache.hadoop.streaming.HadoopStreaming \
  -D mapreduce.framework.name=local \
  -D fs.defaultFS=file:/// \
  -D mapreduce.job.reduces=8 \
  -D stream.num.map.output.key.fields=2 \
  -D mapreduce.partition.keypartitioner.options=-k1,2 \
  -files "${PROJECT_ROOT}/hadoop/mapper.py,${PROJECT_ROOT}/hadoop/reducer.py" \
  -mapper "python3 mapper.py" \
  -reducer "python3 reducer.py" \
  -partitioner org.apache.hadoop.mapred.lib.KeyFieldBasedPartitioner \
  -input "${PROJECT_ROOT}/${INPUT_PATH}" \
  -output "${PROJECT_ROOT}/${OUTPUT_PATH}"
