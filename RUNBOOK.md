# RUNBOOK — Local Run and AWS Deployment

Follow this document from top to bottom. The project uses:

```text
GitHub
+ GitHub Actions
+ five AWS Glue Jobs
+ AWS Glue Workflow
+ scheduled and conditional triggers
+ CloudFormation
```

## Architecture

```text
Daily scheduled trigger
        │
        ├── dwd_reservation_event ─┐
        │                           ├── dm_reservation_conversion
        └── dwd_paid_order ────────┘              │
                                                   ├── ads_campaign_conversion
                                                   └── ads_crm_reserved_not_paid
```

The DWD jobs run in parallel. The DM job runs only when both DWD jobs succeed. The two ADS jobs then run in parallel.

---

## Part A — Run locally

### A1. Open the project

```bash
unzip reservation-analytics-platform-enterprise.zip
cd reservation-analytics-platform-enterprise
```

### A2. Create Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### A3. Run the complete local pipeline

```bash
python -m src.run_local
pytest -q
```

Expected:

```text
1 passed
```

Local execution uses DuckDB and `sql/local/00_mock_ods.sql`. It does not require AWS.

---

## Part B — Prepare AWS

### B1. Check AWS CLI

```bash
aws --version
aws configure
aws sts get-caller-identity
```

Use a sandbox or development AWS account. The identity must be allowed to use:

```text
S3
CloudFormation
Glue
IAM
Athena
CloudWatch Logs
```

### B2. Choose a globally unique S3 bucket name

Example:

```bash
export AWS_REGION=ap-southeast-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ARTIFACT_BUCKET="reservation-analytics-${AWS_ACCOUNT_ID}-${AWS_REGION}"
```

Check:

```bash
echo "$ARTIFACT_BUCKET"
```

---

## Part C — Generate and upload artifacts

### C1. Generate mock ODS Parquet

```bash
python scripts/generate_mock_ods.py
```

Generated paths:

```text
aws/mock_data/ods/ods_reservation_event/
aws/mock_data/ods/ods_order/
aws/mock_data/dim/dim_campaign/
```

### C2. Create the bucket and upload code/data

```bash
python scripts/upload_artifacts.py \
  --bucket "$ARTIFACT_BUCKET" \
  --region "$AWS_REGION"
```

Confirm in S3:

```text
code/glue_jobs/run_single_sql_job.py
code/sql/dwd/
code/sql/dm/
code/sql/ads/
data/ods/
data/dim/
```

---

## Part D — Deploy CloudFormation

Run:

```bash
aws cloudformation deploy \
  --template-file infra/glue-workflow.yaml \
  --stack-name reservation-analytics-dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    ProjectName=reservation-analytics \
    ArtifactBucket="$ARTIFACT_BUCKET" \
    DailySchedule="cron(0 2 * * ? *)" \
  --region "$AWS_REGION"
```

This creates:

```text
5 Glue databases: ODS, DIM, DWD, DM, ADS
8 Glue Catalog tables
5 Glue Jobs
1 Glue Workflow
1 manual trigger
1 scheduled trigger
2 conditional triggers
1 Glue IAM role
```

### D1. Check the stack

```bash
aws cloudformation describe-stacks \
  --stack-name reservation-analytics-dev \
  --region "$AWS_REGION"
```

In the AWS Console:

```text
CloudFormation → Stacks → reservation-analytics-dev
AWS Glue → Workflows → reservation-analytics-workflow
AWS Glue → ETL jobs
AWS Glue → Triggers
AWS Glue → Data Catalog → Databases
```

---

## Part E — Run the workflow immediately

The daily trigger is scheduled, but you do not need to wait. The command below starts the on-demand trigger attached to the same workflow.

```bash
python scripts/run_workflow.py \
  --trigger reservation-analytics-manual-start \
  --workflow reservation-analytics-workflow \
  --region "$AWS_REGION"
```

Expected dependency order:

```text
dwd-reservation-event: SUCCEEDED
dwd-paid-order: SUCCEEDED
dm-reservation-conversion: SUCCEEDED
ads-campaign-conversion: SUCCEEDED
ads-crm-reserved-not-paid: SUCCEEDED
```

Check in the console:

```text
AWS Glue → Workflows → reservation-analytics-workflow → History
```

If a job fails:

```text
AWS Glue → ETL jobs → failed job → Runs → CloudWatch logs
```

---

## Part F — Validate with Athena

Run:

```bash
python scripts/aws_validate.py \
  --bucket "$ARTIFACT_BUCKET" \
  --region "$AWS_REGION"
```

Expected DM result:

| mid | order_flag | tag_reserved_not_paid |
|---|---:|---:|
| U001 | 1 | 0 |
| U002 | 0 | 1 |
| U003 | 0 | 1 |

The output folders are:

