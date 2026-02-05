FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential g++ python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip==26.0.1 wheel==0.46.2 \
    && pip install --no-cache-dir ".[address]" \
    && pip install --no-cache-dir "gunicorn>=21"

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /usr/local /usr/local
COPY src /app/src
COPY towns /app/towns

RUN useradd --system --uid 10001 --user-group \
      --home-dir /home/app --create-home --shell /usr/sbin/nologin app \
    && chown -R app:app /app

USER app

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "town_collection_cal.service.app:create_app()"]
