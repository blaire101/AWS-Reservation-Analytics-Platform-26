# AWS Deployment Steps Explained

本文解释这个项目从本地代码到 AWS Glue Workflow 的完整部署过程，以及每一个命令和 AWS 资源分别负责什么。

---

## 1. 整体架构

本项目采用以下数仓分层：

```text
ODS → DWD + DIM → DM → ADS
```

任务依赖关系：

```text
Scheduled Start Trigger
          │
          ├── DWD Reservation Job ─┐
          │                         ├── DM Reservation Conversion Job
          └── DWD Paid Order Job ──┘               │
                                                    ├── ADS Campaign Job
                                                    └── ADS CRM Job
```

执行逻辑：

1. 定时触发器启动两个 DWD Job。
2. 两个 DWD Job 并行执行。
3. 两个 DWD Job 都成功后，条件触发器启动 DM Job。
4. DM Job 成功后，另一个条件触发器启动两个 ADS Job。
5. 两个 ADS Job 并行执行。

---

# 2. 本地环境变量

```bash
export AWS_REGION=ap-southeast-1
```

作用：

```text
指定 AWS 新加坡区域
```

项目中的 S3、Glue、CloudFormation、Athena 等资源都部署到：

```text
ap-southeast-1
```

---

```bash
export AWS_ACCOUNT_ID=$(
  aws sts get-caller-identity \
    --query Account \
    --output text
)
```

作用：

1. 使用当前 AWS CLI 凭证调用 STS。
2. 获取当前 AWS 账号的 12 位 Account ID。
3. 保存到环境变量 `AWS_ACCOUNT_ID`。

验证当前身份：

```bash
aws sts get-caller-identity
```

返回结果通常包括：

```json
{
  "UserId": "...",
  "Account": "123456789012",
  "Arn": "arn:aws:iam::123456789012:user/example-cli"
}
```

---

```bash
export ARTIFACT_BUCKET="reservation-analytics-${AWS_ACCOUNT_ID}-${AWS_REGION}"
```

作用：

生成一个较为唯一的 S3 Bucket 名称，例如：

```text
reservation-analytics-123456789012-ap-southeast-1
```

S3 Bucket 名称在全球范围内必须唯一，因此名称中加入：

```text
AWS Account ID + Region
```

可以降低重名概率。

---

# 3. 生成 Mock ODS 数据

```bash
python scripts/generate_mock_ods.py
```

作用：

1. 执行本地 Mock ODS SQL。
2. 创建三张模拟源表：
   - `ods_reservation_event`
   - `ods_order`
   - `dim_campaign`
3. 将表数据写成 Parquet。
4. 为 AWS Glue Catalog 提供可查询的底层文件。

生成目录：

```text
aws/mock_data/
├── ods/
│   ├── ods_reservation_event/
│   │   └── part-00000.parquet
│   └── ods_order/
│       └── part-00000.parquet
└── dim/
    └── dim_campaign/
        └── part-00000.parquet
```

这里没有模拟数据采集过程。

项目假设在真实公司中，ODS 数据已经由上游采集系统写入数据湖。本项目只是用 Parquet 文件模拟“已经到达数据湖的 ODS 数据”。

---

# 4. 上传代码和数据到 S3

```bash
python scripts/upload_artifacts.py \
  --bucket "$ARTIFACT_BUCKET" \
  --region "$AWS_REGION"
```

作用：

1. 如果 Bucket 不存在，则创建 Bucket。
2. 上传 Glue 通用执行脚本。
3. 上传 DWD、DM、ADS SQL。
4. 上传任务配置。
5. 上传 Mock ODS 和 DIM Parquet。

上传后的 S3 结构：

```text
s3://<bucket>/
├── code/
│   ├── glue_jobs/
│   │   └── run_single_sql_job.py
│   ├── sql/
│   │   ├── dwd/
│   │   ├── dm/
│   │   └── ads/
│   └── config/
│       └── jobs.json
│
└── data/
    ├── ods/
    │   ├── ods_reservation_event/
    │   └── ods_order/
    └── dim/
        └── dim_campaign/
```

## 为什么代码要上传到 S3？

AWS Glue Job 的 `ScriptLocation` 通常指向 S3 中的 Python 脚本：

