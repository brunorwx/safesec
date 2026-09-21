FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml uv.lock README.md PLAN.md ./
COPY camera ./camera
COPY detection ./detection
COPY storage ./storage
COPY alerts ./alerts
COPY gateway ./gateway
COPY apps ./apps

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --extra ml

EXPOSE 8765

ENTRYPOINT ["uv", "run", "--no-dev", "safesec-local"]
