terraform {
  required_version = ">= 1.5"
  required_providers { aws = { source = "hashicorp/aws", version = ">= 5.0" } }
}

# AWS Organizations tag policy (apply at OU level) + a Config rule backstop so
# untagged creates are both prevented (policy) and detected (rule).
variable "required_tags" {
  type = map(object({ values = optional(list(string)) }))
  default = {
    CostCenter         = {}
    Environment        = { values = ["prod", "staging", "dev", "sandbox"] }
    Owner              = {}
    DataClassification = { values = ["public", "internal", "confidential", "restricted"] }
  }
}

resource "aws_organizations_policy" "tag_policy" {
  name    = "city-required-tags"
  type    = "TAG_POLICY"
  content = jsonencode({ tags = { for k, v in var.required_tags : k => merge(
    { tag_key = { "@@assign" = k }, enforced_for = { "@@assign" = ["ec2:instance", "s3:bucket", "rds:db"] } },
    v.values == null ? {} : { tag_value = { "@@assign" = v.values } }) } })
}

resource "aws_config_rule" "required_tags" {
  name = "city-required-tags"
  source { owner = "AWS", source_identifier = "REQUIRED_TAGS" }
  input_parameters = jsonencode({ tag1Key = "CostCenter", tag2Key = "Environment",
                                  tag3Key = "Owner", tag4Key = "DataClassification" })
}

output "tag_policy_id" { value = aws_organizations_policy.tag_policy.id }
output "config_rule_arn" { value = aws_config_rule.required_tags.arn }
