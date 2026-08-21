#!/usr/bin/env python3
"""Print a read-only OCI export plan; it never executes these commands."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SERVICES = {
    "identity-governance": [
        "oci iam compartment list --compartment-id <TENANCY_OCID> --compartment-id-in-subtree true --access-level ACCESSIBLE --all",
        "oci iam domain list --compartment-id <TENANCY_OCID> --all",
        "oci iam group list --compartment-id <TENANCY_OCID> --all",
        "oci identity-domains groups list --endpoint <IDENTITY_DOMAIN_URL> --all",
        "oci iam policy list --compartment-id <TENANCY_OCID> --all",
        "oci iam tag-namespace list --compartment-id <TENANCY_OCID> --all",
        "oci budgets budget list --compartment-id <TENANCY_OCID> --all",
        "oci events rule list --compartment-id <COMPARTMENT_OCID> --all",
    ],
    "network": [
        "oci network vcn list --compartment-id <COMPARTMENT_OCID> --all",
        "oci network subnet list --compartment-id <COMPARTMENT_OCID> --all",
        "oci network route-table list --compartment-id <COMPARTMENT_OCID> --all",
        "oci network security-list list --compartment-id <COMPARTMENT_OCID> --all",
        "oci network nsg list --compartment-id <COMPARTMENT_OCID> --all",
        "oci network internet-gateway list --compartment-id <COMPARTMENT_OCID> --all",
        "oci network nat-gateway list --compartment-id <COMPARTMENT_OCID> --all",
        "oci network service-gateway list --compartment-id <COMPARTMENT_OCID> --all",
        "oci network drg list --compartment-id <COMPARTMENT_OCID> --all",
        "oci lb load-balancer list --compartment-id <COMPARTMENT_OCID> --all",
        "oci bastion bastion list --compartment-id <COMPARTMENT_OCID> --all",
    ],
    "security-observability": [
        "oci kms management vault list --compartment-id <COMPARTMENT_OCID> --all",
        "oci kms management key list --compartment-id <COMPARTMENT_OCID> --endpoint <VAULT_MANAGEMENT_ENDPOINT> --all",
        "oci os bucket list --compartment-id <COMPARTMENT_OCID> --namespace-name <OBJECT_STORAGE_NAMESPACE> --all",
        "oci logging log-group list --compartment-id <COMPARTMENT_OCID> --all",
        "oci sch service-connector list --compartment-id <COMPARTMENT_OCID> --all",
        "oci cloud-guard target list --compartment-id <TENANCY_OCID> --all",
        "oci cloud-guard security-zone list --compartment-id <COMPARTMENT_OCID> --all",
        "oci vulnerability-scanning host scan target list --compartment-id <COMPARTMENT_OCID> --all",
        "oci monitoring alarm list --compartment-id <COMPARTMENT_OCID> --all",
        "oci ons topic list --compartment-id <COMPARTMENT_OCID> --all",
        "oci ons subscription list --compartment-id <COMPARTMENT_OCID> --all",
    ],
    "workloads": [
        "oci integration integration-instance list --compartment-id <COMPARTMENT_OCID> --all",
        "oci fusion-apps fusion-environment-family list --compartment-id <COMPARTMENT_OCID> --all",
        "oci fusion-apps fusion-environment list --compartment-id <COMPARTMENT_OCID> --all",
    ],
}


def plan(region: str | None = None) -> dict:
    commands = []
    sequence = 0
    for service, service_commands in SERVICES.items():
        for command in service_commands:
            sequence += 1
            commands.append({"service": service, "command": (f"{command} --region {region}" if region else command), "execute": False, "output_file": f"audit/generated/raw/{sequence:02d}-{service}.json", "expected_output": "OCI CLI JSON to be wrapped in the sanitized raw-export contract"})
    return {"schema_version": "oci-export-plan.v1", "read_only": True, "network_access": False, "credentials_required_by_this_tool": False, "commands": commands, "residual_gaps": ["Replace placeholders with exact compartments and region before operator execution.", "Some OCI services require additional list operations or SDK exports.", "Fusion, CCS, and Hyperion/EPM application payloads are intentionally excluded."]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(plan(args.region), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
