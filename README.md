# Reservation Analytics Platform


# Version 1 - This standalone implementation manages the complete ODS, DIM, DWD, DM, and ADS pipeline within a single AWS Glue Workflow

A compact, deployable AWS data-engineering project demonstrating:

```text
ODS → DWD + DIM → DM → ADS
```

It uses:

- SQL developed locally in PyCharm or another IDE;
- GitHub as the source of truth;
- GitHub Actions for CI and DEV deployment;
- five independent AWS Glue Jobs;
- AWS Glue Workflow;
- scheduled and conditional triggers;
- CloudFormation for infrastructure;
- Athena for validation.

![Architecture](docs/architecture.svg)

## Start here

Follow the complete step-by-step guide:

```text
RUNBOOK.md
```

The local-only explanation is in:

```text
ONE_HOUR_GUIDE.md
```

## Workflow

```text
Daily Trigger
    ├── DWD Reservation ─┐
    └── DWD Paid Order ──┴── DM Reservation Conversion
                                  ├── ADS Campaign Conversion
                                  └── ADS CRM Audience
```

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m src.run_local
pytest -q
```

## AWS deployment

```bash
python scripts/generate_mock_ods.py

python scripts/upload_artifacts.py \
  --bucket "$ARTIFACT_BUCKET" \
  --region ap-southeast-1

aws cloudformation deploy \
  --template-file infra/glue-workflow.yaml \
  --stack-name reservation-analytics-dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    ProjectName=reservation-analytics \
    ArtifactBucket="$ARTIFACT_BUCKET" \
    DailySchedule="cron(0 2 * * ? *)" \
  --region ap-southeast-1

python scripts/run_workflow.py \
  --trigger reservation-analytics-manual-start \
  --workflow reservation-analytics-workflow \
  --region ap-southeast-1
```

## Repository structure

```text
sql/                         SQL models
glue_jobs/                   generic Glue Spark SQL runner
infra/glue-workflow.yaml     CloudFormation
.github/workflows/           CI and DEV deployment
scripts/                     upload, run, validate and cleanup
tests/                       local tests
RUNBOOK.md                   complete deployment guide
docs/                        architecture and interview notes
```

## Data layers

| Layer | Purpose | Tables |
|---|---|---|
| ODS | Source-aligned input | `ods_reservation_event`, `ods_order` |
| DWD | Clean atomic facts | `dwd_reservation_event`, `dwd_paid_order` |
| DIM | Shared dimensions | `dim_campaign` |
| DM | Subject-level business model | `dm_reservation_conversion` |
| ADS | Application outputs | campaign metrics and CRM audience |

## Public repository safety

All data and names are synthetic and generic. The repository contains no employer production code or company-specific references.

# Version 2 — Upstream-dependent architecture

> Version 2 treats ODS and DIM as externally managed upstream data contracts. This repository owns only DWD, DM and ADS and starts after receiving an upstream Data Ready event.

> docs/V2_DEMO_RUNBOOK.md

```text
External ODS/DIM
→ EventBridge Data Ready event
→ Lambda
→ Glue Workflow
→ DWD → DM → ADS
```

For a fully runnable simulation, see:

```text
docs/V2_DEMO_RUNBOOK.md
```

The demo creates external-looking ODS and DIM resources through a separate stack:

```text
infra/demo-upstream.yaml
```

The production-style downstream stack is:

```text
infra/glue-workflow.yaml
```
