"""Well-Architected style scorecard (6 pillars), scored from inventory checks.

Each check is boolean in the fixture. Score = passed/total*100 per pillar,
overall = mean of pillar scores. Grades: A>=90 B>=80 C>=70 D>=60 else F.
"""
from __future__ import annotations

PILLARS = {
    "operational_excellence": ["runbook_documented", "change_automated"],
    "security": ["boundary_on_all_roles", "cloudtrail_enabled", "encryption_at_rest", "no_wildcard_admin"],
    "reliability": ["multi_az", "backups_enabled"],
    "performance": ["rightsize_reviewed", "monitoring_enabled"],
    "cost_optimization": ["tags_complete", "storage_tiered"],
    "sustainability": ["region_allowlisted", "idle_resources_reviewed"],
}


def _grade(score: float) -> str:
    return "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"


def checks_from_account(account: dict, denials: list[str]) -> dict[str, bool]:
    """Derive checks from a fixture account + its policy denials."""
    joined = " ".join(denials)
    resources = account.get("resources", [])
    return {
        "runbook_documented": bool(account.get("runbook", False)),
        "change_automated": bool(account.get("change_automated", False)),
        "boundary_on_all_roles": "permission boundary" not in joined,
        "cloudtrail_enabled": bool(account.get("cloudtrail", False)),
        "encryption_at_rest": all(r.get("encrypted", False) for r in resources) if resources else False,
        "no_wildcard_admin": "wildcard" not in joined,
        "multi_az": bool(account.get("multi_az", False)),
        "backups_enabled": bool(account.get("backups", False)),
        "rightsize_reviewed": bool(account.get("rightsize_reviewed", False)),
        "monitoring_enabled": bool(account.get("monitoring", False)),
        "tags_complete": "missing required tag" not in joined and "not in" not in joined,
        "storage_tiered": bool(account.get("storage_tiered", False)),
        "region_allowlisted": "region" not in joined or "not in GovCloud" not in joined,
        "idle_resources_reviewed": bool(account.get("idle_reviewed", False)),
    }


def scorecard(checks: dict[str, bool]) -> dict:
    pillars = {}
    for pillar, keys in PILLARS.items():
        got = sum(1 for k in keys if checks.get(k))
        pillars[pillar] = round(got / len(keys) * 100, 1)
    overall = round(sum(pillars.values()) / len(pillars), 1)
    return {"pillars": pillars, "overall": overall, "grade": _grade(overall)}
