import json, unittest
from pathlib import Path
from citygov.cli import load_tree, plan_data
from citygov.score import scorecard, PILLARS

ROOT = Path(__file__).resolve().parents[1]


class TestScoreAndFixtures(unittest.TestCase):
    def test_perfect_scorecard(self):
        checks = {k: True for keys in PILLARS.values() for k in keys}
        card = scorecard(checks)
        self.assertEqual(card["overall"], 100.0)
        self.assertEqual(card["grade"], "A")

    def test_empty_scorecard_is_f(self):
        card = scorecard({})
        self.assertEqual(card["overall"], 0.0)
        self.assertEqual(card["grade"], "F")

    def test_fixture_tree_has_12_accounts(self):
        accounts = load_tree(ROOT / "fixtures" / "accounts")
        self.assertEqual(len(accounts), 12)

    def test_bench_invariants(self):
        accounts = load_tree(ROOT / "fixtures" / "accounts")
        d = plan_data(accounts)
        planted = sum(a["planted_drift"] for a in accounts)
        detected = sum(len(v) for v in d["drift"].values())
        self.assertEqual(detected, planted)  # fixture is designed for full recall
        self.assertEqual(d["accounts"], 12)
        self.assertGreater(d["monthly_saving"], 0)


if __name__ == "__main__":
    unittest.main()
