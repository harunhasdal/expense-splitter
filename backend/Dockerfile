# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

WORKDIR /app
RUN pip install uv
# Build the venv against the base image's system Python (not a uv-managed
# download): the runtime stage copies only /app/.venv, so the venv's python
# symlink must point at an interpreter that also exists there (/usr/local/bin).
ENV UV_PYTHON_PREFERENCE=only-system
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

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

# Dev stage: stays as root, has uv, runs with hot-reload
FROM python:3.12-slim AS dev

WORKDIR /app
RUN pip install uv
ENV UV_PYTHON_PREFERENCE=only-system
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "alembic -c migrations/alembic.ini upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"]
