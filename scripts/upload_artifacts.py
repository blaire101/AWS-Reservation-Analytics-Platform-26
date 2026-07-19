#!/usr/bin/env python3
"""Upload Version 2 code and optional demo upstream data to S3."""

from __future__ import annotations

import argparse
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def ensure_bucket(s3_client, bucket: str, region: str) -> None:
    try:
        s3_client.head_bucket(Bucket=bucket)
        return
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if error_code not in {"404", "NoSuchBucket", "NotFound"}:
            # A 403 can also mean the globally unique bucket is owned by another account.
            if error_code in {"403", "AccessDenied"}:
                raise RuntimeError(
                    f"Cannot access bucket {bucket!r}. Use another globally unique name."
                ) from exc

    kwargs = {"Bucket": bucket}
    if region != "us-east-1":
        kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}

    s3_client.create_bucket(**kwargs)
    s3_client.get_waiter("bucket_exists").wait(Bucket=bucket)


def upload_file(s3_client, local_path: Path, bucket: str, key: str) -> None:
    if not local_path.is_file():
        raise FileNotFoundError(f"Required file not found: {local_path}")
    print(f"UPLOAD {local_path.relative_to(PROJECT_ROOT)} -> s3://{bucket}/{key}")
    s3_client.upload_file(str(local_path), bucket, key)


def upload_tree(
    s3_client,
    local_dir: Path,
    bucket: str,
    prefix: str,
    *,
    required: bool = True,
) -> None:
    if not local_dir.is_dir():
        if required:
            raise FileNotFoundError(f"Required directory not found: {local_dir}")
        return

    files = sorted(path for path in local_dir.rglob("*") if path.is_file())
    if required and not files:
        raise RuntimeError(f"No files found under required directory: {local_dir}")

    for path in files:
        relative = path.relative_to(local_dir).as_posix()
        upload_file(s3_client, path, bucket, f"{prefix.rstrip('/')}/{relative}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--region", default="ap-southeast-1")
    parser.add_argument(
        "--include-mock-data",
        action="store_true",
        help="Upload aws/mock_data as demo upstream ODS and DIM data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    s3_client = boto3.client("s3", region_name=args.region)

    ensure_bucket(s3_client, args.bucket, args.region)

    upload_file(
        s3_client,
        PROJECT_ROOT / "glue_jobs" / "run_single_sql_job.py",
        args.bucket,
        "code/glue_jobs/run_single_sql_job.py",
    )

    for layer in ("dwd", "dm", "ads"):
        upload_tree(
            s3_client,
            PROJECT_ROOT / "sql" / layer,
            args.bucket,
            f"code/sql/{layer}",
        )

    upload_tree(
        s3_client,
        PROJECT_ROOT / "config",
        args.bucket,
        "code/config",
        required=False,
    )

    if args.include_mock_data:
        upload_tree(
            s3_client,
            PROJECT_ROOT / "aws" / "mock_data" / "ods",
            args.bucket,
            "data/ods",
        )
        upload_tree(
            s3_client,
            PROJECT_ROOT / "aws" / "mock_data" / "dim",
            args.bucket,
            "data/dim",
        )
    else:
        print("SKIP mock ODS/DIM data (production-style mode)")

    print("Upload completed.")


if __name__ == "__main__":
    main()
