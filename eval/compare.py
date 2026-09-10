# eval/compare.py

import json
from pathlib import Path


def compare_reports(report_a: dict, report_b: dict) -> dict:
    """对比两份评测报告"""

    metrics = ["success_rate", "sql_accuracy", "result_accuracy", "avg_time"]

    comparison = {
        "report_a": report_a["timestamp"],
        "report_b": report_b["timestamp"],
        "changes": {}
    }

    for metric in metrics:
        a_val = report_a["summary"][metric]
        b_val = report_b["summary"][metric]

        if isinstance(a_val, (int, float)) and isinstance(b_val, (int, float)):
            delta = b_val - a_val
            pct = (delta / a_val * 100) if a_val != 0 else 0
            comparison["changes"][metric] = {
                "from": a_val,
                "to": b_val,
                "delta": delta,
                "pct_change": pct
            }

    return comparison