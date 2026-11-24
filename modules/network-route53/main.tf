terraform {
  required_version = ">= 1.5"
  required_providers { aws = { source = "hashicorp/aws", version = ">= 5.0" } }
}
variable "zone_name" { type = string } # e.g. internal.city.example
variable "vpc_id" { type = string }
variable "tags" { type = map(string), default = {} }

# Private hosted zone + resolver rules so spoke VPCs share one internal
# namespace instead of per-account zones drifting apart.
resource "aws_route53_zone" "private" {
  name = var.zone_name
  vpc { vpc_id = var.vpc_id }
  tags = var.tags
}
resource "aws_route53_resolver_rule" "forward" {
  name                 = "city-forward-internal"
  rule_type            = "FORWARD"
  domain_name          = var.zone_name
  resolver_endpoint_id = null # set to a resolver endpoint in the network account
  # target_ip blocks are environment-specific; supplied via tfvars in real use.
}
output "zone_id" { value = aws_route53_zone.private.zone_id }
