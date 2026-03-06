from __future__ import annotations

from datetime import timedelta


DAG_ID = "demo_etl_jsonl"

DAG_SPEC = {
    "dag_id": DAG_ID,
    "schedule": "0 * * * *",
    "catchup": False,
    "default_args": {
        "retries": 2,
        "retry_delay_seconds": int(timedelta(minutes=5).total_seconds()),
        "execution_timeout_seconds": int(timedelta(minutes=10).total_seconds()),
    },
    "tasks": [
        {"task_id": "extract", "kind": "python", "expects": "data/raw/events.csv"},
        {"task_id": "transform", "kind": "python", "produces": "data/processed/events_jsonl/events.jsonl"},
        {"task_id": "validate", "kind": "python", "checks": ["event_id>=1", "user_id>=1", "event_type in {signup,login,purchase}"]},
    ],
    "dependencies": [
        ["extract", "transform"],
        ["transform", "validate"],
    ],
}
