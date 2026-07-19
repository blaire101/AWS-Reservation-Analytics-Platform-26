# Version 3.0.1 — Decoupled Orchestration Ownership

```text
Data Engineer
→ pipeline/reservation_pipeline.yaml
        ↓ stable contract
Platform / SRE
→ reusable CloudFormation module
        ↓
EventBridge → Step Functions → Glue Jobs
```

The data engineer owns business dependencies, task order, SQL, Glue code, business-date handling and retry requirements.

The platform/SRE team owns IAM, EventBridge permissions, Step Functions implementation, CloudWatch logging, security standards and deployment tooling.

The two teams collaborate through the pipeline contract instead of editing the same large YAML file.
