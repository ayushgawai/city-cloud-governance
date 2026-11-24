import unittest
from citygov.cost import rightsize, storage_tier, ols_forecast, mape, downsize


class TestCostMath(unittest.TestCase):
    def test_downsize_one_step(self):
        self.assertEqual(downsize("m5.2xlarge"), "m5.xlarge")
        self.assertIsNone(downsize("t3.micro"))
        self.assertIsNone(downsize("unknown.thing"))

    def test_rightsize_saving_math(self):
        recs = rightsize([{"id": "i-1", "instance_type": "m5.2xlarge", "cpu_peak_pct": 10, "mem_peak_pct": 20}])
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["to"], "m5.xlarge")
        self.assertEqual(recs[0]["monthly_saving"], 140.0)  # 280 - 140

    def test_rightsize_skips_busy(self):
        self.assertEqual(rightsize([{"id": "i-1", "instance_type": "m5.2xlarge",
                                     "cpu_peak_pct": 80, "mem_peak_pct": 20}]), [])
        # high memory alone also blocks it
        self.assertEqual(rightsize([{"id": "i-1", "instance_type": "m5.2xlarge",
                                     "cpu_peak_pct": 10, "mem_peak_pct": 90}]), [])

    def test_storage_glacier_saving(self):
        rec = storage_tier({"name": "b", "size_gb": 1000, "age_days": 200,
                            "accesses_per_month": 0, "storage_class": "STANDARD"})
        self.assertEqual(rec["to"], "GLACIER_FLEXIBLE")
        self.assertAlmostEqual(rec["monthly_saving"], 1000 * (0.023 - 0.0036), places=2)

    def test_storage_deep_archive_oldest(self):
        rec = storage_tier({"name": "b", "size_gb": 100, "age_days": 400,
                            "accesses_per_month": 0, "storage_class": "STANDARD"})
        self.assertEqual(rec["to"], "DEEP_ARCHIVE")

    def test_storage_no_rec_when_hot(self):
        self.assertIsNone(storage_tier({"name": "b", "size_gb": 100, "age_days": 10,
                                        "accesses_per_month": 99, "storage_class": "STANDARD"}))

    def test_forecast_flat_and_linear(self):
        self.assertEqual(ols_forecast([100.0] * 6, horizon=2), [100.0, 100.0])
        self.assertEqual(ols_forecast([0.0, 10.0, 20.0, 30.0], horizon=1), [40.0])
        self.assertEqual(ols_forecast([], horizon=2), [0.0, 0.0])

    def test_forecast_never_negative(self):
        self.assertTrue(all(v >= 0 for v in ols_forecast([100.0, 50.0, 10.0], horizon=3)))

    def test_mape(self):
        self.assertEqual(mape([100.0], [110.0]), 10.0)
        self.assertEqual(mape([0.0], [5.0]), 0.0)


if __name__ == "__main__":
    unittest.main()
