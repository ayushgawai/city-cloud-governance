terraform {
  required_version = ">= 1.5"
  required_providers { aws = { source = "hashicorp/aws", version = ">= 5.0" } }
}
variable "name" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "certificate_arn" { type = string, default = null }
variable "internal" { type = bool, default = true }
variable "tags" { type = map(string), default = {} }

resource "aws_lb" "this" {
  name               = var.name
  load_balancer_type = "application"
  internal           = var.internal
  subnets            = var.subnet_ids
  security_groups    = [aws_security_group.lb.id]
  access_logs { bucket = aws_s3_bucket.logs.id, enabled = true }
  tags = var.tags
}
resource "aws_s3_bucket" "logs" {
  bucket        = "${var.name}-alb-logs"
  force_destroy = false
  tags          = var.tags
}
resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } }
}
resource "aws_security_group" "lb" {
  name   = "${var.name}-alb"
  vpc_id = var.vpc_id
  ingress {
    description = "HTTPS in"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.internal ? ["10.0.0.0/8"] : ["0.0.0.0/0"]
  }
  egress { from_port = 0, to_port = 0, protocol = "-1", cidr_blocks = ["0.0.0.0/0"] }
}
resource "aws_lb_listener" "https" {
  count             = var.certificate_arn == null ? 0 : 1
  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.certificate_arn
  default_action { type = "fixed-response", fixed_response { status_code = "404", content_type = "text/plain", message_body = "not found" } }
}
output "lb_arn" { value = aws_lb.this.arn }
output "dns_name" { value = aws_lb.this.dns_name }
