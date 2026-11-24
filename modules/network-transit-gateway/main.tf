terraform {
  required_version = ">= 1.5"
  required_providers { aws = { source = "hashicorp/aws", version = ">= 5.0" } }
}
variable "name" { type = string, default = "city-tgw" }
variable "amazon_side_asn" { type = number, default = 64512 }
variable "tags" { type = map(string), default = {} }

# Hub for the multi-account network: spoke VPCs attach here, shared-services
# (DNS, logging, egress) live in the network account.
resource "aws_ec2_transit_gateway" "this" {
  description                     = "City multi-account hub"
  amazon_side_asn                 = var.amazon_side_asn
  default_route_table_association = "disable" # explicit route tables per trust zone
  default_route_table_propagation = "disable"
  tags                            = merge(var.tags, { Name = var.name })
}
resource "aws_ec2_transit_gateway_route_table" "prod" {
  transit_gateway_id = aws_ec2_transit_gateway.this.id
  tags               = merge(var.tags, { Name = "${var.name}-prod" })
}
resource "aws_ec2_transit_gateway_route_table" "nonprod" {
  transit_gateway_id = aws_ec2_transit_gateway.this.id
  tags               = merge(var.tags, { Name = "${var.name}-nonprod" })
}
# RAM share so spoke accounts (different principals) can attach their VPCs.
resource "aws_ram_resource_share" "tgw" {
  name                      = "${var.name}-share"
  allow_external_principals = false
}
resource "aws_ram_resource_association" "tgw" {
  resource_arn       = aws_ec2_transit_gateway.this.arn
  resource_share_arn = aws_ram_resource_share.tgw.arn
}
output "transit_gateway_id" { value = aws_ec2_transit_gateway.this.id }
output "route_table_ids" { value = { prod = aws_ec2_transit_gateway_route_table.prod.id, nonprod = aws_ec2_transit_gateway_route_table.nonprod.id } }
