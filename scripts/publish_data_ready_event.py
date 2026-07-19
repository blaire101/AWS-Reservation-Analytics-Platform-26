#!/usr/bin/env python3
"""Publish a demo upstream data-ready event to Amazon EventBridge."""

from __future__ import annotations

import argparse
import json

import boto3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--business-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--region", default="ap-southeast-1")
    parser.add_argument("--event-bus", default="default")
    parser.add_argument("--source", default="data-platform.upstream")
    parser.add_argument(
        "--detail-type",
        default="Reservation Source Data Ready",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    events = boto3.client("events", region_name=args.region)

    detail = {
        "business_date": args.business_date,
        "status": "SUCCEEDED",
        "ods_ready": True,
        "dim_ready": True,
    }

    response = events.put_events(
        Entries=[
            {
                "Source": args.source,
                "DetailType": args.detail_type,
                "Detail": json.dumps(detail),
                "EventBusName": args.event_bus,
            }
        ]
    )

    if response.get("FailedEntryCount", 0):
        raise RuntimeError(f"EventBridge rejected the event: {response}")

    print(json.dumps(response, indent=2, default=str))
    print(f"Published data-ready event for {args.business_date}")


if __name__ == "__main__":
    main()
