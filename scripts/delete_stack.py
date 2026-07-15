from __future__ import annotations

import argparse
import time

import boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack", default="reservation-analytics-dev")
    parser.add_argument("--region", default="ap-southeast-1")
    parser.add_argument("--profile")
    args = parser.parse_args()

    session = boto3.Session(
        profile_name=args.profile,
        region_name=args.region,
    )
    cf = session.client("cloudformation")
    cf.delete_stack(StackName=args.stack)
    print(f"Deleting stack: {args.stack}")

    waiter = cf.get_waiter("stack_delete_complete")
    waiter.wait(StackName=args.stack)
    print("Stack deleted. The artifact S3 bucket is retained.")


if __name__ == "__main__":
    main()
