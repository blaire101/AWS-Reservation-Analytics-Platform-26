# Version 2 Architecture

## Ownership

```text
Upstream project
├── ODS
├── DWD
└── DIM

Reservation Analytics project
├── DM
└── ADS
```

## Runtime

```text
Upstream ODS
→ Upstream DWD
→ DWD + DIM Ready Event
→ EventBridge
→ Lambda
→ Downstream Glue Workflow
→ DM
→ ADS Campaign + ADS CRM
```

## Tables owned by this repository

```text
reservation_dm.dm_reservation_conversion
reservation_ads.ads_campaign_conversion
reservation_ads.ads_crm_reserved_not_paid
```

`infra/demo-upstream.yaml` exists only for personal AWS simulation.
