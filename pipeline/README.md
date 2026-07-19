# Data Engineer Ownership

The data engineer owns the pipeline contract, SQL, Glue job code, business-date semantics, task order, and retry requirements.

The data engineer does not directly maintain IAM policies, EventBridge target permissions, CloudWatch logging, or the reusable Step Functions infrastructure module.