```text
s3://<bucket>/code/glue_jobs/run_single_sql_job.py
```

Glue Job 启动时：

1. 从 S3 下载 Python Runner。
2. Runner 再从 S3 读取对应 SQL。
3. Spark SQL 执行转换。
4. 结果写回 S3。

---

# 5. CloudFormation 部署

```bash
aws cloudformation deploy \
  --template-file infra/glue-workflow.yaml \
  --stack-name reservation-analytics-dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    ProjectName=reservation-analytics \
    ArtifactBucket="$ARTIFACT_BUCKET" \
    DailySchedule="cron(0 2 * * ? *)" \
  --region "$AWS_REGION"
```

这个命令不是执行 ETL，而是创建和管理 AWS 基础设施。

## 参数解释

### `--template-file`

```text
infra/glue-workflow.yaml
```

CloudFormation 模板，声明项目需要创建哪些 AWS 资源。

---

### `--stack-name`

```text
reservation-analytics-dev
```

CloudFormation Stack 的名称。

一个 Stack 是一组统一创建、更新和删除的 AWS 资源。

---

### `--capabilities CAPABILITY_NAMED_IAM`

模板会创建一个有固定名称的 IAM Role，因此必须显式允许 CloudFormation 创建命名 IAM 资源。

没有这个参数通常会报：

```text
InsufficientCapabilitiesException
```

---

### `ProjectName`

用于生成统一的资源名，例如：

```text
reservation-analytics-workflow
reservation-analytics-dwd-paid-order
reservation-analytics-dm-reservation-conversion
```

---

### `ArtifactBucket`

告诉 CloudFormation：

```text
Glue Job 代码和 SQL 在哪个 S3 Bucket
```

---

### `DailySchedule`

```text
cron(0 2 * * ? *)
```

AWS Glue 调度使用 UTC。

它表示：

```text
每天 02:00 UTC
每天 10:00 Singapore Time
```

---

# 6. CloudFormation 创建的资源

模板通常创建以下资源。

## 6.1 Glue Databases

```text
reservation_ods
reservation_dim
reservation_dwd
reservation_dm
reservation_ads
```

这些是 Glue Data Catalog 中的逻辑数据库，不是独立数据库服务器。

它们保存：

```text
表名
字段
字段类型
S3 Location
文件格式
```

---

## 6.2 Glue Catalog Tables

例如：

```text
reservation_ods.ods_reservation_event
reservation_ods.ods_order
reservation_dim.dim_campaign

reservation_dwd.dwd_reservation_event
reservation_dwd.dwd_paid_order

reservation_dm.dm_reservation_conversion

reservation_ads.ads_campaign_conversion
reservation_ads.ads_crm_reserved_not_paid
```

表本身不保存数据。

真实数据保存在 S3，Glue Catalog Table 只是为它提供元数据。

---

## 6.3 IAM Role

例如：

```text
reservation-analytics-glue-role
```

Glue Job 运行时使用这个 Role。

它需要的权限包括：

```text
读取 S3 输入数据
读取 S3 代码和 SQL
写入 S3 输出
读取 Glue Catalog
写 CloudWatch Logs
```

这和执行部署命令的 IAM 用户不是同一个身份。

```text
CLI IAM User
    用于创建和部署资源

Glue IAM Role
    用于 Glue Job 实际执行
```

---

## 6.4 五个 Glue Jobs

```text
reservation-analytics-dwd-reservation-event
reservation-analytics-dwd-paid-order
reservation-analytics-dm-reservation-conversion
reservation-analytics-ads-campaign-conversion
reservation-analytics-ads-crm-reserved-not-paid
```

每个 Job 负责生成一张输出表。

所有 Job 都使用同一个通用 Runner：

```text
run_single_sql_job.py
```

但每个 Job 的参数不同，例如：

```text
SQL_PATH
INPUT_TABLES_JSON
OUTPUT_VIEW
OUTPUT_PATH
```

因此一个 Runner 可以执行不同 SQL。

---

## 6.5 Glue Workflow

```text
reservation-analytics-workflow
```

Workflow 用来：

```text
组织多个 Glue Jobs
展示依赖关系
展示每次完整运行的状态
```

Workflow 本身不处理数据。

