"""Pure reconciliation logic — no AWS or Django dependencies.

Kept dependency-free so the *exact same code* runs in three places:

1. the Django worker (core/worker path) against model instances,
2. unit tests (fast, no mocking needed),
3. the Step Functions Lambda functions, where it is bundled into the
   deployment zip and works against plain JSON dicts.

Duck-typed accessor helpers let reconcile() operate on either model
instances or dicts without caring which it got.
"""

import csv
import io
import os
from decimal import Decimal


def parse_transactions_csv(text, source):
    """Parse a CSV body into a list of transaction dicts (pure, no DB)."""
    transactions = []
    for row in csv.DictReader(io.StringIO(text)):
        transactions.append(
            {
                "source": source,
                "external_id": row["external_id"].strip(),
                "amount": Decimal(row["amount"]),
                "date": row["date"].strip(),
                "description": row.get("description", "").strip(),
            }
        )
    return transactions


def source_from_filename(file_key):
    """Infer the transaction source from the uploaded file's name.

    Sample files are named like ``bank-jan2026.csv`` / ``ledger-jan2026.csv``.
    Anything that is not a ledger file is treated as a bank file.
    """
    base = os.path.basename(file_key).lower()
    return "ledger" if "ledger" in base else "bank"


def field(obj, name):
    """Read a field from a dict or from an object attribute."""
    if isinstance(obj, dict):
        return obj[name]
    return getattr(obj, name)


def reconcile(bank_transactions, ledger_transactions):
    """Match every bank transaction against the ledger by ``external_id``.

    The bank side is treated as the source of truth: a bank transaction is
    flagged if it is missing from the ledger, or if its amount differs.
    Ledger-only transactions are not flagged.

    Returns a list of ``(transaction, reason)`` tuples.
    """
    mismatches = []
    ledger_by_id = {field(t, "external_id"): t for t in ledger_transactions}
    for bank_txn in bank_transactions:
        ledger_txn = ledger_by_id.get(field(bank_txn, "external_id"))
        if not ledger_txn:
            mismatches.append((bank_txn, "missing in ledger"))
        elif Decimal(str(field(bank_txn, "amount"))) != Decimal(str(field(ledger_txn, "amount"))):
            mismatches.append((bank_txn, "amount mismatch"))
    return mismatches


def mismatch_summary(mismatches):
    """Turn ``(transaction, reason)`` pairs into JSON-friendly dicts."""
    return [
        {
            "external_id": field(t, "external_id"),
            "amount": str(field(t, "amount")),
            "reason": reason,
        }
        for t, reason in mismatches
    ]
