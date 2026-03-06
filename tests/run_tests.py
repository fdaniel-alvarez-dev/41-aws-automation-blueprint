#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def fail(message: str, *, output: str | None = None, code: int = 1) -> None:
    print(f"FAIL: {message}")
    if output:
        print(output.rstrip())
    raise SystemExit(code)


def require_file(path: Path, description: str) -> None:
    if not path.exists():
        fail(f"Missing {description}: {path}")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON: {path}", output=str(exc))
    return {}


def demo_mode() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    report_path = ARTIFACTS_DIR / "airflow_guardrails.json"
    guard = run([sys.executable, "tools/airflow_guardrails.py", "--format", "json", "--out", str(report_path)])
    if guard.returncode != 0:
        fail("Airflow guardrails failed (demo mode must be offline).", output=guard.stdout)

    report = load_json(report_path)
    if report.get("summary", {}).get("errors", 0) != 0:
        fail("Airflow guardrails reported errors.", output=json.dumps(report.get("findings", []), indent=2))

    dag_lint = run([sys.executable, "tools/dag_spec_lint.py"])
    if dag_lint.returncode != 0:
        fail("DAG spec lint failed.", output=dag_lint.stdout)

    demo = run([sys.executable, "pipelines/pipeline_demo.py"])
    if demo.returncode != 0:
        fail("Offline demo pipeline failed.", output=demo.stdout)

    out_path = REPO_ROOT / "data" / "processed" / "events_jsonl" / "events.jsonl"
    require_file(out_path, "offline demo output")
    if out_path.stat().st_size == 0:
        fail("Offline demo output is empty.", output=str(out_path))

    for required in ["NOTICE.md", "COMMERCIAL_LICENSE.md", "GOVERNANCE.md"]:
        require_file(REPO_ROOT / required, required)

    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8", errors="replace")
    if "it.freddy.alvarez@gmail.com" not in license_text:
        fail("LICENSE must include the commercial licensing contact email.")

    print("OK: demo-mode tests passed (offline).")


def _airflow_get(base_url: str, path: str, *, username: str | None, password: str | None, timeout_s: int = 8) -> tuple[int, str]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    headers = {}
    if username and password:
        import base64

        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"
    req = Request(url, method="GET", headers=headers)
    with urlopen(req, timeout=timeout_s) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def production_mode() -> None:
    if os.environ.get("PRODUCTION_TESTS_CONFIRM") != "1":
        fail(
            "Production-mode tests require an explicit opt-in.",
            output=(
                "Set `PRODUCTION_TESTS_CONFIRM=1` and rerun:\n"
                "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n"
            ),
            code=2,
        )

    ran_external_integration = False

    base_url = os.environ.get("AIRFLOW_BASE_URL", "").strip()
    username = os.environ.get("AIRFLOW_USERNAME", "").strip() or None
    password = os.environ.get("AIRFLOW_PASSWORD", "").strip() or None

    if base_url:
        try:
            code, body = _airflow_get(base_url, "/api/v1/health", username=username, password=password)
            if code != 200:
                raise RuntimeError(f"unexpected status: {code} body={body[:200]!r}")
        except Exception as exc:
            fail(
                "Airflow REST API health check failed.",
                output=(
                    "Verify AIRFLOW_BASE_URL is reachable and credentials (if required) are valid.\n"
                    "Example:\n"
                    "  export AIRFLOW_BASE_URL='http://localhost:8080'\n"
                    "  export AIRFLOW_USERNAME='...'\n"
                    "  export AIRFLOW_PASSWORD='...'\n"
                    "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n\n"
                    f"{type(exc).__name__}: {exc}\n"
                ),
            )

        ran_external_integration = True

    if os.environ.get("TERRAFORM_VALIDATE") == "1":
        tf = shutil.which("terraform")
        if tf is None:
            fail(
                "TERRAFORM_VALIDATE=1 requires terraform.",
                output="Install Terraform and rerun production mode, or unset TERRAFORM_VALIDATE.",
                code=2,
            )
        ran_external_integration = True
        example_dir = REPO_ROOT / "infra" / "examples" / "dev"
        init = run([tf, "init", "-backend=false"], cwd=example_dir)
        if init.returncode != 0:
            fail("terraform init failed.", output=init.stdout, code=2)
        validate = run([tf, "validate"], cwd=example_dir)
        if validate.returncode != 0:
            fail("terraform validate failed.", output=validate.stdout)

    if not ran_external_integration:
        fail(
            "No external integration checks were executed in production mode.",
            output=(
                "Enable at least one real integration:\n"
                "- Set `AIRFLOW_BASE_URL` to run an Airflow REST API health check, and/or\n"
                "- Set `TERRAFORM_VALIDATE=1` to run Terraform validate.\n\n"
                "Then rerun:\n"
                "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n"
            ),
            code=2,
        )

    print("OK: production-mode tests passed (integrations executed).")


def main() -> None:
    mode = os.environ.get("TEST_MODE", "demo").strip().lower()
    if mode not in {"demo", "production"}:
        fail("Invalid TEST_MODE. Expected 'demo' or 'production'.", code=2)

    if mode == "demo":
        demo_mode()
        return

    production_mode()


if __name__ == "__main__":
    main()