真正处理数据的是 Glue Job。

---

## 6.6 Start Trigger

Workflow 必须从一个起始 Trigger 开始。

本项目使用：

```text
reservation-analytics-daily-start
```

类型：

```text
SCHEDULED
```

动作：

```text
同时启动两个 DWD Jobs
```

AWS Glue Workflow 中只能有一个 start trigger，因此不能同时为同一个 Workflow 配置：

```text
一个 Scheduled start trigger
+
一个 On-demand start trigger
```

否则 CloudFormation 会报：

```text
Workflow already has a starting trigger
```

AWS Glue 官方工作流模型是：

```text
一个 Start Trigger
+
后续多个 Conditional Triggers
```

Start Trigger 可以选择：

```text
ON_DEMAND
或
SCHEDULED
或
EVENT
```

但同一个 Workflow 只使用一个起始 Trigger。

---

## 6.7 Conditional Triggers

### DM Trigger

等待：

```text
DWD Reservation Job = SUCCEEDED
AND
DWD Paid Order Job = SUCCEEDED
```

然后启动：

```text
DM Reservation Conversion Job
```

---

### ADS Trigger

等待：

```text
DM Reservation Conversion Job = SUCCEEDED
```

然后同时启动：

```text
ADS Campaign Job
ADS CRM Job
```

条件触发器保证：

```text
上游失败时，下游不会继续执行
```

---

# 7. 为什么第一次 CloudFormation 失败？

失败原因：

```text
Workflow reservation-analytics-workflow already has a starting trigger
```

原模板同时创建：

```text
ManualStartTrigger
DailyStartTrigger
```

而且两个 Trigger 都被配置成同一个 Workflow 的起始 Trigger。

这不符合 Glue Workflow 的约束。

正确设计是只保留：

```text
DailyStartTrigger
```

手动测试时直接运行 Workflow，而不是再创建第二个起始 Trigger。

---

# 8. 查看 CloudFormation 失败原因

```bash
aws cloudformation describe-stack-events \
  --stack-name reservation-analytics-dev \
  --region "$AWS_REGION" \
  --query \
  "StackEvents[?ResourceStatus=='CREATE_FAILED'].[Timestamp,LogicalResourceId,ResourceType,ResourceStatusReason]" \
  --output table
```

作用：

从 Stack Events 中筛选所有：

```text
CREATE_FAILED
```

事件，并显示：

```text
失败时间
模板逻辑资源名
AWS 资源类型
具体错误原因
```

CloudFormation 部署失败时，优先看 Stack Events，而不是直接重新部署。

---

# 9. 为什么 Workflow 显示 EntityNotFound？

执行：

```bash
aws glue start-workflow-run \
  --name reservation-analytics-workflow \
  --region "$AWS_REGION"
```

返回：

```text
EntityNotFoundException
```

原因通常是：

1. CloudFormation Stack 创建失败。
2. CloudFormation 自动执行回滚。
3. 回滚删除了已经创建的 Workflow。
4. 因此该 Workflow 已经不存在。

先确保 Stack 状态是：

```text
CREATE_COMPLETE
```

再运行 Workflow。

---

# 10. 删除失败 Stack

先检查状态：

```bash
aws cloudformation describe-stacks \
  --stack-name reservation-analytics-dev \
  --region "$AWS_REGION" \
  --query "Stacks[0].StackStatus" \
  --output text
```

失败后常见状态：

```text
ROLLBACK_COMPLETE
```

删除 Stack：

```bash
aws cloudformation delete-stack \
  --stack-name reservation-analytics-dev \
  --region "$AWS_REGION"
```

等待删除完成：

```bash
aws cloudformation wait stack-delete-complete \
  --stack-name reservation-analytics-dev \
  --region "$AWS_REGION"
```

为什么要删除？

处于 `ROLLBACK_COMPLETE` 的首次创建 Stack 通常不能直接更新，需要先删除后重新创建。

---

# 11. 修复模板后重新部署

在：

```text
infra/glue-workflow.yaml
```

删除：

```yaml
ManualStartTrigger:
  Type: AWS::Glue::Trigger
  ...
```

以及任何引用 `ManualStartTrigger` 的 Output。

只保留一个起始 Trigger：

