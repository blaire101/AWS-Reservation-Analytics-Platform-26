#!/usr/bin/env python3
"""Inspect the latest Version 2 workflow run and its graph."""

from __future__ import annotations

import argparse
import json

import boto3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", default="reservation-analytics-workflow")
    parser.add_argument("--region", default="ap-southeast-1")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    glue = boto3.client("glue", region_name=args.region)

    runs = glue.get_workflow_runs(Name=args.workflow, IncludeGraph=True, MaxResults=1)
    if not runs.get("Runs"):
        print("No workflow runs found yet.")
        return

    run = runs["Runs"][0]
    summary = {
        "Name": run.get("Name"),
        "WorkflowRunId": run.get("WorkflowRunId"),
        "Status": run.get("Status"),
        "StartedOn": str(run.get("StartedOn")),
        "CompletedOn": str(run.get("CompletedOn")),
        "Statistics": run.get("Statistics"),
        "RunProperties": run.get("WorkflowRunProperties"),
    }
    print(json.dumps(summary, indent=2, default=str))

    graph = run.get("Graph", {})
    for node in graph.get("Nodes", []):
        node_type = node.get("Type")
        name = (
            node.get("JobDetails", {}).get("JobRuns", [{}])[0].get("JobName")
            if node_type == "JOB"
            else node.get("Name")
        )
        print(f"{node_type}: {name}")


if __name__ == "__main__":
    main()
