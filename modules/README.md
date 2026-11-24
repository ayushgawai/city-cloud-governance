# Terraform modules

| Module | Purpose |
|---|---|
| `iam-boundary/` | Permission boundary capping every role; hard-denies protect CloudTrail/Config/Organizations. Mirrored by `citygov.policy.evaluate_role`. |
| `tag-policy/` | Organizations tag policy + Config `REQUIRED_TAGS` rule for CostCenter/Environment/Owner/DataClassification. Mirrored by `evaluate_tags`. |
| `network-vpc/` | VPC with private subnets per AZ + VPC flow logs to CloudWatch. |
| `network-transit-gateway/` | TGW hub, separate prod/nonprod route tables, RAM share for spoke accounts. |
| `network-route53/` | Shared private hosted zone + resolver forwarding rule. |
| `network-load-balancer/` | ALB with access logs to an encrypted S3 bucket, HTTPS listener when a cert is supplied. |
| `cost-controls/` | Monthly budget (actual 80% / forecast 100% alerts) + Cost Explorer anomaly monitor. Math in `citygov.cost`. |
| `monitoring-prometheus/` | kube-prometheus-stack via Helm + governance alert rules (tag compliance, budget burn, TGW down). |
| `well-architected/` | Registers a Well-Architected workload; scoring is done by `citygov score`. |

See `../examples/multi-account/main.tf` for composition. These modules have
not been applied to a real AWS account — validate with `terraform init && terraform validate`
in an account with credentials before use.
