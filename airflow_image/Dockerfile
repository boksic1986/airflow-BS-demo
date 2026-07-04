FROM apache/airflow:2.9.3-python3.11

ENV PIP_CONFIG_FILE=/etc/pip.conf

USER root
COPY pip.conf /etc/pip.conf

USER airflow
COPY requirements.txt /tmp/airflow-demo-airflow-requirements.txt
RUN pip install --no-cache-dir -r /tmp/airflow-demo-airflow-requirements.txt
