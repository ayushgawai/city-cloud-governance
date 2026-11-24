terraform {
  required_version = ">= 1.5"
  required_providers { aws = { source = "hashicorp/aws", version = ">= 5.0" } }
}
variable "account_name" { type = string }
variable "monthly_budget_usd" { type = number }
variable "alert_emails" { type = list(string), default = [] }
variable "tags" { type = map(string), default = {} }

# Budget with forecast alerting: actual >80% and forecast >100% both notify.
# The RightSize / storage-tier maths behind the recommendations lives in
# src/citygov/cost.py (offline, unit-tested); this module enforces the guardrail.
resource "aws_budgets_budget" "account" {
  name         = "${var.account_name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.alert_emails
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.alert_emails
  }
}
resource "aws_ce_anomaly_monitor" "service" {
  name              = "${var.account_name}-anomalies"
  monitor_type      = "DIMENSIONAL"
  monitor_dimension = "SERVICE"
}
output "budget_id" { value = aws_budgets_budget.account.id }
