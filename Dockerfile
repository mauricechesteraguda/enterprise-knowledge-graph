# type-10052026-Maurice: Build a reproducible non-root API/ETL image.
FROM python:3.11.11-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
COPY data ./data
COPY mappings ./mappings
COPY ontology ./ontology
COPY shapes ./shapes
COPY queries ./queries
RUN python -m pip install --upgrade pip==25.0.1 && python -m pip wheel --wheel-dir /wheels .

FROM python:3.11.11-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
WORKDIR /app
RUN addgroup --system kg && adduser --system --ingroup kg kg
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels
COPY src ./src
COPY data ./data
COPY mappings ./mappings
COPY ontology ./ontology
COPY shapes ./shapes
COPY queries ./queries
COPY docs ./docs
COPY static ./static
RUN mkdir -p /app/artifacts && chown -R kg:kg /app
USER kg
EXPOSE 8000
CMD ["uvicorn", "kg.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS tests
# type-10052026-Maurice: Keep test tooling out of the production runtime image.
RUN python -m pip install --no-cache-dir httpx==0.28.1 pytest==8.3.4 pytest-cov==6.0.0
COPY tests ./tests
CMD ["python", "-m", "pytest", "--cov=kg", "--cov-branch", "--cov-report=term-missing", "--cov-fail-under=85", "--maxfail=1"]
