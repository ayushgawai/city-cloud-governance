"""CLI: plan, apply, score, forecast, bench. Offline, fixture-driven.

`plan`/`apply` mirror `terraform plan/apply`: plan evaluates the account
tree against policy + cost rules and prints the change set; apply records
the planned remediations to a local state file (never calls AWS).
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path

from . import __version__
from .policy import evaluate_tree, evaluate_account
from .cost import rightsize, storage_tier, ols_forecast, mape
from .score import checks_from_account, scorecard

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TREE = ROOT / "fixtures" / "accounts"


def load_tree(path: Path) -> list[dict]:
    files = sorted(Path(path).glob("*.json"))
    if not files:
        raise SystemExit(f"no *.json accounts under {path}")
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def plan_data(accounts: list[dict]) -> dict:
    drift = evaluate_tree(accounts)
    recs, total_saving = [], 0.0
    for a in accounts:
        for r in rightsize(a.get("instances", [])):
            recs.append({"account": a["name"], "kind": "rightsize", **r})
        for b in a.get("buckets", []):
            s = storage_tier(b)
            if s:
                recs.append({"account": a["name"], "kind": "storage_tier", **s})
    total_saving = round(sum(r["monthly_saving"] for r in recs), 2)
    return {"drift": drift, "recommendations": recs,
            "accounts": len(accounts), "noncompliant": len(drift),
            "monthly_saving": total_saving, "annual_saving": round(total_saving * 12, 2)}


def cmd_plan(args) -> int:
    d = plan_data(load_tree(args.tree))
    print(f"plan: {d['accounts']} accounts, {d['noncompliant']} non-compliant, "
          f"{len(d['recommendations'])} cost recommendations")
    for name, reasons in d["drift"].items():
        print(f"  DRIFT {name}:")
        for r in reasons:
            print(f"    - {r}")
    for r in d["recommendations"]:
        print(f"  SAVE  {r['account']}: {r['kind']} {r.get('id') or r.get('name')} "
              f"{r['from']}->{r['to']} ${r['monthly_saving']}/mo")
    print(f"plan: total saving ${d['monthly_saving']}/mo (${d['annual_saving']}/yr), "
          f"{sum(len(v) for v in d['drift'].values())} drift findings")
    return 1 if d["drift"] else 0


def cmd_apply(args) -> int:
    accounts = load_tree(args.tree)
    d = plan_data(accounts)
    state = {"applied": not args.dry_run, "recommendations": d["recommendations"],
             "drift_findings": sum(len(v) for v in d["drift"].values())}
    if args.dry_run:
        print(f"apply --dry-run: would remediate {len(d['recommendations'])} recommendations, "
              f"{state['drift_findings']} drift findings (no state written)")
        return 0
    out = Path(args.state)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"apply: recorded {len(d['recommendations'])} recommendations to {out} "
          f"(simulated — no AWS calls made)")
    return 0


def cmd_score(args) -> int:
    accounts = load_tree(args.tree)
    rows = []
    for a in accounts:
        card = scorecard(checks_from_account(a, evaluate_account(a)))
        rows.append((a["name"], card))
        print(f"{a['name']:<22} overall {card['overall']:>5}%  grade {card['grade']}  " +
              "  ".join(f"{k.split('_')[0]}={v:g}" for k, v in card["pillars"].items()))
    avg = round(sum(c["overall"] for _, c in rows) / len(rows), 1) if rows else 0.0
    print(f"score: fleet average {avg}% across {len(rows)} accounts")
    return 0


def cmd_forecast(args) -> int:
    accounts = load_tree(args.tree)
    for a in accounts:
        series = a.get("monthly_cost", [])
        fc = ols_forecast(series, horizon=args.horizon)
        print(f"{a['name']:<22} last=${series[-1] if series else 0:>8}  "
              f"next {args.horizon}mo forecast={fc}  total=${round(sum(fc),2)}")
    return 0


def cmd_bench(args) -> int:
    accounts = load_tree(args.tree)
    d = plan_data(accounts)
    planted = sum(a.get("planted_drift", 0) for a in accounts)
    detected = sum(len(v) for v in d["drift"].values())
    # forecast backtest: train on all but last 3 months, compare
    mapes, per = [], []
    for a in accounts:
        series = a.get("monthly_cost", [])
        if len(series) >= 6:
            pred = ols_forecast(series[:-3], horizon=3)
            m = mape(series[-3:], pred)
            mapes.append(m)
            per.append((a["name"], m))
    mean_mape = round(sum(mapes) / len(mapes), 2) if mapes else 0.0
    print(f"benchmark: {len(accounts)}-account fixture tree")
    print(f"  governance drift: planted={planted} detected={detected} "
          f"recall={round(detected/planted*100,1) if planted else 100.0}%")
    for name, reasons in d["drift"].items():
        print(f"    {name}: {len(reasons)} findings")
    print(f"  forecast backtest (train n-3, predict 3): mean MAPE={mean_mape}% over {len(per)} accounts")
    for name, m in per:
        print(f"    {name}: MAPE {m}%")
    print(f"  cost recommendations: {len(d['recommendations'])} "
          f"(${d['monthly_saving']}/mo, ${d['annual_saving']}/yr)")
    cards = [scorecard(checks_from_account(a, evaluate_account(a)))["overall"] for a in accounts]
    print(f"  well-architected: fleet average {round(sum(cards)/len(cards),1)}% "
          f"min {min(cards)}% max {max(cards)}%")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="citygov", description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "score", "forecast", "bench"):
        sp = sub.add_parser(name)
        sp.add_argument("--tree", type=Path, default=DEFAULT_TREE)
    sub.choices["forecast"].add_argument("--horizon", type=int, default=3)
    ap = sub.add_parser("apply")
    ap.add_argument("--tree", type=Path, default=DEFAULT_TREE)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--state", type=Path, default=ROOT / ".citygov" / "state.json")
    args = p.parse_args(argv)
    return {"plan": cmd_plan, "apply": cmd_apply, "score": cmd_score,
            "forecast": cmd_forecast, "bench": cmd_bench}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
