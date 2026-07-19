# Version 2 Demo Runbook

This guide lets you simulate an enterprise-style dependency while keeping the repository independently runnable.

## Architecture

```text
Demo upstream stack
├── reservation_ods.ods_reservation_event
├── reservation_ods.ods_order
└── reservation_dim.dim_campaign
             │
             │ simulated Data Ready event
             ▼
EventBridge rule
             ▼
Lambda workflow starter
             ▼
Reservation analytics workflow
├── DWD Reservation ─┐
├── DWD Paid Order ──┴── DM Conversion
│                              ├── ADS Campaign
│                              └── ADS CRM
```

In production, the demo upstream stack is not deployed. Another team owns ODS, DIM, the upstream S3 paths and the data-ready event.

---

## 0. Apply the package

From the repository root, copy the extracted package over the project:

```bash
cp -R reservation-analytics-v2-overlay/* .
```

Review:

```bash
git status
git diff -- infra/glue-workflow.yaml
```

The package intentionally replaces:

```text
infra/glue-workflow.yaml
scripts/upload_artifacts.py
```

It adds:

```text
infra/demo-upstream.yaml
scripts/publish_data_ready_event.py
scripts/check_v2_workflow.py
examples/upstream-data-ready-event.json
docs/V2_DEMO_RUNBOOK.md
docs/V2_ARCHITECTURE.md
README_V2_SECTION.md
```

---

## 1. Create the Version 2 branch

```bash
git switch -c feature/v2-upstream-dependency
```

---

## 2. Prepare the environment

```bash
source .venv/bin/activate

export AWS_REGION=ap-southeast-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ARTIFACT_BUCKET="reservation-analytics-${AWS_ACCOUNT_ID}-${AWS_REGION}"
export UPSTREAM_DATA_BUCKET="$ARTIFACT_BUCKET"
```

For the demo, one S3 bucket plays two logical roles:

```text
ARTIFACT_BUCKET
= this project's code and curated output

UPSTREAM_DATA_BUCKET
= mock ODS and DIM input
```

Production can use different buckets.

Confirm:

```bash
aws sts get-caller-identity
echo "$ARTIFACT_BUCKET"
```

---

## 3. Generate mock upstream data

Use the existing generator:

```bash
python scripts/generate_mock_ods.py
```

Expected local paths:

```text
aws/mock_data/ods/ods_reservation_event/
aws/mock_data/ods/ods_order/
aws/mock_data/dim/dim_campaign/
```

This simulates files produced by another team's upstream workflow.

---

## 4. Upload code and demo upstream data

```bash
python scripts/upload_artifacts.py \
  --bucket "$ARTIFACT_BUCKET" \
  --region "$AWS_REGION" \
  --include-mock-data
```

Expected S3 paths:

```text
s3://$ARTIFACT_BUCKET/code/glue_jobs/
s3://$ARTIFACT_BUCKET/code/sql/
s3://$ARTIFACT_BUCKET/data/ods/
s3://$ARTIFACT_BUCKET/data/dim/
```

Without `--include-mock-data`, the script uploads only this project's code and configuration. That is the production-style behavior.

---

## 5. Deploy the demo upstream stack

```bash
aws cloudformation deploy \
  --template-file infra/demo-upstream.yaml \
  --stack-name reservation-analytics-demo-upstream \
  --parameter-overrides \
    ProjectName=reservation-analytics \
    UpstreamDataBucket="$UPSTREAM_DATA_BUCKET" \
  --region "$AWS_REGION"
```

Confirm:

```bash
aws cloudformation describe-stacks \
  --stack-name reservation-analytics-demo-upstream \
  --query "Stacks[0].StackStatus" \
  --output text \
  --region "$AWS_REGION"
```

Expected:

```text
CREATE_COMPLETE
```

This stack owns only the demo ODS and DIM Catalog resources.

---

## 6. Remove or update the Version 1 downstream stack

The Version 1 stack owns ODS and DIM resources. The Version 2 demo upstream stack cannot create resources with identical names while Version 1 still owns them.

Because Version 1 is already preserved by Git tag `v1.0.0`, delete the old stack before deploying Version 2:

```bash
aws cloudformation delete-stack \
  --stack-name reservation-analytics-dev \
  --region "$AWS_REGION"

aws cloudformation wait stack-delete-complete \
  --stack-name reservation-analytics-dev \
  --region "$AWS_REGION"
```

The S3 bucket remains because it was created outside the stack.

Deploy the demo upstream stack after the Version 1 stack has been deleted if the first attempt failed because of duplicate databases.

---

## 7. Deploy the Version 2 analytics stack

