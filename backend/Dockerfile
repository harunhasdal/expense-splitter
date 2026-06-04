# syntax=docker/dockerfile:1
FROM python:3.12-slim@sha256:a7cbdbb380480e5f49d2d8a3e3a6b92cb97e9a11da2b8b5d9e5d6f7c6b0e3421 AS builder

WORKDIR /app
RUN pip install uv==0.2.33
COPY pyproject.toml .
RUN uv sync --no-dev --frozen

FROM python:3.12-slim@sha256:a7cbdbb380480e5f49d2d8a3e3a6b92cb97e9a11da2b8b5d9e5d6f7c6b0e3421 AS runtime

WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /app/.venv /app/.venv
COPY . .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER app

EXPOSE 8000

CMD ["gunicorn", "main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "30", \
     "--graceful-timeout", "10"]
