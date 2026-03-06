# 41-aws-reliability-security-airflow

A portfolio-grade **Airflow reliability and security** toolkit:
deterministic offline demos, operational guardrails, and production-safe validation paths.

## The top pains this repo addresses
1) Keeping orchestration dependable: predictable DAG definitions, clear validation gates, and fast failure detection.
2) Reducing operational risk: repeatable checks and guardrails instead of “run it and hope”.
3) Enforcing security and governance without blocking delivery: explicit validation modes and clean documentation.

## Quick demo (local)
```bash
make demo-offline
make test-demo
```

What you get:
- an offline demo dataset in JSONL format
- a small, reviewable DAG spec (`dags/demo_etl_dag.py`) + offline DAG validation
- deterministic guardrails report (`artifacts/airflow_guardrails.json`)
- explicit `TEST_MODE=demo|production` tests with safe production gating

## Tests (two explicit modes)

- `TEST_MODE=demo` (default): offline-only checks, deterministic artifacts
- `TEST_MODE=production`: real integrations (requires explicit opt-in + configuration)

Run production mode:

```bash
make test-production
```

Production integration options:
- Set `AIRFLOW_BASE_URL` to run Airflow REST API health checks (optionally add `AIRFLOW_USERNAME` / `AIRFLOW_PASSWORD`).
- Or set `TERRAFORM_VALIDATE=1` to validate the included Terraform example (requires `terraform`).

## Sponsorship and contact

Sponsored by:
CloudForgeLabs  
https://cloudforgelabs.ainextstudios.com/  
support@ainextstudios.com

Built by:
Freddy D. Alvarez  
https://www.linkedin.com/in/freddy-daniel-alvarez/

For job opportunities, contact:
it.freddy.alvarez@gmail.com

## License

Personal, educational, and non-commercial use is free. Commercial use requires paid permission.
See `LICENSE` and `COMMERCIAL_LICENSE.md`.
