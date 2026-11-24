terraform {
  required_version = ">= 1.5"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 5.0" } }
}
provider "aws" { region = "us-gov-west-1" } # network / hub account profile in real use

locals {
  tags = { CostCenter = "CC-100", Environment = "prod", Owner = "platform", DataClassification = "internal" }
}

module "boundary" { source = "../../modules/iam-boundary" }
module "tag_policy" { source = "../../modules/tag-policy" }
module "hub_vpc" {
  source     = "../../modules/network-vpc"
  name       = "hub"
  cidr_block = "10.0.0.0/16"
  tags       = local.tags
}
module "tgw" { source = "../../modules/network-transit-gateway", tags = local.tags }
module "dns" {
  source    = "../../modules/network-route53"
  zone_name = "internal.city.example"
  vpc_id    = module.hub_vpc.vpc_id
  tags      = local.tags
}
module "portal_alb" {
  source     = "../../modules/network-load-balancer"
  name       = "citizen-portal"
  vpc_id     = module.hub_vpc.vpc_id
  subnet_ids = module.hub_vpc.private_subnet_ids
  tags       = local.tags
}
module "cost" {
  source             = "../../modules/cost-controls"
  account_name       = "prod-citizen-portal"
  monthly_budget_usd = 12000
}
module "monitoring" { source = "../../modules/monitoring-prometheus" }
module "review" {
  source        = "../../modules/well-architected"
  workload_name = "citizen-portal"
  tags          = local.tags
}
