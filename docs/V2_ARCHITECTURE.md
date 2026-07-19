# Version 2 Architecture and Ownership

## Ownership boundary

| Resource | Owner |
|---|---|
| ODS ingestion workflow | External upstream project |
| ODS S3 data | External upstream project |
| `reservation_ods` Catalog database | External upstream project |
| `reservation_dim` Catalog database | External upstream project |
| `dim_campaign` | External upstream project |
| DWD, DM and ADS Jobs | Reservation analytics project |
| DWD, DM and ADS Catalog tables | Reservation analytics project |
| Downstream Glue Workflow | Reservation analytics project |
| EventBridge consumer rule | Reservation analytics project |

## Why the fixed daily schedule was removed

A downstream fixed schedule can begin before upstream data is complete. Version 2 therefore starts from a data-readiness contract:

```json
{
  "business_date": "2026-07-19",
  "status": "SUCCEEDED",
  "ods_ready": true,
  "dim_ready": true
}
```

## Demo versus production

### Demo

```text
generate_mock_ods.py
→ mock Parquet in the project bucket
→ demo-upstream.yaml registers ODS and DIM
→ publish_data_ready_event.py sends the event
```

### Production

```text
external upstream pipelines
→ external S3 and Glue Catalog
→ upstream quality checks
→ real Data Ready event
```

The downstream CloudFormation template is the same in both modes; only its parameters and the source of the event differ.

## Important limitation

The Lambda passes `business_date` as a Glue Workflow run property. The current generic runner may still read every source record unless it is extended to retrieve the workflow run property and filter the relevant source partition. The mock dataset is small and unpartitioned, so the demo can run without that extension.
