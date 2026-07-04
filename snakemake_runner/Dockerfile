FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_CONFIG_FILE=/etc/pip.conf

WORKDIR /app

COPY pip.conf /etc/pip.conf
COPY requirements.txt /tmp/snakemake-runner-requirements.txt
RUN pip install --no-cache-dir -r /tmp/snakemake-runner-requirements.txt

CMD ["snakemake", "--help"]
