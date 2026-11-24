"""Policy engine mirroring modules/iam-boundary and modules/tag-policy.

Pure functions over plain dicts (the fixture / inventory shape) so denial
cases are unit-testable without AWS.

Fixture account shape:
  {
    "account_id": "111122223333", "name": "prod-permits",
    "region": "us-gov-west-1",
    "roles": [{"name": "...", "permission_boundary": "city-boundary"|null,
               "actions": ["ec2:Describe*", ...]}],
    "resources": [{"type": "ec2_instance", "id": "...", "tags": {...}}]
  }
"""
from __future__ import annotations

ALLOWED_REGIONS = {"us-gov-west-1", "us-gov-east-1"}  # GovCloud partitions only
REQUIRED_TAGS = ("CostCenter", "Environment", "Owner", "DataClassification")
ALLOWED_ENVIRONMENTS = {"prod", "staging", "dev", "sandbox"}
ALLOWED_CLASSIFICATIONS = {"public", "internal", "confidential", "restricted"}
BOUNDARY_NAME = "city-permission-boundary"
# Actions no role may take even inside the boundary (mirrors the Deny
# statements in modules/iam-boundary/main.tf).
HARD_DENY_ACTIONS = {
    "iam:CreateUser", "iam:DeletePolicy", "organizations:LeaveOrganization",
    "cloudtrail:StopLogging", "cloudtrail:DeleteTrail", "config:DeleteConfigurationRecorder",
}


def evaluate_role(role: dict) -> list[str]:
    """Return denial reasons for one IAM role ([] == allowed)."""
    reasons: list[str] = []
    if role.get("permission_boundary") != BOUNDARY_NAME:
        reasons.append(f"role {role.get('name')}: missing permission boundary {BOUNDARY_NAME}")
    for action in role.get("actions", []):
        if action in ("*", "*:*"):
            reasons.append(f"role {role.get('name')}: wildcard admin action '{action}' denied")
        elif action in HARD_DENY_ACTIONS:
            reasons.append(f"role {role.get('name')}: hard-denied action '{action}'")
        elif action.endswith(":*") and action.split(":")[0] in {"iam", "organizations", "cloudtrail"}:
            reasons.append(f"role {role.get('name')}: wildcard on guarded service '{action}' denied")
    return reasons


def evaluate_tags(resource: dict) -> list[str]:
    tags = resource.get("tags") or {}
    label = f"{resource.get('type')}/{resource.get('id')}"
    reasons = [f"{label}: missing required tag {t}" for t in REQUIRED_TAGS if not tags.get(t)]
    env = tags.get("Environment")
    if env and env not in ALLOWED_ENVIRONMENTS:
        reasons.append(f"{label}: Environment '{env}' not in {sorted(ALLOWED_ENVIRONMENTS)}")
    cls = tags.get("DataClassification")
    if cls and cls not in ALLOWED_CLASSIFICATIONS:
        reasons.append(f"{label}: DataClassification '{cls}' not in {sorted(ALLOWED_CLASSIFICATIONS)}")
    return reasons


def evaluate_account(account: dict) -> list[str]:
    reasons: list[str] = []
    if account.get("region") not in ALLOWED_REGIONS:
        reasons.append(f"account {account.get('name')}: region '{account.get('region')}' "
                       f"not in GovCloud allowlist {sorted(ALLOWED_REGIONS)}")
    for role in account.get("roles", []):
        reasons.extend(evaluate_role(role))
    for res in account.get("resources", []):
        reasons.extend(evaluate_tags(res))
    return reasons


def evaluate_tree(accounts: list[dict]) -> dict[str, list[str]]:
    """Map account name -> denial reasons (only non-compliant accounts)."""
    out: dict[str, list[str]] = {}
    for acct in accounts:
        reasons = evaluate_account(acct)
        if reasons:
            out[acct["name"]] = reasons
    return out
