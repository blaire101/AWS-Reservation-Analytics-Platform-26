#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline", default="pipeline/reservation_pipeline.yaml")
    parser.add_argument("--stack-name", default="reservation-analytics-orchestration")
    parser.add_argument("--region", default="ap-southeast-1")
    parser.add_argument("--project-name", default="reservation-analytics")
    parser.add_argument("--dm-job", required=True)
    parser.add_argument("--ads-campaign-job", required=True)
    parser.add_argument("--ads-crm-job", required=True)
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.pipeline).read_text(encoding="utf-8"))

    command = [
        "aws", "cloudformation", "deploy",
        "--template-file", "platform/templates/step-functions-pipeline.yaml",
        "--stack-name", args.stack_name,
        "--capabilities", "CAPABILITY_NAMED_IAM",
        "--parameter-overrides",
        f"ProjectName={args.project_name}",
        f"DmConversionJob={args.dm_job}",
        f"AdsCampaignJob={args.ads_campaign_job}",
        f"AdsCrmJob={args.ads_crm_job}",
        f"UpstreamEventSource={config['trigger']['event_source']}",
        f"UpstreamEventDetailType={config['trigger']['detail_type']}",
        "--region", args.region,
    ]

    print("+", " ".join(command))
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
