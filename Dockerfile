ARG PYTHON_IMAGE=python:3.11-slim-bookworm@sha256:528257d48c1da0dcecc2e725d1ae34498d60c965f1241e39cd6a85a8859bdf84
FROM ${PYTHON_IMAGE} AS base

# Patch the runtime OS too, not just the discarded compiler stage.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

FROM base AS builder

ARG GIT_COMMIT

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY requirements/runtime.txt /app/requirements/runtime.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && /opt/venv/bin/python -m pip install --no-cache-dir \
       -c requirements/runtime.txt ".[address]" "gunicorn>=21" \
    && /opt/venv/bin/python -m pip check \
    && /opt/venv/bin/python -m pip install --no-cache-dir \
       -c requirements/runtime.txt --target /opt/test-tools pytest==9.1.1 \
    && /opt/venv/bin/python -m pip uninstall -y pip setuptools wheel

FROM base AS runtime

ARG GIT_COMMIT

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GIT_COMMIT=$GIT_COMMIT \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

# Remove unused global packaging tools and their bundled vulnerable copies.
# Copy a clean environment instead of overlaying the base's /usr/local tree.
RUN /usr/local/bin/python -m pip uninstall -y pip setuptools wheel \
    && rm -rf /usr/local/lib/python3.11/ensurepip

COPY --from=builder /opt/venv /opt/venv
COPY towns /app/towns

RUN useradd --system --uid 10001 --user-group \
      --home-dir /home/app --create-home --shell /usr/sbin/nologin app

USER app

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import sys,urllib.request; \
url='http://127.0.0.1:5000/healthz'; \
urllib.request.urlopen(url, timeout=2).read(); \
sys.exit(0)"

CMD ["gunicorn", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "town_collection_cal.service.app:create_app()"]

# Exercise the installed production package with test tools isolated from the image.
FROM runtime AS test
COPY --from=builder /opt/test-tools /opt/test-tools
COPY tests /app/tests
ENV PYTHONPATH=/opt/test-tools
RUN python -m pytest -q -p no:cacheprovider

# The default build excludes the test tools and test fixtures.
FROM runtime AS production
