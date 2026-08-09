"""State 4: Complete — emit the final workflow result.

Input:  output of FlagMismatches
Output: {"run_id": 1, "status": "SUCCEEDED", "mismatch_count": 4}
"""


def handler(event, context):
    return {
        "run_id": event["run_id"],
        "status": "SUCCEEDED",
        "mismatch_count": event.get("mismatch_count", 0),
    }
