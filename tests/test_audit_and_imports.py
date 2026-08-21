import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_import_manifest import generate, render_hcl, validate_hcl_output_path  # noqa: E402
from oci_audit import compare, normalize, summary, validate_snapshot  # noqa: E402
from plan_oci_exports import plan  # noqa: E402
from test_validate_inventory import VALID_OCID, valid_document  # noqa: E402
from validate_inventory import validate_inventory  # noqa: E402


class AuditAndImportTests(unittest.TestCase):
    def test_global_duplicate_and_invalid_type_are_rejected(self):
        document = valid_document()
        document["groups"] = [{"key": "group", "group_type": "classic", "mode": "existing-managed", "ocid": VALID_OCID}]
        document["network"]["vcns"] = [{"key": "vcn", "mode": "existing-managed", "ocid": VALID_OCID}]
        errors = validate_inventory(document)
        self.assertTrue(any("duplicate OCID globally" in error for error in errors))
        self.assertTrue(any("expected one of" in error for error in errors))

    def test_same_key_is_allowed_for_distinct_resource_types(self):
        document = valid_document()
        document["groups"] = [{"key": "shared", "group_type": "classic", "mode": "create"}]
        document["network"]["vcns"] = [{"key": "shared", "mode": "create"}]
        self.assertEqual(validate_inventory(document), [])

    def test_noncommercial_realm_ocids_are_accepted(self):
        document = valid_document()
        document["tenancy"]["ocid"] = "ocid1.tenancy.oc2..tenancyexample"
        document["compartments"][0]["ocid"] = "ocid1.compartment.oc2..compartmentexample"
        self.assertEqual(validate_inventory(document), [])

    def test_parent_reference_and_move_binding_are_rejected(self):
        document = valid_document()
        document["compartments"][0]["parent_key"] = "does-not-exist"
        document["compartments"][0]["mode"] = "move-allowlisted"
        errors = validate_inventory(document)
        self.assertTrue(any("unresolved inventory key" in error for error in errors))
        self.assertTrue(any("requires an exact move_allowlist" in error for error in errors))

    def test_secret_content_is_rejected(self):
        document = valid_document()
        document["groups"] = [{"key": "bad", "group_type": "classic", "mode": "create", "description": "-----BEGIN PRIVATE KEY-----"}]
        self.assertTrue(any("secret-bearing content" in error for error in validate_inventory(document)))

    def test_export_plan_covers_diagram_foundation_without_execution(self):
        export_plan = plan("us-ashburn-1")
        commands = "\n".join(item["command"] for item in export_plan["commands"])
        for expected in ("iam domain list", "identity-domains groups list", "network nsg list", "cloud-guard target list", "ons topic list", "fusion-environment-family list"):
            self.assertIn(expected, commands)
        self.assertTrue(export_plan["read_only"])
        self.assertTrue(all(item["execute"] is False for item in export_plan["commands"]))

    def test_stage_generator_only_emits_implemented_stage_addresses(self):
        document = valid_document()
        document["network"]["vcns"] = [{"key": "shared", "mode": "existing-managed", "ocid": "ocid1.vcn.oc1..vcnexample"}]
        document["network"]["subnets"] = [{"key": "web", "mode": "existing-managed", "ocid": "ocid1.subnet.oc1..subnetexample", "vcn_key": "shared"}]
        document["security"]["vaults"] = [{"key": "vault", "mode": "existing-managed", "ocid": "ocid1.vault.oc1..vaultexample"}]
        network = generate(document, "02-network")
        self.assertEqual([item["address"] for item in network["imports"]], ['oci_core_subnet.this["web"]', 'oci_core_vcn.this["shared"]'])
        self.assertNotIn("oci_kms_vault", render_hcl(network))
        security = generate(document, "03-security-observability")
        self.assertEqual([item["address"] for item in security["imports"]], ['oci_kms_vault.this["vault"]'])

    def test_generator_validates_before_writing_manifest(self):
        document = valid_document()
        document["compartments"][0]["ocid"] = "bad"
        with self.assertRaises(ValueError):
            generate(document, "00-bootstrap")

    def test_domain_group_import_address_is_explicit(self):
        document = valid_document()
        import_id = "idcsEndpoint/example.identity.oraclecloud.com/groups/scim-group-id"
        document["groups"] = [{"key": "domain-admins", "name": "domain-admins", "description": "test", "group_type": "identity-domain", "mode": "existing-managed", "ocid": "ocid1.group.oc1..domainexample", "import_id": import_id}]
        manifest = generate(document, "01-governance-iam")
        self.assertEqual(manifest["imports"][0]["address"], 'oci_identity_domains_group.this["domain-admins"]')
        self.assertEqual(manifest["imports"][0]["id"], import_id)
        self.assertEqual(manifest["imports"][0]["ocid"], "ocid1.group.oc1..domainexample")

    def test_domain_group_requires_provider_import_id(self):
        document = valid_document()
        document["groups"] = [{"key": "domain-admins", "group_type": "identity-domain", "mode": "existing-managed", "ocid": "ocid1.group.oc1..domainexample"}]
        self.assertTrue(any("import_id" in error for error in validate_inventory(document)))

    def test_generated_hcl_must_live_in_its_stage(self):
        validate_hcl_output_path(ROOT / "stages" / "02-network" / "imports.generated.tf", "02-network")
        with self.assertRaises(ValueError):
            validate_hcl_output_path(ROOT / "audit" / "generated" / "02-network-imports.tf", "02-network")

    def test_normalization_is_deterministic_and_redacts_ocids(self):
        raw = {
            "metadata": {"generated_at": "2026-08-20T00:00:00Z", "region": "us-ashburn-1", "tenancy": {"ocid": "ocid1.tenancy.oc1..tenancyexample"}},
            "resources": [{"oci_type": "oci_core_vcn", "ocid": "ocid1.vcn.oc1..vcnexample", "display_name": "shared", "attributes": {"cidr_blocks": ["10.0.0.0/16"]}, "mode": "observe-only"}],
        }
        first = normalize(raw, redacted=True)
        second = normalize(copy.deepcopy(raw), redacted=True)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertNotIn("ocid1.vcn", json.dumps(first))
        self.assertIn("sha256:", json.dumps(first))
        self.assertIn("OCI Audit Summary", summary(first))

    def test_redaction_covers_nested_ocids_and_preserves_snapshot_identity(self):
        nested_ocid = "ocid1.subnet.oc2..nestedexample"
        raw = {
            "metadata": {"generated_at": "2026-08-20T00:00:00Z", "region": "us-langley-1", "tenancy": {"ocid": "ocid1.tenancy.oc2..tenancyexample"}},
            "resources": [{"oci_type": "oci_core_vcn", "ocid": "ocid1.vcn.oc2..vcnexample", "display_name": "shared", "attributes": {"subnet_id": nested_ocid}, "evidence": {"request": f"get {nested_ocid}"}}],
            "relationships": [{"source": nested_ocid, "target": "ocid1.vcn.oc2..vcnexample"}],
            "collection_manifest": {"input_files": [], "planned_commands": [{"command": f"oci network subnet get --subnet-id {nested_ocid}"}], "residual_gaps": []},
        }
        exact = normalize(raw, redacted=False)
        safe = normalize(raw, redacted=True)
        self.assertEqual(exact["snapshot_id"], safe["snapshot_id"])
        self.assertNotIn("ocid1.", json.dumps(safe))
        self.assertIn("sha256:", json.dumps(safe))
        self.assertEqual(validate_snapshot(exact), [])
        self.assertEqual(validate_snapshot(safe), [])
        safe["relationships"].append({"source": nested_ocid})
        self.assertTrue(any("unredacted OCID" in error for error in validate_snapshot(safe)))

    def test_snapshot_compare_reports_changes(self):
        base = normalize({"metadata": {"generated_at": "2026-08-20T00:00:00Z"}, "resources": []}, redacted=True)
        newer = normalize({"metadata": {"generated_at": "2026-08-21T00:00:00Z"}, "resources": [{"oci_type": "oci_core_vcn", "ocid": "ocid1.vcn.oc1..vcnexample", "display_name": "new"}]}, redacted=True)
        diff = compare(base, newer)
        self.assertEqual(len(diff["added"]), 1)
        self.assertEqual(diff["removed"], [])


if __name__ == "__main__":
    unittest.main()
