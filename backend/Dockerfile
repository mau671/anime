# syntax=docker/dockerfile:1
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install uv from the official container image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy project metadata and source code
COPY pyproject.toml uv.lock ./
COPY app ./app
COPY main.py ./main.py
COPY scripts ./scripts
COPY README.md ./README.md

# Install dependencies into an in-project virtual environment
RUN uv sync --frozen --no-cache

ENV PATH="/app/.venv/bin:${PATH}"
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
