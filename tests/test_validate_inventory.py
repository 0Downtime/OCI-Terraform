#!/usr/bin/env python3
import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_inventory import validate_inventory  # noqa: E402


VALID_OCID = "ocid1.compartment.oc1..exampleid123"


def valid_document():
    return {
        "schema_version": 1,
        "tenancy": {
            "name": "test",
            "ocid": "ocid1.tenancy.oc1..exampleid123",
            "home_region": "us-ashburn-1",
            "target_region": "us-ashburn-1",
            "identity_domain_ocid": "ocid1.domain.oc1..exampleid123",
        },
        "compartments": [{"key": "cmp-top", "name": "cmp-top", "mode": "existing-managed", "ocid": VALID_OCID}],
        "groups": [],
        "policies": [],
        "tag_namespaces": [],
        "budgets": [],
        "events": [],
        "network": {label: [] for label in ("vcns", "subnets", "route_tables", "security_lists", "network_security_groups", "internet_gateways", "nat_gateways", "service_gateways", "drgs", "load_balancers", "bastions")},
        "security": {label: [] for label in ("vaults", "keys", "buckets", "log_groups", "service_connectors", "cloud_guard", "security_zones", "vulnerability_scanning", "alarms", "topics", "notifications")},
        "workloads": {label: [] for label in ("fusion_environment_families", "fusion_environments", "integration_instances", "ccs", "hyperion_epm")},
        "move_allowlist": [],
    }


class InventoryValidationTests(unittest.TestCase):
    def test_example_shape_is_valid(self):
        self.assertEqual(validate_inventory(valid_document()), [])

    def test_existing_resource_requires_ocid(self):
        document = valid_document()
        document["compartments"][0]["ocid"] = ""
        self.assertTrue(any("ocid is required" in error for error in validate_inventory(document)))

    def test_duplicate_ocid_is_rejected(self):
        document = valid_document()
        document["groups"] = [
            {"key": "network-admins", "mode": "existing-managed", "ocid": VALID_OCID},
            {"key": "security-admins", "mode": "existing-managed", "ocid": VALID_OCID},
        ]
        self.assertTrue(any("duplicate OCID" in error for error in validate_inventory(document)))

    def test_secret_fields_are_rejected(self):
        document = valid_document()
        document["groups"] = [{"key": "bad", "mode": "create", "password": "do-not-store"}]
        self.assertTrue(any("secret-bearing field" in error for error in validate_inventory(document)))

    def test_move_requires_two_ocids(self):
        document = valid_document()
        document["move_allowlist"] = [{"resource_key": "cmp-top", "from_parent_ocid": VALID_OCID, "to_parent_ocid": "bad"}]
        self.assertTrue(any("to_parent_ocid" in error for error in validate_inventory(document)))


if __name__ == "__main__":
    unittest.main()
