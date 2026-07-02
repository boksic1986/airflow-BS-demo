FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PIP_CONFIG_FILE=/etc/pip.conf \
    PYTHONPATH=/app

WORKDIR /app

COPY pip.conf /etc/pip.conf
RUN python -m venv "$VIRTUAL_ENV"

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY tests ./tests

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