```text
s3://$ARTIFACT_BUCKET/curated/dwd_reservation_event/
s3://$ARTIFACT_BUCKET/curated/dwd_paid_order/
s3://$ARTIFACT_BUCKET/curated/dm_reservation_conversion/
s3://$ARTIFACT_BUCKET/curated/ads_campaign_conversion/
s3://$ARTIFACT_BUCKET/curated/ads_crm_reserved_not_paid/
```

---

## Part G — Understand the schedule

Default CloudFormation parameter:

```text
cron(0 2 * * ? *)
```

This is:

```text
02:00 UTC
10:00 Singapore time
```

To change the time, redeploy the same stack with another `DailySchedule`.

Example for 09:00 Singapore time:

```bash
aws cloudformation deploy \
  --template-file infra/glue-workflow.yaml \
  --stack-name reservation-analytics-dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    ProjectName=reservation-analytics \
    ArtifactBucket="$ARTIFACT_BUCKET" \
    DailySchedule="cron(0 1 * * ? *)" \
  --region "$AWS_REGION"
```

---

## Part H — Enable GitHub Actions deployment

### H1. Create a GitHub repository

```bash
git init
git add .
git commit -m "Initial reservation analytics platform"
git branch -M main
git remote add origin <YOUR_GITHUB_REPOSITORY>
git push -u origin main
```

### H2. Configure AWS authentication

The workflow uses GitHub OpenID Connect rather than long-lived access keys.

Create or use an AWS IAM role trusted by your GitHub repository. It needs permissions for:

```text
S3 artifact upload
CloudFormation deployment
Glue resources
IAM role creation/pass-role
```

Add this GitHub repository secret:

```text
AWS_DEPLOY_ROLE_ARN
```

Add this secret too:

```text
AWS_ARTIFACT_BUCKET
```

Value example:

```text
reservation-analytics-123456789012-ap-southeast-1
```

### H3. Run deployment

GitHub:

```text
Actions → Deploy DEV → Run workflow
```

Or push a change to:

```text
sql/**
glue_jobs/**
infra/**
config/**
```

CI runs tests first in `.github/workflows/ci.yml`. Deployment is defined in `.github/workflows/deploy-dev.yml`.

---

## Part I — Daily development workflow

```text
1. Pull latest main.
2. Create a feature branch.
3. Change one SQL model.
4. Run local tests.
5. Push branch.
6. Open Pull Request.
7. GitHub Actions runs CI.
8. Review and merge.
9. Deploy DEV workflow uploads artifacts.
10. CloudFormation updates jobs/workflow if needed.
11. Run workflow and validate Athena.
```

Example:

```bash
git checkout -b feature/add-country-dimension
# edit SQL
python -m src.run_local
pytest -q
git add .
git commit -m "Add country dimension to conversion model"
git push -u origin feature/add-country-dimension
```

---

## Part J — Add another DM table

For `dm_user_channel_profile`:

1. Add SQL:

```text
sql/dm/31_dm_user_channel_profile.sql
```

2. Add a Glue Catalog table to:

```text
infra/glue-workflow.yaml
```

3. Add a new Glue Job using `run_single_sql_job.py`.

4. Add a conditional trigger based on its upstream job.

5. Add a local execution entry in `src/run_local.py`.

6. Add a test in `tests/test_pipeline.py`.

7. Run CI and deploy through CloudFormation.

For a small extension based only on the current DM table, you may instead add it as another ADS/DM job triggered after `dm_reservation_conversion`.

---

## Part K — Clean up

Delete CloudFormation resources:

```bash
python scripts/delete_stack.py \
  --stack reservation-analytics-dev \
  --region "$AWS_REGION"
```

The S3 bucket is intentionally retained because CloudFormation does not own it.

Delete its objects and the bucket:

```bash
aws s3 rm "s3://$ARTIFACT_BUCKET" --recursive
aws s3 rb "s3://$ARTIFACT_BUCKET"
```

---

## Troubleshooting

### CloudFormation reports insufficient capabilities

Use:

```text
--capabilities CAPABILITY_NAMED_IAM
```

### Glue cannot read an input table

Check:

```text
Glue Catalog table location
S3 Parquet file exists
Glue role has s3:GetObject
database/table name matches INPUT_TABLES_JSON
```

### DM trigger does not run

Both DWD jobs must be launched as part of the same workflow run and must reach `SUCCEEDED`.

Check:

```text
Glue Workflow → Run graph
Glue Triggers → dm-after-dwd
```

### Athena table is empty

Check the relevant `curated/` folder in S3 and the table Location in Glue Catalog.

### GitHub deploy cannot assume AWS role

Check:

```text
GitHub OIDC provider exists in AWS
role trust policy matches repository owner/name and branch
AWS_DEPLOY_ROLE_ARN secret is correct
```
