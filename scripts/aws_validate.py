from __future__ import annotations

import argparse
import time

import boto3


QUERIES = {
    "dm": """
        SELECT mid, order_flag, tag_reserved_not_paid, order_id
        FROM reservation_dm.dm_reservation_conversion
        ORDER BY mid
    """,
    "campaign_ads": """
        SELECT campaign_id, site, channel, reserved_users, paid_users,
               unconverted_users, conversion_rate
        FROM reservation_ads.ads_campaign_conversion
        ORDER BY channel
    """,
    "crm_ads": """
        SELECT mid, campaign_id, product_id, site, channel
        FROM reservation_ads.ads_crm_reserved_not_paid
        ORDER BY mid
    """,
}


def wait(athena, execution_id: str) -> None:
    while True:
        status = athena.get_query_execution(
            QueryExecutionId=execution_id
        )["QueryExecution"]["Status"]
        state = status["State"]
        if state == "SUCCEEDED":
            return
        if state in {"FAILED", "CANCELLED"}:
            raise RuntimeError(status.get("StateChangeReason", state))
        time.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--region", default="ap-southeast-1")
    parser.add_argument("--profile")
    args = parser.parse_args()

    session = boto3.Session(
        profile_name=args.profile,
        region_name=args.region,
    )
    athena = session.client("athena")
    output = f"s3://{args.bucket}/athena-results/"

    for name, query in QUERIES.items():
        execution_id = athena.start_query_execution(
            QueryString=query,
            ResultConfiguration={"OutputLocation": output},
        )["QueryExecutionId"]
        wait(athena, execution_id)
        rows = athena.get_query_results(
            QueryExecutionId=execution_id
        )["ResultSet"]["Rows"]
        print(f"\n=== {name.upper()} ===")
        for row in rows:
            print(" | ".join(
                cell.get("VarCharValue", "NULL")
                for cell in row["Data"]
            ))


if __name__ == "__main__":
    main()
