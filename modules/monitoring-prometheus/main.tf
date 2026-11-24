terraform {
  required_version = ">= 1.5"
  required_providers {
    aws        = { source = "hashicorp/aws", version = ">= 5.0" }
    kubernetes = { source = "hashicorp/kubernetes", version = ">= 2.0" }
    helm       = { source = "hashicorp/helm", version = ">= 2.0" }
  }
}
variable "namespace" { type = string, default = "monitoring" }
variable "retention" { type = string, default = "30d" }
variable "tags" { type = map(string), default = {} }

# Prometheus on EKS (kube-prometheus-stack) + CloudWatch scrape targets.
# Alert rules cover the governance signals the scorecard consumes: drift in
# tag compliance, budget burn rate, and TGW attachment loss.
resource "helm_release" "kube_prometheus_stack" {
  name       = "kube-prometheus-stack"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  namespace  = var.namespace
  values = [yamlencode({
    prometheus = { prometheusSpec = { retention = var.retention } }
    alertmanager = { enabled = true }
    grafana      = { enabled = true }
  })]
}
resource "kubernetes_config_map" "governance_alerts" {
  metadata { name = "city-governance-alerts", namespace = var.namespace }
  data = {
    "governance.yaml" = <<-YAML
      groups:
        - name: city-governance
          rules:
            - alert: TagComplianceDropping
              expr: citygov_tag_compliance_ratio < 0.95
              for: 15m
              labels: { severity: warning }
            - alert: BudgetBurnRateHigh
              expr: citygov_budget_forecast_ratio > 1.0
              for: 1h
              labels: { severity: critical }
            - alert: TransitGatewayAttachmentDown
              expr: aws_tgw_attachment_up == 0
              for: 5m
              labels: { severity: critical }
    YAML
  }
}
output "namespace" { value = var.namespace }
