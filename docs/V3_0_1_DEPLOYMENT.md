# Version 3.0.1 Deployment

Install PyYAML:

```bash
pip install pyyaml
```

Deploy through the platform interface:

```bash
python platform/scripts/deploy_pipeline.py   --pipeline pipeline/reservation_pipeline.yaml   --stack-name reservation-analytics-orchestration   --region ap-southeast-1   --dm-job reservation-analytics-dm-reservation-conversion   --ads-campaign-job reservation-analytics-ads-campaign-conversion   --ads-crm-job reservation-analytics-ads-crm-reserved-not-paid
```

In a mature organization, `platform/` would normally live in a separate shared repository or package.
