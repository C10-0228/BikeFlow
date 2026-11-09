PYTHON ?= .venv/bin/python

.PHONY: install sample etl prepare-real real test dashboard presentation check-env clean

install:
	$(PYTHON) -m pip install -r requirements.txt

sample:
	$(PYTHON) jobs/generate_sample_data.py

etl: sample
	$(PYTHON) jobs/pipeline.py

prepare-real:
	$(PYTHON) jobs/prepare_citibike_data.py \
	  --trip-archives data/raw/citibike_source/202401-citibike-tripdata.zip \
	    data/raw/citibike_source/202402-citibike-tripdata.zip \
	    data/raw/citibike_source/202403-citibike-tripdata.zip \
	  --weather-json data/raw/weather_source/open_meteo_nyc_2024q1.json

real: prepare-real
	$(PYTHON) jobs/pipeline.py --trip data/raw/real/trips.csv --weather data/raw/real/weather.csv

test:
	$(PYTHON) -m pytest -q

dashboard:
	$(PYTHON) -m streamlit run dashboard/app.py --server.port 8501

presentation:
	$(PYTHON) jobs/build_presentation.py

check-env:
	@command -v java >/dev/null && java -version || true
	@command -v hadoop >/dev/null && hadoop version || echo 'hadoop: not installed (optional for local run)'
	@command -v hive >/dev/null && hive --version || echo 'hive: not installed (optional for local run)'
	@command -v spark-submit >/dev/null && spark-submit --version || echo 'spark-submit: not installed (optional for local run)'
	@command -v hbase >/dev/null && hbase version || echo 'hbase: not installed (optional for local run)'

clean:
	$(PYTHON) -c "from pathlib import Path; import shutil; [shutil.rmtree(p) for p in [Path('data/processed'), Path('artifacts')] if p.exists()]; Path('data/processed').mkdir(parents=True); Path('artifacts').mkdir(parents=True)"

