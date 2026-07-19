# Version 2 Demo Runbook

## 1. Prepare environment

```bash
export AWS_REGION=ap-southeast-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ARTIFACT_BUCKET="reservation-analytics-${AWS_ACCOUNT_ID}-${AWS_REGION}"
```

## 2. Generate mock ODS and DIM data

```bash
python scripts/generate_mock_ods.py
```

## 3. Upload code and mock data

```bash
python scripts/upload_artifacts.py   --bucket "$ARTIFACT_BUCKET"   --region "$AWS_REGION"   --include-mock-data
```

## 4. Delete the old Version 1 AWS stack

The Version 1 stack owns ODS, DWD and DIM resources with the same names.

```bash
aws cloudformation delete-stack   --stack-name reservation-analytics-dev   --region "$AWS_REGION"

aws cloudformation wait stack-delete-complete   --stack-name reservation-analytics-dev   --region "$AWS_REGION"
```

## 5. Deploy the demo upstream stack

```bash
aws cloudformation deploy   --template-file infra/demo-upstream.yaml   --stack-name reservation-analytics-demo-upstream   --capabilities CAPABILITY_NAMED_IAM   --parameter-overrides     ProjectName=reservation-analytics     ArtifactBucket="$ARTIFACT_BUCKET"   --region "$AWS_REGION"
```

## 6. Run the upstream DWD workflow

```bash
aws glue start-trigger   --name reservation-analytics-upstream-on-demand-start   --region "$AWS_REGION"
```

Check:

```bash
aws glue get-workflow-runs   --name reservation-analytics-upstream-workflow   --max-results 1   --region "$AWS_REGION"
```

Wait until both DWD jobs succeed.

## 7. Deploy the downstream DM/ADS stack

```bash
aws cloudformation deploy   --template-file infra/glue-workflow.yaml   --stack-name reservation-analytics-v2-dev   --capabilities CAPABILITY_NAMED_IAM   --parameter-overrides     ProjectName=reservation-analytics     ArtifactBucket="$ARTIFACT_BUCKET"     UpstreamDataBucket="$ARTIFACT_BUCKET"     UpstreamDwdDatabase=reservation_dwd     UpstreamDimDatabase=reservation_dim     DwdReservationTableName=dwd_reservation_event     DwdPaidOrderTableName=dwd_paid_order     DimCampaignTableName=dim_campaign     UpstreamEventSource=data-platform.upstream     UpstreamEventDetailType="Reservation DWD Data Ready"   --region "$AWS_REGION"
```

## 8. Publish the DWD ready event

```bash
python scripts/publish_data_ready_event.py   --business-date 2026-07-19   --region "$AWS_REGION"
```

## 9. Check the downstream workflow

```bash
aws glue get-workflow-runs   --name reservation-analytics-workflow   --max-results 1   --region "$AWS_REGION"
```

Expected:

```text
DM Reservation Conversion
├── ADS Campaign Conversion
└── ADS CRM Reserved Not Paid
```

## 10. Validate with Athena

```sql
SELECT *
FROM reservation_dm.dm_reservation_conversion;
```

```sql
SELECT *
FROM reservation_ads.ads_campaign_conversion;
```

```sql
SELECT *
FROM reservation_ads.ads_crm_reserved_not_paid;
```
