"""Cost math: RightSize + storage tiering + forecast.

All prices are illustrative monthly USD figures (GovCloud-flavoured,
rounded) kept in one table so the math — not live pricing — is testable.
"""
from __future__ import annotations

# instance type -> monthly USD (illustrative, on-demand, linux)
INSTANCE_MONTHLY = {
    "t3.micro": 8.0, "t3.small": 15.0, "t3.medium": 30.0, "t3.large": 60.0,
    "m5.large": 70.0, "m5.xlarge": 140.0, "m5.2xlarge": 280.0, "m5.4xlarge": 560.0,
    "c5.large": 62.0, "c5.xlarge": 124.0, "r5.large": 92.0, "r5.xlarge": 184.0,
}
# one step down in the same family ordering (largest -> smallest)
_SIZE_ORDER = ["4xlarge", "2xlarge", "xlarge", "large", "medium", "small", "micro"]


def downsize(instance_type: str) -> str | None:
    family, _, size = instance_type.partition(".")
    if size not in _SIZE_ORDER:
        return None
    idx = _SIZE_ORDER.index(size)
    if idx == len(_SIZE_ORDER) - 1:
        return None
    candidate = f"{family}.{_SIZE_ORDER[idx + 1]}"
    return candidate if candidate in INSTANCE_MONTHLY else None


def rightsize(instances: list[dict]) -> list[dict]:
    """Recommend a one-size-down move when peak CPU < 25% and peak mem < 40%.

    instance: {"id","instance_type","cpu_peak_pct","mem_peak_pct"}
    Only recommends when the smaller size exists in the price table.
    """
    recs = []
    for inst in instances:
        if inst["cpu_peak_pct"] < 25 and inst["mem_peak_pct"] < 40:
            smaller = downsize(inst["instance_type"])
            if smaller:
                cur, new = INSTANCE_MONTHLY[inst["instance_type"]], INSTANCE_MONTHLY[smaller]
                recs.append({"id": inst["id"], "from": inst["instance_type"], "to": smaller,
                             "monthly_saving": round(cur - new, 2)})
    return sorted(recs, key=lambda r: -r["monthly_saving"])


# storage class -> USD per GB-month (illustrative)
STORAGE_PER_GB = {"STANDARD": 0.023, "STANDARD_IA": 0.0125, "GLACIER_FLEXIBLE": 0.0036, "DEEP_ARCHIVE": 0.00099}


def storage_tier(bucket: dict) -> dict | None:
    """Recommend a colder tier from age + access frequency.

    bucket: {"name","size_gb","age_days","accesses_per_month"}
    Rules: >180d & <1 access/mo -> GLACIER_FLEXIBLE; >365d & 0 -> DEEP_ARCHIVE;
           >90d & <4/mo -> STANDARD_IA.  No rec if already cold enough.
    """
    cur = bucket.get("storage_class", "STANDARD")
    age, acc = bucket["age_days"], bucket["accesses_per_month"]
    target = None
    if age > 365 and acc == 0:
        target = "DEEP_ARCHIVE"
    elif age > 180 and acc < 1:
        target = "GLACIER_FLEXIBLE"
    elif age > 90 and acc < 4:
        target = "STANDARD_IA"
    if target is None or STORAGE_PER_GB[target] >= STORAGE_PER_GB[cur]:
        return None
    saving = bucket["size_gb"] * (STORAGE_PER_GB[cur] - STORAGE_PER_GB[target])
    return {"name": bucket["name"], "from": cur, "to": target, "monthly_saving": round(saving, 2)}


def ols_forecast(series: list[float], horizon: int = 3) -> list[float]:
    """Ordinary least squares on index 0..n-1, extrapolated `horizon` steps.

    Deterministic and dependency-free. Constant / flat series forecast flat.
    """
    n = len(series)
    if n == 0:
        return [0.0] * horizon
    if n == 1:
        return [float(series[0])] * horizon
    xs = list(range(n))
    mx, my = sum(xs) / n, sum(series) / n
    denom = sum((x - mx) ** 2 for x in xs)
    slope = 0.0 if denom == 0 else sum((x - mx) * (y - my) for x, y in zip(xs, series)) / denom
    intercept = my - slope * mx
    return [round(max(0.0, intercept + slope * (n + i)), 2) for i in range(horizon)]


def mape(actual: list[float], predicted: list[float]) -> float:
    """Mean absolute percentage error (%), skipping zero actuals."""
    pairs = [(a, p) for a, p in zip(actual, predicted) if a != 0]
    if not pairs:
        return 0.0
    return round(sum(abs(a - p) / abs(a) for a, p in pairs) / len(pairs) * 100, 2)
