#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-machine-arn", required=True)
    parser.add_argument("--region", default="ap-southeast-1")
    args = parser.parse_args()

    client = boto3.client("stepfunctions", region_name=args.region)
    executions = client.list_executions(
        stateMachineArn=args.state_machine_arn,
        maxResults=1
    ).get("executions", [])

    if not executions:
        print("No Step Functions executions found.")
        return

    execution = client.describe_execution(
        executionArn=executions[0]["executionArn"]
    )

    print(json.dumps({
        "name": execution["name"],
        "status": execution["status"],
        "startDate": execution["startDate"],
        "stopDate": execution.get("stopDate"),
        "input": json.loads(execution["input"]),
        "error": execution.get("error"),
        "cause": execution.get("cause")
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
