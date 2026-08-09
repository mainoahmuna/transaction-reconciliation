"""State 2: MatchTransactions — run reconcile() and store the mismatches.

Input:  output of ParseFile, i.e. {"run_id": 1, "parsed_key": "parsed/1.json", ...}
Output: {"run_id": 1, "mismatches_key": "mismatches/1.json", "mismatch_count": 4}
"""

import common
import reconcile


def handler(event, context):
    parsed = common.get_json(event["parsed_key"])
    mismatches = reconcile.reconcile(parsed["bank"], parsed["ledger"])
    summary = reconcile.mismatch_summary(mismatches)

    mismatches_key = f"mismatches/{event['run_id']}.json"
    common.put_json(mismatches_key, summary)

    return {
        "run_id": event["run_id"],
        "mismatches_key": mismatches_key,
        "mismatch_count": len(summary),
    }
