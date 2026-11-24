terraform {
  required_version = ">= 1.5"
  required_providers { aws = { source = "hashicorp/aws", version = ">= 5.0" } }
}

variable "boundary_name" { type = string, default = "city-permission-boundary" }
variable "allowed_regions" { type = list(string), default = ["us-gov-west-1", "us-gov-east-1"] }

# Permission boundary: caps every role in the account. Even an AdministratorAccess
# managed policy cannot exceed this. Hard-denies protect the audit trail itself.
data "aws_iam_policy_document" "boundary" {
  statement {
    sid       = "AllowScopedServices"
    effect    = "Allow"
    actions   = ["ec2:*", "s3:*", "rds:*", "lambda:*", "cloudwatch:*", "logs:*", "tag:*"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = var.allowed_regions
    }
  }
  statement {
    sid    = "HardDenyGuardrails"
    effect = "Deny"
    actions = ["iam:CreateUser", "iam:DeletePolicy", "organizations:LeaveOrganization",
               "cloudtrail:StopLogging", "cloudtrail:DeleteTrail", "config:DeleteConfigurationRecorder"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "boundary" {
  name   = var.boundary_name
  policy = data.aws_iam_policy_document.boundary.json
}

output "boundary_arn" { value = aws_iam_policy.boundary.arn }
output "boundary_name" { value = var.boundary_name }
