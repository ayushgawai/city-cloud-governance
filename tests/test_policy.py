import unittest
from citygov.policy import evaluate_role, evaluate_tags, evaluate_account

BOUNDARY = "city-permission-boundary"
GOOD = {"CostCenter": "CC-1", "Environment": "prod", "Owner": "p", "DataClassification": "internal"}


class TestPolicyDenial(unittest.TestCase):
    def test_missing_boundary_denied(self):
        self.assertTrue(evaluate_role({"name": "r", "permission_boundary": None, "actions": ["s3:GetObject"]}))

    def test_wildcard_admin_denied(self):
        self.assertTrue(evaluate_role({"name": "r", "permission_boundary": BOUNDARY, "actions": ["*"]}))

    def test_hard_deny_cloudtrail_denied(self):
        self.assertTrue(evaluate_role({"name": "r", "permission_boundary": BOUNDARY,
                                       "actions": ["cloudtrail:StopLogging"]}))

    def test_guarded_wildcard_denied(self):
        self.assertTrue(evaluate_role({"name": "r", "permission_boundary": BOUNDARY, "actions": ["iam:*"]}))

    def test_scoped_role_allowed(self):
        self.assertEqual(evaluate_role({"name": "r", "permission_boundary": BOUNDARY,
                                        "actions": ["ec2:Describe*", "s3:GetObject"]}), [])

    def test_missing_tags_denied(self):
        self.assertEqual(len(evaluate_tags({"type": "s3_bucket", "id": "b", "tags": {}})), 4)

    def test_bad_environment_denied(self):
        self.assertTrue(evaluate_tags({"type": "s3_bucket", "id": "b", "tags": {**GOOD, "Environment": "production"}}))

    def test_good_tags_allowed(self):
        self.assertEqual(evaluate_tags({"type": "s3_bucket", "id": "b", "tags": GOOD}), [])

    def test_non_govcloud_region_denied(self):
        acct = {"name": "a", "region": "us-east-1", "roles": [], "resources": []}
        self.assertTrue(evaluate_account(acct))

    def test_compliant_account_allowed(self):
        acct = {"name": "a", "region": "us-gov-west-1",
                "roles": [{"name": "r", "permission_boundary": BOUNDARY, "actions": ["s3:GetObject"]}],
                "resources": [{"type": "ec2_instance", "id": "i-1", "tags": GOOD}]}
        self.assertEqual(evaluate_account(acct), [])


if __name__ == "__main__":
    unittest.main()
