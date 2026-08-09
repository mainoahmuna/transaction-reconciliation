"""State 1: ParseFile — read both CSVs from S3 and store the parsed rows.

Input:  {"run_id": 1, "bank_file_key": "...", "ledger_file_key": "..."}
Output: {"run_id": 1, "parsed_key": "parsed/1.json", "bank_count": 10, "ledger_count": 10}
"""

import common
import reconcile


def handler(event, context):
    run_id = event["run_id"]
    bank = reconcile.parse_transactions_csv(common.get_object(event["bank_file_key"]), "bank")
    ledger = reconcile.parse_transactions_csv(common.get_object(event["ledger_file_key"]), "ledger")

    parsed_key = f"parsed/{run_id}.json"
    common.put_json(parsed_key, {"bank": bank, "ledger": ledger})

    return {
        "run_id": run_id,
        "parsed_key": parsed_key,
        "bank_count": len(bank),
        "ledger_count": len(ledger),
    }
