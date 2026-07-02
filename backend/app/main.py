from fastapi import FastAPI

app = FastAPI(title="airflow-demo backend")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
