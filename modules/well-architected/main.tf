terraform {
  required_version = ">= 1.5"
  required_providers { aws = { source = "hashicorp/aws", version = ">= 5.0" } }
}
variable "workload_name" { type = string }
variable "tags" { type = map(string), default = {} }

# A Well-Architected workload + lens review anchor. The numeric scorecard
# itself is computed offline by `citygov score` (src/citygov/score.py) from
# inventory checks across the six pillars; this module registers the workload
# so findings can be attached to a review in the AWS console.
resource "aws_wellarchitected_workload" "this" {
  workload_name = var.workload_name
  description   = "Governance scorecard workload (scored by citygov CLI)"
  environment   = "PRODUCTION"
  lens_arns     = [] # add the Well-Architected Framework lens ARN in real use
  tags          = var.tags
}
output "workload_id" { value = aws_wellarchitected_workload.this.id }
