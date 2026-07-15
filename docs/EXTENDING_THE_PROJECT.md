# Extending the Project

This version uses one Glue Job per output model.

## Add a new DM table

For `dm_user_channel_profile`:

1. Create `sql/dm/31_dm_user_channel_profile.sql`.
2. Add its output table to `infra/glue-workflow.yaml`.
3. Add a Glue Job that uses `glue_jobs/run_single_sql_job.py`.
4. Pass its input Catalog tables in `--INPUT_TABLES_JSON`.
5. Add a conditional trigger after the required upstream job.
6. Add the SQL to the local runner.
7. Add assertions to `tests/test_pipeline.py`.
8. Push a branch and open a Pull Request.
9. Merge after CI passes; the DEV deployment workflow updates AWS.

## What usually changes

```text
SQL model
CloudFormation table
CloudFormation Glue Job
CloudFormation trigger
local runner
test
Athena validation query
```

The generic Glue runner normally does not change.
