ARG BASE_IMAGE=172.17.61.235:2333/niptpro/niptpro:1.0.11
FROM ${BASE_IMAGE}

USER root

COPY nipt_s9_image/environment.yaml /tmp/nipt-snakemake9-environment.yaml
RUN micromamba create -y -p /opt/snakemake9 -f /tmp/nipt-snakemake9-environment.yaml \
    && micromamba clean --all --yes \
    && rm -f /tmp/nipt-snakemake9-environment.yaml

COPY dags/snakemake_logger_plugin_airflow_demo /opt/airflow-demo-plugins/snakemake_logger_plugin_airflow_demo
COPY nipt_s9_image/run_nipt_s9.sh /opt/airflow-demo/bin/run_nipt_s9.sh
RUN chmod 0755 /opt/airflow-demo/bin/run_nipt_s9.sh \
    && PYTHONPATH=/opt/airflow-demo-plugins /opt/snakemake9/bin/python -c "import snakemake_logger_plugin_airflow_demo" \
    && test "$(/opt/snakemake9/bin/snakemake --version)" = "9.23.1" \
    && test "$(/opt/conda/bin/snakemake --version)" = "7.32.4"

LABEL org.opencontainers.image.title="NIPTPro 1.0.11 with Snakemake 9"
LABEL org.opencontainers.image.version="1.0.11-snakemake9.23.1-v1"
LABEL airflow-demo.nipt.base-image-id="sha256:1cd289afbd0c48564a530b1a56dd608dc2803b63ed6a4a4c0ca313ef84380b26"
LABEL airflow-demo.nipt.snakemake-version="9.23.1"
