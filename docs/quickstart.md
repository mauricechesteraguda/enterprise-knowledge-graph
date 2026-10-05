# Quickstart

Requirements: Python 3.11–3.13 for the offline path, or Docker Compose for the full local
stack. No cloud account or credential is needed.

```shell
cp .env.example .env
make install
make check
make test
make coverage
```

For the Compose path:

```shell
make compose-config
docker compose up --build -d
make etl
make compose-tests
curl http://127.0.0.1:8000/health/live
docker compose down -v --remove-orphans
```

The ETL and test jobs are deliberately explicit profiles; `docker compose up` does not run
them implicitly. Local defaults are disposable and must not be reused as production secrets.
