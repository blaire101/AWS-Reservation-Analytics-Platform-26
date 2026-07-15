from __future__ import annotations

import argparse
from pathlib import Path

import boto3


UPLOADS = [
    (Path("glue_jobs"), "code/glue_jobs"),
    (Path("sql/dwd"), "code/sql/dwd"),
    (Path("sql/dm"), "code/sql/dm"),
    (Path("sql/ads"), "code/sql/ads"),
    (Path("config"), "code/config"),
    (Path("aws/mock_data"), "data"),
]


def upload_tree(s3, source: Path, bucket: str, prefix: str) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Missing {source}. Follow RUNBOOK.md first.")

    for path in source.rglob("*"):
        if path.is_file():
            key = f"{prefix}/{path.relative_to(source).as_posix()}"
            s3.upload_file(str(path), bucket, key)
            print(f"Uploaded s3://{bucket}/{key}")


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
    s3 = session.client("s3")

    try:
        s3.head_bucket(Bucket=args.bucket)
    except Exception:
        if args.region == "us-east-1":
            s3.create_bucket(Bucket=args.bucket)
        else:
            s3.create_bucket(
                Bucket=args.bucket,
                CreateBucketConfiguration={"LocationConstraint": args.region},
            )
        print(f"Created bucket: {args.bucket}")

    for source, prefix in UPLOADS:
        upload_tree(s3, source, args.bucket, prefix)


if __name__ == "__main__":
    main()
