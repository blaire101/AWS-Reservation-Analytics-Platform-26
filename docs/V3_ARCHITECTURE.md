# Version 3 Architecture — Step Functions

Version 3 changes only the orchestration layer.

## Ownership remains unchanged

```text
Upstream project
├── ODS
├── DWD
└── DIM

Reservation Analytics project
├── DM
└── ADS
```

## Runtime flow

```text
Upstream DWD + DIM ready
          ↓
     EventBridge
          ↓
   Step Functions
          ↓
DM Reservation Conversion
          ↓
       Parallel
      ↙        ↘
ADS Campaign   ADS CRM
```

## Removed from Version 2

```text
Lambda workflow starter
Glue Workflow
Glue on-demand trigger
Glue conditional trigger
```

## Added in Version 3

```text
Step Functions state machine
Step Functions execution role
EventBridge-to-Step-Functions role
Explicit Retry and Catch handling
Parallel ADS execution
```

The Glue jobs, SQL files, Glue Catalog tables, S3 locations, upstream ownership and event format remain unchanged.
