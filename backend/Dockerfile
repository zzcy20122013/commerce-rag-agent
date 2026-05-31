FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip \
    && python -m pip install \
        "chromadb>=0.5.0" \
        "fastapi>=0.115.0" \
        "httpx>=0.27.0" \
        "langgraph>=0.2.0" \
        "pillow>=12.0.0" \
        "pydantic>=2.8.0" \
        "python-dotenv>=1.0.1" \
        "python-multipart>=0.0.9" \
        "sqlalchemy>=2.0.0" \
        "uvicorn[standard]>=0.30.0"

COPY app ./app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
