FROM apache/airflow:2.9.3-python3.11

ENV PIP_CONFIG_FILE=/etc/pip.conf \
    PATH="/opt/airflow/snakemake-venv/bin:${PATH}"

USER root
COPY pip.conf /etc/pip.conf
RUN python -m venv /opt/airflow/snakemake-venv \
    && chown -R airflow:0 /opt/airflow/snakemake-venv

USER airflow
COPY requirements.txt /tmp/airflow-demo-airflow-requirements.txt
RUN /opt/airflow/snakemake-venv/bin/pip install --no-cache-dir -r /tmp/airflow-demo-airflow-requirements.txt
