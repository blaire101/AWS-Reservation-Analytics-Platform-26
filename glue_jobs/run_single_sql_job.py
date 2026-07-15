"""Generic AWS Glue runner for one SQL model and one output table.

Required job arguments:
  --JOB_NAME
  --CODE_BASE_PATH
  --SQL_PATH
  --INPUT_TABLES_JSON
  --OUTPUT_PATH
  --OUTPUT_VIEW
"""
from __future__ import annotations

import json
import sys
from urllib.parse import urlparse

import boto3
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext


def read_s3_text(uri: str) -> str:
    parsed = urlparse(uri)
    response = boto3.client("s3").get_object(
        Bucket=parsed.netloc,
        Key=parsed.path.lstrip("/"),
    )
    return response["Body"].read().decode("utf-8")


args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "CODE_BASE_PATH",
        "SQL_PATH",
        "INPUT_TABLES_JSON",
        "OUTPUT_PATH",
        "OUTPUT_VIEW",
    ],
)

sc = SparkContext()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

for item in json.loads(args["INPUT_TABLES_JSON"]):
    spark.table(f"{item['database']}.{item['table']}").createOrReplaceTempView(
        item["view"]
    )

sql_uri = f"{args['CODE_BASE_PATH'].rstrip('/')}/{args['SQL_PATH']}"
spark.sql(read_s3_text(sql_uri))

view_name = args["OUTPUT_VIEW"]

(
    spark.table(view_name)
    .write
    .mode("overwrite")
    .parquet(args["OUTPUT_PATH"])
)

job.commit()
