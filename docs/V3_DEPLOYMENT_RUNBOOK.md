# Version 3 Deployment and Demo Runbook

Version 3 reuses the existing upstream demo stack and the same DWD-ready event.

## 1. Start from the current repository

```bash
cd ~/ghome/github/AWS-Reservation-Analytics-Platform-26
git switch main
git pull origin main
git switch -c feature/v3-step-functions
```

## 2. Copy the Version 3 overlay

```bash
cp -R reservation-analytics-v3-step-functions/*   ~/ghome/github/AWS-Reservation-Analytics-Platform-26/
```

Append the README section:

```bash
cat README_V3_SECTION.md >> README.md
rm README_V3_SECTION.md
```

## 3. Validate the template

```bash
aws cloudformation validate-template   --template-body file://infra/glue-workflow.yaml   --region "$AWS_REGION"
```

## 4. Update the existing downstream stack

Use the same stack name that currently contains Version 2:

```bash
aws cloudformation deploy   --template-file infra/glue-workflow.yaml   --stack-name reservation-analytics-v2-dev   --capabilities CAPABILITY_NAMED_IAM   --parameter-overrides     ProjectName=reservation-analytics     ArtifactBucket="$ARTIFACT_BUCKET"     UpstreamDataBucket="$ARTIFACT_BUCKET"     UpstreamDwdDatabase=reservation_dwd     UpstreamDimDatabase=reservation_dim     DwdReservationTableName=dwd_reservation_event     DwdPaidOrderTableName=dwd_paid_order     DimCampaignTableName=dim_campaign     UpstreamEventSource=data-platform.upstream     UpstreamEventDetailType="Reservation DWD Data Ready"   --region "$AWS_REGION"
```

CloudFormation will remove the Version 2 Lambda and Glue Workflow resources and create the Step Functions resources.

## 5. Publish the unchanged upstream event

```bash
python scripts/publish_data_ready_event.py   --business-date 2026-07-19   --region "$AWS_REGION"
```

## 6. Find the state machine ARN

```bash
export STATE_MACHINE_ARN=$(aws cloudformation describe-stacks   --stack-name reservation-analytics-v2-dev   --query "Stacks[0].Outputs[?OutputKey=='StateMachineArn'].OutputValue"   --output text   --region "$AWS_REGION")
```

## 7. Check the latest execution

```bash
python scripts/check_v3_execution.py   --state-machine-arn "$STATE_MACHINE_ARN"   --region "$AWS_REGION"
```

You can also use:

```bash
aws stepfunctions list-executions   --state-machine-arn "$STATE_MACHINE_ARN"   --max-results 1   --region "$AWS_REGION"
```

## Expected execution graph

```text
Run DM Conversion
        ↓
Run ADS Jobs
├── Run ADS Campaign
└── Run ADS CRM
        ↓
Workflow Succeeded
```

## Notes

- `business_date` is passed to each Glue job as `--BUSINESS_DATE`.
- The existing SQL and runner remain unchanged. The argument is available for later partition filtering.
- Each Glue task retries up to two times with exponential backoff.
- Failure of either ADS branch causes the Parallel state to fail.
