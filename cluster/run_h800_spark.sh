#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_ROOT="${HOME}/bikeflow-tools"
export JAVA_HOME="${TOOLS_ROOT}/jre17"
export PATH="${JAVA_HOME}/bin:${PROJECT_ROOT}/.venv/bin:${PATH}"
export PYSPARK_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
export SPARK_LOCAL_IP="127.0.0.1"
export SPARK_LOCAL_DIRS="${PROJECT_ROOT}/var/spark"
EVENT_LOG_DIR="${PROJECT_ROOT}/var/spark-events"
mkdir -p "${SPARK_LOCAL_DIRS}" "${EVENT_LOG_DIR}"

exec "${PROJECT_ROOT}/.venv/bin/spark-submit" \
  --master 'local[8]' \
  --conf spark.eventLog.enabled=true \
  --conf "spark.eventLog.dir=file://${EVENT_LOG_DIR}" \
  "$@"
