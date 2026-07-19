#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--region", default="ap-southeast-1")
    args = parser.parse_args()

    events = boto3.client("events", region_name=args.region)

    detail = {
        "business_date": args.business_date,
        "status": "SUCCEEDED",
        "dwd_ready": True,
        "dim_ready": True
    }

    response = events.put_events(
        Entries=[
            {
                "Source": "data-platform.upstream",
                "DetailType": "Reservation DWD Data Ready",
                "Detail": json.dumps(detail),
                "EventBusName": "default"
            }
        ]
    )

    if response.get("FailedEntryCount", 0):
        raise RuntimeError(response)

    print(json.dumps(response, indent=2, default=str))


if __name__ == "__main__":
    main()
