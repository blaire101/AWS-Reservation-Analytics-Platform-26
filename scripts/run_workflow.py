from __future__ import annotations

import argparse
import time

import boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trigger", default="reservation-analytics-manual-start")
    parser.add_argument("--workflow", default="reservation-analytics-workflow")
    parser.add_argument("--region", default="ap-southeast-1")
    parser.add_argument("--profile")
    args = parser.parse_args()

    session = boto3.Session(
        profile_name=args.profile,
        region_name=args.region,
    )
    glue = session.client("glue")

    before = {
        run["WorkflowRunId"]
        for run in glue.get_workflow_runs(Name=args.workflow, MaxResults=10).get("Runs", [])
    }
    glue.start_trigger(Name=args.trigger)
    print(f"Started trigger: {args.trigger}")

    run_id = None
    for _ in range(30):
        runs = glue.get_workflow_runs(Name=args.workflow, MaxResults=10).get("Runs", [])
        new_runs = [run for run in runs if run["WorkflowRunId"] not in before]
        if new_runs:
            run_id = new_runs[0]["WorkflowRunId"]
            break
        time.sleep(5)

    if run_id is None:
        raise SystemExit("No new workflow run appeared after starting the trigger.")

    print(f"Workflow run ID: {run_id}")
    while True:
        run = glue.get_workflow_run(
            Name=args.workflow,
            RunId=run_id,
            IncludeGraph=True,
        )["Run"]
        status = run["Status"]
        print(f"Workflow status: {status}")
        if status in {"COMPLETED", "STOPPED", "ERROR"}:
            break
        time.sleep(20)

    for node in run.get("Graph", {}).get("Nodes", []):
        job_runs = node.get("JobDetails", {}).get("JobRuns", [])
        if job_runs:
            print(f"{node['Name']}: {job_runs[0].get('JobRunState')}")

    if status != "COMPLETED":
        raise SystemExit(f"Workflow did not complete successfully: {status}")


if __name__ == "__main__":
    main()
