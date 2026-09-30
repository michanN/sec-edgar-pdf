FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.10.2 /uv /usr/local/bin/uv

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
COPY src/ ./src/
RUN uv sync --locked --no-editable --no-cache \
    && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY tests/ ./tests/

ENTRYPOINT ["sec-pdf"]
