"""Generate the deterministic 12-account fixture tree (run once, commit output)."""
import json, random
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "fixtures" / "accounts"
NAMES = ["prod-permits", "prod-payments", "prod-gis", "staging-apps", "dev-sandbox",
         "shared-network", "shared-logging", "security-tooling", "data-warehouse",
         "citizen-portal", "fleet-iot", "archive-records"]
GOOD_TAGS = {"CostCenter": "CC-100", "Environment": "prod", "Owner": "platform",
             "DataClassification": "internal"}


def acct(i, name):
    rng = random.Random(1000 + i)
    drift = []
    region = "us-gov-west-1" if i % 3 else "us-gov-east-1"
    roles = [{"name": "app-role", "permission_boundary": "city-permission-boundary",
              "actions": ["ec2:Describe*", "s3:GetObject"]}]
    resources = [{"type": "ec2_instance", "id": f"i-{i:04d}", "encrypted": True, "tags": dict(GOOD_TAGS)}]
    # planted drift on accounts 1,4,6,9 (1-indexed-ish): boundary, wildcard, region, tags
    if i == 1:
        roles[0]["permission_boundary"] = None; drift.append(1)
    if i == 4:
        roles.append({"name": "legacy-admin", "permission_boundary": "city-permission-boundary",
                      "actions": ["*"]}); drift.append(1)
    if i == 6:
        region = "us-east-1"; drift.append(1)
    if i == 9:
        resources[0]["tags"] = {"Environment": "production", "Owner": "data"}; drift.append(3)
        # missing CostCenter+DataClassification (2) + bad Environment value (1) = 3 findings
    base = 4000 + i * 650
    monthly = [round(base * (1 + 0.012 * m) + rng.uniform(-60, 60), 2) for m in range(12)]
    return {
        "account_id": f"2000000000{i:02d}", "name": name, "region": region,
        "roles": roles, "resources": resources,
        "planted_drift": sum(drift),
        "cloudtrail": i != 7, "multi_az": i % 4 != 0, "backups": i % 5 != 0,
        "monitoring": True, "runbook": i % 3 != 0, "change_automated": i % 2 == 0,
        "rightsize_reviewed": i % 3 == 0, "storage_tiered": i % 4 == 0, "idle_reviewed": i % 2 == 1,
        "monthly_cost": monthly,
        "instances": [
            {"id": f"i-{i:04d}a", "instance_type": "m5.2xlarge", "cpu_peak_pct": 12 + i, "mem_peak_pct": 30},
            {"id": f"i-{i:04d}b", "instance_type": "t3.large", "cpu_peak_pct": 68, "mem_peak_pct": 71},
        ] if i % 2 == 0 else [
            {"id": f"i-{i:04d}a", "instance_type": "m5.xlarge", "cpu_peak_pct": 55, "mem_peak_pct": 60}],
        "buckets": [{"name": f"{name}-archive", "size_gb": 2000 + i * 300, "age_days": 240,
                     "accesses_per_month": 0, "storage_class": "STANDARD"}] if i % 3 == 0 else [],
    }


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    for i, name in enumerate(NAMES):
        (OUT / f"{i+1:02d}-{name}.json").write_text(json.dumps(acct(i, name), indent=2), encoding="utf-8")
    print(f"wrote {len(NAMES)} accounts to {OUT}")
