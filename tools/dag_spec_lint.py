#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def validate_spec(path: Path) -> dict:
    mod = load_module(path)
    dag_id = getattr(mod, "DAG_ID", "")
    spec = getattr(mod, "DAG_SPEC", None)

    if not isinstance(dag_id, str) or not dag_id.strip():
        fail(f"{path}: DAG_ID must be a non-empty string")
    if not isinstance(spec, dict):
        fail(f"{path}: DAG_SPEC must be a dict")

    if spec.get("dag_id") != dag_id:
        fail(f"{path}: DAG_SPEC['dag_id'] must match DAG_ID")

    for k in ["schedule", "catchup", "default_args", "tasks", "dependencies"]:
        if k not in spec:
            fail(f"{path}: DAG_SPEC missing key: {k}")

    if not isinstance(spec["tasks"], list) or not spec["tasks"]:
        fail(f"{path}: DAG_SPEC['tasks'] must be a non-empty list")

    tasks = {}
    for t in spec["tasks"]:
        if not isinstance(t, dict):
            fail(f"{path}: task entries must be dicts")
        task_id = t.get("task_id", "")
        if not isinstance(task_id, str) or not task_id:
            fail(f"{path}: task_id must be a non-empty string")
        if task_id in tasks:
            fail(f"{path}: duplicate task_id: {task_id}")
        tasks[task_id] = t

    if not isinstance(spec["dependencies"], list):
        fail(f"{path}: DAG_SPEC['dependencies'] must be a list")
    for dep in spec["dependencies"]:
        if not (isinstance(dep, list) and len(dep) == 2 and all(isinstance(x, str) for x in dep)):
            fail(f"{path}: dependency entries must be [upstream, downstream] string pairs")
        up, down = dep
        if up not in tasks or down not in tasks:
            fail(f"{path}: dependency references unknown task: {dep}")

    return {"dag_id": dag_id, "task_count": len(tasks), "dependency_count": len(spec["dependencies"])}


def main() -> None:
    dags_dir = REPO_ROOT / "dags"
    dag_files = sorted(p for p in dags_dir.glob("*.py") if p.is_file())
    if not dag_files:
        fail("No DAG spec files found in dags/")

    results = [validate_spec(p) for p in dag_files]
    out = {"count": len(results), "dags": results}
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
