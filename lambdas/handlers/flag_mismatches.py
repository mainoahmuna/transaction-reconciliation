"""State 3: FlagMismatches — turn stored mismatches into a readable report.

Input:  output of MatchTransactions, i.e. {"run_id": 1, "mismatches_key": ..., "mismatch_count": 4}
Output: {"run_id": 1, "mismatch_count": 4, "mismatches": [...], "summary": [...]}
"""

import common


def handler(event, context):
    mismatches = common.get_json(event["mismatches_key"])
    lines = [f"{m['external_id']}: {m['reason']} (bank amount {m['amount']})" for m in mismatches]

    return {
        "run_id": event["run_id"],
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "summary": lines,
    }