```yaml
DailyStartTrigger:
  Type: AWS::Glue::Trigger
  Properties:
    Type: SCHEDULED
    WorkflowName: !Ref AnalyticsWorkflow
    Schedule: !Ref DailySchedule
    StartOnCreation: true
    Actions:
      - JobName: !Ref DwdReservationJob
      - JobName: !Ref DwdPaidOrderJob
```

然后重新运行 CloudFormation deploy。

---

# 12. 确认部署成功

```bash
aws cloudformation describe-stacks \
  --stack-name reservation-analytics-dev \
  --region "$AWS_REGION" \
  --query "Stacks[0].StackStatus" \
  --output text
```

预期：

```text
CREATE_COMPLETE
```

确认 Workflow：

```bash
aws glue get-workflow \
  --name reservation-analytics-workflow \
  --region "$AWS_REGION"
```

确认 Jobs：

```bash
aws glue get-jobs \
  --region "$AWS_REGION" \
  --query "Jobs[?starts_with(Name, 'reservation-analytics')].Name" \
  --output table
```

确认 Triggers：

```bash
aws glue get-triggers \
  --region "$AWS_REGION" \
  --query "Triggers[?starts_with(Name, 'reservation-analytics')].[Name,Type,State]" \
  --output table
```

---

# 13. 手动运行完整 Workflow

部署成功后，可以通过 AWS Console：

```text
AWS Glue
→ Workflows
→ reservation-analytics-workflow
→ Run
```

也可以通过 CLI：

```bash
aws glue start-workflow-run \
  --name reservation-analytics-workflow \
  --region "$AWS_REGION"
```

返回：

```json
{
  "RunId": "..."
}
```

保存 Run ID：

```bash
export WORKFLOW_RUN_ID=$(
  aws glue start-workflow-run \
    --name reservation-analytics-workflow \
    --region "$AWS_REGION" \
    --query RunId \
    --output text
)
```

查看状态：

```bash
aws glue get-workflow-run \
  --name reservation-analytics-workflow \
  --run-id "$WORKFLOW_RUN_ID" \
  --include-graph \
  --region "$AWS_REGION"
```

> 注意：工作流的手动运行应通过 Workflow 的 Run 操作或 `start-workflow-run`。  
> `aws glue start-trigger` 的含义是“启用 Trigger”；对于 ON_DEMAND Trigger，启用时会立即触发。对于 Scheduled 和 Conditional Trigger，它主要用于激活 Trigger，而不是把定时 Trigger 当作普通的立即执行按钮。

---

# 14. 查看 Job 执行结果

控制台：

```text
AWS Glue
→ ETL jobs
→ 选择 Job
→ Runs
```

CLI 查询最近运行：

```bash
aws glue get-job-runs \
  --job-name reservation-analytics-dwd-reservation-event \
  --max-results 5 \
  --region "$AWS_REGION"
```

重点字段：

```text
JobRunState
StartedOn
CompletedOn
ExecutionTime
ErrorMessage
```

常见状态：

```text
STARTING
RUNNING
SUCCEEDED
FAILED
TIMEOUT
STOPPED
```

---

# 15. CloudWatch Logs 是干什么的？

Glue Job 失败时，CloudFormation 通常不会帮你分析 SQL 或 Spark 错误。

需要到：

```text
CloudWatch
→ Log groups
→ AWS Glue logs
```

常见问题包括：

```text
Glue Catalog 表不存在
S3 路径错误
SQL 字段不存在
Spark SQL 语法错误
IAM Role 没有 S3 权限
输出 Schema 与 Catalog 不一致
```

---

# 16. Athena 验证

```bash
python scripts/aws_validate.py \
  --bucket "$ARTIFACT_BUCKET" \
  --region "$AWS_REGION"
```

作用：

1. 在 Athena 提交 SQL。
2. 查询 DM 和 ADS Catalog 表。
3. 将 Athena 查询结果写到：

```text
s3://<bucket>/athena-results/
```

4. 在终端打印验证结果。

预期 DM：

| mid | order_flag | tag_reserved_not_paid |
|---|---:|---:|
| U001 | 1 | 0 |
| U002 | 0 | 1 |
| U003 | 0 | 1 |

Athena 验证的意义：

