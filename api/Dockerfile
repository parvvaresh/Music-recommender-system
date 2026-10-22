# Backend: FastAPI recommendation API.
# Build from the repo root:  docker build -f api/Dockerfile -t rj-backend .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WEB_CONCURRENCY=2

WORKDIR /app

COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY api ./api

RUN useradd --create-home --uid 1000 app
USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=2)"

# uvicorn reads the worker count from $WEB_CONCURRENCY.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
