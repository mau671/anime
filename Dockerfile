FROM ghcr.io/astral-sh/uv:python3.11-bookworm

WORKDIR /app

COPY pyproject.toml README.md ./
RUN uv sync --no-dev

COPY . .

ENV PYTHONPATH=/app/src

CMD ["uv", "run", "python", "-m", "anime_service", "run-service"]