```bash
aws cloudformation deploy \
  --template-file infra/glue-workflow.yaml \
  --stack-name reservation-analytics-v2-dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    ProjectName=reservation-analytics \
    ArtifactBucket="$ARTIFACT_BUCKET" \
    UpstreamDataBucket="$UPSTREAM_DATA_BUCKET" \
    UpstreamOdsDatabase=reservation_ods \
    UpstreamDimDatabase=reservation_dim \
    OdsReservationTableName=ods_reservation_event \
    OdsOrderTableName=ods_order \
    DimCampaignTableName=dim_campaign \
    UpstreamEventSource=data-platform.upstream \
    UpstreamEventDetailType="Reservation Source Data Ready" \
  --region "$AWS_REGION"
```

Confirm:

```bash
aws cloudformation describe-stacks \
  --stack-name reservation-analytics-v2-dev \
  --query "Stacks[0].StackStatus" \
  --output text \
  --region "$AWS_REGION"
```

Expected:

```text
CREATE_COMPLETE
```

---

## 8. Confirm the resources

### External upstream tables

```bash
aws glue get-table \
  --database-name reservation_ods \
  --name ods_reservation_event \
  --region "$AWS_REGION"

aws glue get-table \
  --database-name reservation_dim \
  --name dim_campaign \
  --region "$AWS_REGION"
```

### Downstream workflow

```bash
aws glue get-workflow \
  --name reservation-analytics-workflow \
  --include-graph \
  --region "$AWS_REGION"
```

### EventBridge rule

```bash
aws events describe-rule \
  --name reservation-analytics-upstream-data-ready \
  --region "$AWS_REGION"
```

### Lambda

```bash
aws lambda get-function \
  --function-name reservation-analytics-workflow-starter \
  --region "$AWS_REGION"
```

---

## 9. Simulate the upstream completion event

```bash
python scripts/publish_data_ready_event.py \
  --business-date 2026-07-19 \
  --region "$AWS_REGION"
```

This simulates:

```text
Upstream ODS complete
+ upstream DIM complete
+ data-quality checks passed
```

EventBridge invokes Lambda, and Lambda calls `StartWorkflowRun`.

---

## 10. Check the workflow

Wait about 10–30 seconds, then:

```bash
python scripts/check_v2_workflow.py \
  --workflow reservation-analytics-workflow \
  --region "$AWS_REGION"
```

Or use the console:

```text
AWS Glue
→ Workflows
→ reservation-analytics-workflow
→ Run history
```

Expected dependency order:

```text
dwd-reservation-event ─┐
dwd-paid-order ────────┴── dm-reservation-conversion
                              ├── ads-campaign-conversion
                              └── ads-crm-reserved-not-paid
```

---

## 11. Validate with Athena

Use the existing validation script:

```bash
python scripts/aws_validate.py \
  --bucket "$ARTIFACT_BUCKET" \
  --region "$AWS_REGION"
```

You can also query:

```sql
SELECT *
FROM reservation_dm.dm_reservation_conversion
ORDER BY mid;
```

```sql
SELECT *
FROM reservation_ads.ads_campaign_conversion;
```

```sql
SELECT *
FROM reservation_ads.ads_crm_reserved_not_paid;
```

---

## 12. Stop automatic cost

Version 2 has no daily scheduled trigger. It runs only when the matching event is published or when the workflow is started manually.

Check recent runs:

```bash
aws glue get-workflow-runs \
  --name reservation-analytics-workflow \
  --max-results 5 \
  --region "$AWS_REGION"
```

Glue databases, tables, workflow definitions, triggers, IAM roles and EventBridge rules do not create ongoing Glue Spark compute charges. S3 and logs may create very small storage charges.

---

## 13. Clean up

Delete downstream:

```bash
aws cloudformation delete-stack \
  --stack-name reservation-analytics-v2-dev \
  --region "$AWS_REGION"

aws cloudformation wait stack-delete-complete \
  --stack-name reservation-analytics-v2-dev \
  --region "$AWS_REGION"
```

Delete demo upstream:

```bash
aws cloudformation delete-stack \
  --stack-name reservation-analytics-demo-upstream \
  --region "$AWS_REGION"

aws cloudformation wait stack-delete-complete \
  --stack-name reservation-analytics-demo-upstream \
  --region "$AWS_REGION"
```

Optional S3 cleanup:

```bash
aws s3 rm "s3://$ARTIFACT_BUCKET" --recursive
aws s3 rb "s3://$ARTIFACT_BUCKET"
```

---

## 14. Production differences

Production does not deploy `infra/demo-upstream.yaml`.

Instead:

1. The upstream team owns ODS and DIM Catalog tables.
2. The upstream team writes S3 partitions.
3. It validates completeness and data quality.
4. It publishes the same Data Ready event.
5. This repository starts from DWD and owns DWD, DM and ADS.

For production-grade reliability, add idempotency keyed by `business_date`, preferably using DynamoDB, because EventBridge uses at-least-once delivery.
