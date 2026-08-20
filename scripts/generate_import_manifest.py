#!/usr/bin/env python3
"""Generate a reviewed, human-readable Terraform import manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


RESOURCE_PREFIXES = {
    "compartments": "oci_identity_compartment",
    "groups": "oci_identity_group",
    "policies": "oci_identity_policy",
    "tag_namespaces": "oci_identity_tag_namespace",
    "budgets": "oci_budget_budget",
    "events": "oci_events_rule",
    "vcns": "oci_core_vcn",
    "subnets": "oci_core_subnet",
    "route_tables": "oci_core_route_table",
    "security_lists": "oci_core_security_list",
    "network_security_groups": "oci_core_network_security_group",
    "internet_gateways": "oci_core_internet_gateway",
    "nat_gateways": "oci_core_nat_gateway",
    "service_gateways": "oci_core_service_gateway",
    "drgs": "oci_core_drg",
    "load_balancers": "oci_load_balancer_load_balancer",
    "bastions": "oci_bastion_bastion",
    "vaults": "oci_kms_vault",
    "keys": "oci_kms_key",
    "buckets": "oci_objectstorage_bucket",
    "log_groups": "oci_log_analytics_log_analytics_log_group",
    "service_connectors": "oci_sch_service_connector",
    "security_zones": "oci_cloud_guard_security_zone",
    "alarms": "oci_monitoring_alarm",
    "topics": "oci_ons_notification_topic",
    "notifications": "oci_ons_subscription",
    "fusion_environment_families": "oci_fusion_apps_fusion_environment_family",
    "fusion_environments": "oci_fusion_apps_fusion_environment",
    "integration_instances": "oci_integration_integration_instance",
}


def flatten(document: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    resources: list[tuple[str, dict[str, Any]]] = []
    for label in ("compartments", "groups", "policies", "tag_namespaces", "budgets", "events"):
        resources.extend((label, item) for item in document.get(label, []))
    for label, items in document.get("network", {}).items():
        resources.extend((label, item) for item in items)
    for label, items in document.get("security", {}).items():
        resources.extend((label, item) for item in items)
    for label, items in document.get("workloads", {}).items():
        resources.extend((label, item) for item in items)
    return resources


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=Path("inventory/oci-inventory.local.json"))
    parser.add_argument("--output", type=Path, default=Path("inventory/generated/import-manifest.txt"))
    args = parser.parse_args()

    document = json.loads(args.inventory.read_text(encoding="utf-8"))
    lines = [
        "# Generated import manifest. Review every line before execution.",
        "# This file contains resource addresses and OCIDs; do not commit it.",
        "",
    ]
    for label, item in flatten(document):
        if item.get("mode") not in {"existing-managed", "move-allowlisted"}:
            continue
        resource_type = RESOURCE_PREFIXES.get(label)
        key = item.get("terraform_key") or item.get("key") or item.get("name") or item.get("display_name")
        if not resource_type or not key or not item.get("ocid"):
            lines.append(f"# REVIEW: incomplete import record for {label}: {json.dumps(item, sort_keys=True)}")
            continue
        lines.append(f'terraform import \'{resource_type}.this["{key}"]\' {item["ocid"]}')

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
