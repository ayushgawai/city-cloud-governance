# city-cloud-governance

Terraform-based multi-account AWS governance and cost-optimization reference,
GovCloud style. Terraform modules are the deployable artefact; a pure-stdlib
Python CLI (`citygov`) mirrors the same policy/cost logic so it can be planned,
scored, forecast, tested and benchmarked **offline** against a 12-account
fixture tree — no AWS credentials required.

> Status: reference implementation. The Python logic is tested and benchmarked
> below; the Terraform modules have **not** been applied to a real AWS account
> (see Limitations).

## Design

```
                         AWS Organizations (GovCloud partition)
   ┌──────────────────────────────────────────────────────────────────┐
   │  SCPs · tag policies · city-permission-boundary (every role)     │
   └──────────────┬───────────────────────────────┬───────────────────┘
                  │                               │
        ┌─────────▼─────────┐           ┌─────────▼──────────┐
        │  Hub / network    │           │  Spoke accounts xN │
        │  account          │  TGW + RAM│  (fixture: 12)     │
        │ ┌───────────────┐ │◄──────────►│  prod-permits      │
        │ │ VPC + flowlogs│ │  attach    │  prod-payments ... │
        │ │ TransitGateway│ │            │  archive-records   │
        │ │ Route53 priv. │ │            └─────────┬──────────┘
        │ │ ALB (shared)  │ │                      │ inventory JSON
        │ └───────────────┘ │                      ▼
        └─────────┬─────────┘           ┌──────────────────────┐
                  │ metrics/alerts      │  citygov CLI (offline)│
        ┌─────────▼─────────┐           │  plan · apply          │
        │ Prometheus stack  │           │  score · forecast      │
        │ (EKS/Helm) +      │           │  bench                 │
        │ governance alerts │           └──────────┬─────────────┘
        └───────────────────┘                      │ mirrors
                                        ┌──────────▼─────────────┐
                                        │ policy.py · cost.py    │
                                        │ score.py (6 pillars)   │
                                        └────────────────────────┘
```

| Area | Terraform module(s) | Python mirror | What it enforces / computes |
|---|---|---|---|
| IAM boundary | `modules/iam-boundary` | `policy.evaluate_role` | Every role carries `city-permission-boundary`; wildcard admin and guarded-service wildcards denied; CloudTrail/Config/Organizations actions hard-denied; region condition `us-gov-west-1`/`us-gov-east-1` only |
| Tag policy | `modules/tag-policy` | `policy.evaluate_tags` | Required `CostCenter`, `Environment`, `Owner`, `DataClassification` (Organizations tag policy + Config `REQUIRED_TAGS` rule) |
| Network library | `modules/network-vpc`, `network-transit-gateway`, `network-route53`, `network-load-balancer` | — (inventory checks only) | Per-account VPC + flow logs, TGW hub with prod/nonprod route tables and RAM sharing, shared private DNS, ALB with encrypted access-log bucket |
| Cost | `modules/cost-controls` | `cost.rightsize`, `storage_tier`, `ols_forecast`, `mape` | Budgets (actual 80% / forecast 100% alerts) + anomaly monitor; RightSize when peak CPU <25% and mem <40%; storage tiering by age/access; OLS forecast |
| Review scorecard | `modules/well-architected` | `score.scorecard` | Six pillars (operational excellence, security, reliability, performance, cost, sustainability), 14 checks, A–F grade |
| Monitoring | `modules/monitoring-prometheus`, `monitoring/alerts.yaml` | scorecard inputs | kube-prometheus-stack on EKS; alerts on tag-compliance drop, budget burn >100%, TGW attachment down |

## Run

```bash
pip install -e .          # or skip install: export PYTHONPATH=src

citygov plan              # drift + savings over fixtures/accounts/ (exit 1 if drift)
citygov apply --dry-run   # simulated remediation; `apply` writes .citygov/state.json
citygov score             # Well-Architected scorecard per account
citygov forecast          # next-3-month OLS cost forecast per account
citygov bench             # benchmark below (also: python -m citygov.cli bench)
```

