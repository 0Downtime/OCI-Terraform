#!/usr/bin/env python3
"""Generate stage-scoped Terraform import blocks from a validated inventory."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_inventory import validate_inventory  # noqa: E402

STAGES = {
    "00-bootstrap": {"compartments": "oci_identity_compartment.this", "state_bucket": "oci_objectstorage_bucket.terraform_state"},
    "01-governance-iam": {"groups": "oci_identity_group.this", "policies": "oci_identity_policy.this", "tag_namespaces": "oci_identity_tag_namespace.this"},
    "02-network": {"vcns": "oci_core_vcn.this", "subnets": "oci_core_subnet.this"},
    "03-security-observability": {"security_zones": "oci_cloud_guard_security_zone.this", "vaults": "oci_kms_vault.this"},
    "04-workloads": {"integration_instances": "oci_integration_integration_instance.this", "fusion_environments": "oci_fusion_apps_fusion_environment.this"},
}
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ROOT_LABELS = {"compartments", "groups", "policies", "tag_namespaces", "budgets", "events"}


def flatten(document: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    result = []
    for label in ROOT_LABELS:
        result.extend((label, item) for item in document.get(label, []))
    for parent in ("network", "security", "workloads"):
        for label, items in document.get(parent, {}).items():
            result.extend((label, item) for item in items)
    return result


def hcl_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def generate(document: dict[str, Any], stage: str) -> dict[str, Any]:
    errors = validate_inventory(document)
    if errors:
        raise ValueError("inventory validation failed: " + "; ".join(errors))
    if stage not in STAGES:
        raise ValueError(f"unknown stage: {stage}")
    entries = []
    for label, item in sorted(flatten(document), key=lambda pair: (pair[0], str(pair[1].get("key") or pair[1].get("name") or pair[1].get("display_name")))):
        if item.get("mode") not in {"existing-managed", "move-allowlisted"}:
            continue
        address_base = STAGES[stage].get(label)
        if label == "groups" and item.get("group_type", "classic") == "identity-domain":
            address_base = "oci_identity_domains_group.this"
        if not address_base:
            continue
        key = item.get("terraform_key") or item.get("key") or item.get("name") or item.get("display_name")
        if not isinstance(key, str) or not item.get("ocid"):
            raise ValueError(f"incomplete import record for {label}: {key!r}")
        import_id = item["ocid"]
        if label == "groups" and item.get("group_type", "classic") == "identity-domain":
            import_id = item["import_id"]
        entries.append({"category": label, "key": key, "address": f'{address_base}[{json.dumps(key)}]', "id": import_id, "ocid": item["ocid"], "mode": item["mode"], "stage": stage})
    return {"schema_version": "oci-import-manifest.v2", "stage": stage, "terraform_directory": f"stages/{stage}", "imports": entries}


def render_hcl(manifest: dict[str, Any]) -> str:
    lines = ["# Generated offline. Review the plan and run from the stage directory.", "# No import is executed by this file.", ""]
    for entry in manifest["imports"]:
        lines.extend(["import {", f"  to = {entry['address']}", f"  id = {hcl_string(entry['id'])}", "}", ""])
    return "\n".join(lines)


def validate_hcl_output_path(path: Path, stage: str) -> None:
    stage_directory = (REPOSITORY_ROOT / "stages" / stage).resolve()
    resolved = path.resolve()
    if resolved.parent != stage_directory:
        raise ValueError(f"generated import blocks must be written directly into {stage_directory}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=Path("inventory/oci-inventory.local.json"))
    parser.add_argument("--stage", required=True, choices=sorted(STAGES))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hcl-output", type=Path)
    args = parser.parse_args()
    try:
        document = json.loads(args.inventory.read_text(encoding="utf-8"))
        manifest = generate(document, args.stage)
        if args.hcl_output:
            validate_hcl_output_path(args.hcl_output, args.stage)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"import manifest generation failed: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.hcl_output:
        args.hcl_output.parent.mkdir(parents=True, exist_ok=True)
        args.hcl_output.write_text(render_hcl(manifest), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
