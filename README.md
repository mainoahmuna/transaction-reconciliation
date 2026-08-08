# Financial Transaction Reconciliation Service

![CI](https://github.com/mainoahmuna/transaction-reconciliation/actions/workflows/ci.yml/badge.svg)

A Django REST API that reconciles transactions from two sources (bank and ledger), using S3, SQS, Step Functions, and SNS — all emulated locally with [LocalStack](https://docs.localstack.cloud/). No AWS account or billing required.

## Stack

- Django 5.2 + Django REST Framework
- LocalStack (s3, sqs, sns, stepfunctions) via Docker Compose
- Postgres (via Docker) or SQLite for local dev
- boto3, Celery, gunicorn

## Quick start

```bash
# 1. Start infrastructure (Postgres + LocalStack)
docker compose up -d

# 2. Verify LocalStack is healthy
curl http://localhost:4566/_localstack/health   # s3, sqs, sns, stepfunctions: available

# 3. Create the S3 bucket once
awslocal s3 mb s3://reconciliation-uploads

# 4. Set up the environment (Python 3.11+)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# 5. Run Django
python manage.py migrate
python manage.py runserver
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/upload/` | Upload a CSV (multipart field `file`) → stores in S3, creates a `ReconciliationRun` |
| GET/POST | `/api/transactions/` | Full CRUD for raw transactions |
| GET | `/api/runs/` | Read-only view of reconciliation runs |
| GET | `/api/mismatches/` | Read-only view of mismatches found |

Sample CSVs for testing live in `bruno/` (a [Bruno](https://www.usebruno.com/) collection is included).

## Tests

```bash
python manage.py test core
coverage run manage.py test core && coverage report   # must stay above 80%
```

Run the suite against Postgres (prod-like) instead of SQLite:

```bash
DB_ENGINE=django.db.backends.postgresql DB_NAME=reconciler \
DB_USER=reconciler DB_PASSWORD=localdevpassword \
DB_HOST=localhost DB_PORT=5432 python manage.py test core
```

## CI

[GitHub Actions](.github/workflows/ci.yml) runs on every push/PR to `main`:

- **lint** — ruff
- **audit** — pip-audit scans dependencies for known vulnerabilities
- **test** — Django checks + migrations check + tests with a coverage threshold
- **test-postgres** — same suite against a real Postgres service
- **docker-build** — builds the `reconciler` server image