Without installing: `PYTHONPATH=src python -m citygov.cli plan` (Windows PowerShell: `$env:PYTHONPATH="src"; python -m citygov.cli plan`).

Regenerate the fixture tree (deterministic, seeded): `python tools/make_fixtures.py`

Terraform (needs AWS credentials + a GovCloud account — not run here):

```bash
cd examples/multi-account && terraform init && terraform validate && terraform plan
```

## Tests

```bash
python -m pytest tests -q
```

```
23 passed in 0.03s
```

Coverage: policy denial cases (missing boundary, wildcard admin, hard-denied
`cloudtrail:StopLogging`, guarded `iam:*`, missing/bad tags, non-GovCloud
region, plus compliant-allowed cases) and cost math (one-step downsize price
differences, RightSize busy-instance exclusion, storage-tier savings,
flat/linear/never-negative forecasts, MAPE).

## Benchmark (sanity run, scaled down honestly)

`citygov bench` over the committed 12-account fixture tree (4 accounts carry
6 planted drift findings; 12 months of synthetic cost history per account).
This is a fixture benchmark, not a production measurement:

```
benchmark: 12-account fixture tree
  governance drift: planted=6 detected=6 recall=100.0%
    prod-payments: 1 findings
    dev-sandbox: 1 findings
    shared-logging: 1 findings
    citizen-portal: 3 findings
  forecast backtest (train n-3, predict 3): mean MAPE=0.42% over 12 accounts
    prod-permits: MAPE 0.42%
    prod-payments: MAPE 0.24%
    prod-gis: MAPE 0.75%
    staging-apps: MAPE 0.19%
    dev-sandbox: MAPE 0.38%
    shared-network: MAPE 0.24%
    shared-logging: MAPE 0.53%
    security-tooling: MAPE 0.22%
    data-warehouse: MAPE 0.47%
    citizen-portal: MAPE 0.96%
    fleet-iot: MAPE 0.38%
    archive-records: MAPE 0.21%
  cost recommendations: 10 ($1099.96/mo, $13199.52/yr)
  well-architected: fleet average 69.8% min 58.3% max 75.0%
```

Related sanity outputs: `citygov plan` reports the same 6 drift findings and
`$1099.96/mo ($13199.52/yr)` across 10 recommendations; `citygov score`
fleet average is 69.8% (grades C–F on the deliberately imperfect fixtures).

The 0.42% MAPE is low **by construction**: fixture cost series are smooth
(~1.2%/month growth + small noise), so a linear model backtests well. It
validates the forecast plumbing, not real-world forecast accuracy.

## Limitations

- **Terraform not applied or validated in this environment** — no AWS/GovCloud
  account, credentials, or Terraform binary were available. Modules are
  written to current provider conventions; run `terraform init/validate/plan`
  before trusting them. The Route53 resolver rule and Well-Architected lens
  ARN are placeholders that need real values.
- **CLI is a simulator.** `plan`/`apply` evaluate exported inventory JSON and
  write a local state file; they never call AWS. A real deployment replaces
  `load_tree()` with a Config aggregator / Security Hub export.
- Prices in `cost.py` are illustrative monthly figures in one table, not live
  GovCloud pricing; the OLS forecast ignores seasonality, spikes, and
  committed-use discounts.
- Scorecard checks are booleans derived from fixture fields; real checks need
  per-service API evidence.
- Benchmark scale is 12 synthetic accounts — drift recall and MAPE say the
  logic works on known input, nothing about production estates.

## Layout

```
modules/            Terraform: iam-boundary, tag-policy, network-*, cost-controls,
                    monitoring-prometheus, well-architected (+ examples/multi-account)
src/citygov/        policy.py · cost.py · score.py · cli.py (plan/apply/score/forecast/bench)
fixtures/accounts/  12-account fixture tree (tools/make_fixtures.py, seeded)
tests/              policy denial + cost math + scorecard/fixture tests (23 tests)
monitoring/         Prometheus governance alert rules
docs/               architecture notes
```

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Ayush Gawai.
