# Financial Transaction Reconciliation Service

![CI](https://github.com/mainoahmuna/transaction-reconciliation/actions/workflows/ci.yml/badge.svg)

A Django REST API that reconciles transactions from two sources (bank and ledger), using S3, SQS, Step Functions, and SNS — all emulated locally with [LocalStack](https://docs.localstack.cloud/). No AWS account or billing required.

## Stack

- Django 5.2 + Django REST Framework
- LocalStack (s3, sqs, sns, stepfunctions, lambda) via Docker Compose
- Postgres (via Docker) or SQLite for local dev
- boto3, Celery, gunicorn

## Quick start

```bash
# 1. Start infrastructure (Postgres + LocalStack)
docker compose up -d

# 2. Verify LocalStack is healthy
curl http://localhost:4566/_localstack/health   # s3, sqs, sns, stepfunctions: available

# 3. Create the S3 bucket and SQS queue once
awslocal s3 mb s3://reconciliation-uploads
awslocal sqs create-queue --queue-name reconciliation-queue

# 4. Set up the environment (Python 3.11+)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# 5. Run Django
python manage.py migrate
python manage.py runserver

# 6. In a second terminal, run the worker that consumes the queue
python worker.py
```

The upload endpoint no longer does work synchronously: it stores the file in S3,
creates a `pending` `ReconciliationRun`, and pushes a message onto
`reconciliation-queue`. The standalone `worker.py` polls that queue in the
classic SQS loop (`receive_message` → process → `delete_message`), then runs the
real matching logic from `core/reconcile.py` (pure Python, no AWS): it downloads
the CSV from S3, infers the source from the file name (`bank-*` / `ledger-*`),
persists the rows as `Transaction`s, matches bank against ledger by
`external_id`, and writes `Mismatch` rows before marking the run `complete`.
If the worker crashes, the message stays in the queue (invisible for the 30s
visibility timeout) and gets retried.

Demo order matters: upload `ledger-jan2026.csv` first (it seeds the ledger
transactions), then `bank-jan2026.csv` — the second run flags 4 mismatches
(REF-1007/1008 amount mismatches, REF-1009/1010 missing in ledger).

## Step Functions workflow

The same matching logic is also wrapped in a Step Functions state machine
(`state_machine.json`) with four discrete, independently observable states —
`ParseFile → MatchTransactions → FlagMismatches → Complete`. Each state is a
real Lambda on LocalStack that shares `core/reconcile.py` (bundled into the
deployment zip) and hands data between steps via S3 objects:

- `ParseFile` reads both CSVs from S3 → writes `parsed/{run_id}.json`
- `MatchTransactions` runs `reconcile()` → writes `mismatches/{run_id}.json`
- `FlagMismatches` builds a human-readable report
- `Complete` emits the final `{status: SUCCEEDED, mismatch_count}`

LocalStack must have Docker access to run Lambda containers (the compose file
already mounts `/var/run/docker.sock`). Deploy and run:

```bash
# 1. deploy the four Lambdas + state machine (LocalStack must be running)
.venv/bin/python lambdas/package.py

# 2. upload the demo CSVs to S3 (done once)
awslocal s3 cp bruno/bank-jan2026.csv   s3://reconciliation-uploads/uploads/demo/bank-jan2026.csv
awslocal s3 cp bruno/ledger-jan2026.csv s3://reconciliation-uploads/uploads/demo/ledger-jan2026.csv

# 3. start an execution
awslocal stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:000000000000:stateMachine:ReconciliationWorkflow \
  --input '{"run_id": 1, "bank_file_key": "uploads/demo/bank-jan2026.csv", "ledger_file_key": "uploads/demo/ledger-jan2026.csv"}'

# 4. watch it walk through the states to SUCCEEDED
awslocal stepfunctions describe-execution \
  --execution-arn <execution-arn>
```

The step-by-step benefit over one big function: each state's success/failure is
visible in the execution history and can be retried independently, instead of
the whole job failing as an opaque blob.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/upload/` | Upload a CSV (multipart field `file`) → stores in S3, creates a `pending` `ReconciliationRun`, and enqueues it on SQS (processed async by `worker.py`) |
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