```text
Glue Job SUCCEEDED
不等于
业务数据一定正确
```

所以还需要检查：

```text
行数
主键重复
业务标签
转化人数
未转化名单
```

---

# 17. 每个 AWS 组件的职责

| 组件 | 作用 |
|---|---|
| PyCharm | 编写 SQL、Python 和 CloudFormation |
| GitHub | 保存代码版本 |
| GitHub Actions | 自动测试和部署 |
| S3 | 保存 ODS、代码、SQL、输出数据 |
| Glue Catalog | 保存表结构和 S3 Location |
| Glue Job | 执行 Spark SQL |
| Glue Workflow | 组织多个 Job |
| Scheduled Trigger | 定时启动工作流入口 |
| Conditional Trigger | 管理上下游依赖 |
| CloudFormation | 创建和更新所有 AWS 资源 |
| CloudWatch | 保存运行日志和错误 |
| Athena | 查询和验证 S3 数据 |
| IAM | 控制部署和运行权限 |

---

# 18. 实际大厂开发流程

正常生产开发不是每天在 Glue Console 中手写 SQL。

更常见的是：

```text
PyCharm 编写 SQL
→ 本地测试
→ Git feature branch
→ Pull Request
→ CI
→ Code Review
→ Merge
→ CI/CD 上传代码到 S3
→ CloudFormation 更新 Glue 资源
→ DEV Workflow 执行
→ Athena 验证
→ 发布到生产环境
```

Glue Console 主要用于：

```text
查看 Workflow 图
查看 Job Runs
查看参数
查看 Trigger 状态
进入 CloudWatch 排错
临时运行 DEV Workflow
```

---

# 19. 推荐的操作顺序

每次首次部署：

```text
1. aws sts get-caller-identity
2. 设置 AWS_REGION / ACCOUNT_ID / ARTIFACT_BUCKET
3. 本地运行 pytest
4. generate_mock_ods.py
5. upload_artifacts.py
6. cloudformation deploy
7. 检查 CREATE_COMPLETE
8. 检查 Workflow / Jobs / Triggers
9. 手动 Run Workflow
10. 检查五个 Job 状态
11. Athena 验证
12. 检查 S3 curated 输出
```

出现错误：

```text
CloudFormation 创建错误
→ describe-stack-events

Glue Job 运行错误
→ Glue Job Runs + CloudWatch

查询结果错误
→ Athena + SQL 业务逻辑

AccessDenied
→ IAM User / Glue Role 权限
```

---

# 20. 本次问题的正确修复总结

```text
问题：
同一个 Glue Workflow 创建了两个 Start Triggers

错误设计：
Manual Start Trigger
+
Daily Scheduled Start Trigger

正确设计：
保留一个 Scheduled Start Trigger
+
使用 Workflow Run 进行人工测试
+
使用 Conditional Triggers 管理 DM 和 ADS 依赖
```

修复顺序：

```bash
# 1. 删除失败 Stack
aws cloudformation delete-stack \
  --stack-name reservation-analytics-dev \
  --region "$AWS_REGION"

aws cloudformation wait stack-delete-complete \
  --stack-name reservation-analytics-dev \
  --region "$AWS_REGION"

# 2. 修改模板，删除 ManualStartTrigger

# 3. 重新部署
aws cloudformation deploy \
  --template-file infra/glue-workflow.yaml \
  --stack-name reservation-analytics-dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    ProjectName=reservation-analytics \
    ArtifactBucket="$ARTIFACT_BUCKET" \
    DailySchedule="cron(0 2 * * ? *)" \
  --region "$AWS_REGION"

# 4. 确认成功
aws cloudformation describe-stacks \
  --stack-name reservation-analytics-dev \
  --region "$AWS_REGION" \
  --query "Stacks[0].StackStatus" \
  --output text

# 5. 手动运行 Workflow
aws glue start-workflow-run \
  --name reservation-analytics-workflow \
  --region "$AWS_REGION"
```

---

## Official AWS references

- AWS Glue workflows overview
- Creating and running Glue workflows
- AWS Glue triggers
- Activating and deactivating triggers
- AWS CloudFormation `AWS::Glue::Trigger`
- Running and monitoring a Glue workflow
- AWS CloudFormation for AWS Glue
