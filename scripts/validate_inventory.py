#!/usr/bin/env python3
"""Validate a local OCI inventory before Terraform import generation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MODES = {"existing-managed", "observe-only", "create", "external-saas", "move-allowlisted"}
OCID_RE = re.compile(r"^ocid1\.[a-z0-9_-]+\.[a-z0-9-]+\.[a-z0-9_.-]+$")
SECRET_TERMS = {
    "password",
    "private_key",
    "private_key_pem",
    "api_key",
    "secret_key",
    "secret_value",
    "token",
    "access_token",
    "client_secret",
    "connection_password",
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def walk_for_secrets(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.lower().replace("-", "_")
            if normalized in SECRET_TERMS or any(term in normalized for term in ("password", "private_key", "secret_value", "access_token")):
                fail(errors, f"secret-bearing field is not allowed: {path}.{key}")
            walk_for_secrets(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_for_secrets(child, f"{path}[{index}]", errors)


def validate_resource_list(items: Any, label: str, errors: list[str]) -> None:
    if not isinstance(items, list):
        fail(errors, f"{label} must be a list")
        return

    keys: set[str] = set()
    ocids: set[str] = set()
    for index, item in enumerate(items):
        path = f"{label}[{index}]"
        if not isinstance(item, dict):
            fail(errors, f"{path} must be an object")
            continue
        key = item.get("key") or item.get("name") or item.get("display_name")
        if not isinstance(key, str) or not key.strip():
            fail(errors, f"{path} requires a non-empty key, name, or display_name")
        elif key in keys:
            fail(errors, f"duplicate resource identity in {label}: {key}")
        else:
            keys.add(key)

        mode = item.get("mode")
        if mode not in MODES:
            fail(errors, f"{path}.mode must be one of {sorted(MODES)}")
        if mode in {"existing-managed", "observe-only", "move-allowlisted"}:
            ocid = item.get("ocid")
            if not isinstance(ocid, str) or not OCID_RE.match(ocid):
                fail(errors, f"{path}.ocid is required and must be an OCI OCID for mode={mode}")
            elif ocid in ocids:
                fail(errors, f"duplicate OCID in {label}: {ocid}")
            else:
                ocids.add(ocid)


def validate_inventory(document: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(document, dict):
        return ["inventory must be a JSON object"]
    if document.get("schema_version") != 1:
        fail(errors, "schema_version must be 1")

    tenancy = document.get("tenancy")
    if not isinstance(tenancy, dict):
        fail(errors, "tenancy must be an object")
    else:
        for field in ("ocid", "home_region", "target_region"):
            if not isinstance(tenancy.get(field), str) or not tenancy[field].strip():
                fail(errors, f"tenancy.{field} is required")

    validate_resource_list(document.get("compartments"), "compartments", errors)
    for label in ("groups", "policies", "tag_namespaces", "budgets", "events"):
        validate_resource_list(document.get(label), label, errors)

    network = document.get("network")
    if not isinstance(network, dict):
        fail(errors, "network must be an object")
    else:
        for label in ("vcns", "subnets", "route_tables", "security_lists", "network_security_groups", "internet_gateways", "nat_gateways", "service_gateways", "drgs", "load_balancers", "bastions"):
            validate_resource_list(network.get(label), f"network.{label}", errors)

    security = document.get("security")
    if not isinstance(security, dict):
        fail(errors, "security must be an object")
    else:
        for label in ("vaults", "keys", "buckets", "log_groups", "service_connectors", "cloud_guard", "security_zones", "vulnerability_scanning", "alarms", "topics", "notifications"):
            validate_resource_list(security.get(label), f"security.{label}", errors)

    workloads = document.get("workloads")
    if not isinstance(workloads, dict):
        fail(errors, "workloads must be an object")
    else:
        for label in ("fusion_environment_families", "fusion_environments", "integration_instances", "ccs", "hyperion_epm"):
            validate_resource_list(workloads.get(label), f"workloads.{label}", errors)

    moves = document.get("move_allowlist")
    if not isinstance(moves, list):
        fail(errors, "move_allowlist must be a list")
    else:
        move_keys: set[str] = set()
        for index, move in enumerate(moves):
            path = f"move_allowlist[{index}]"
            if not isinstance(move, dict):
                fail(errors, f"{path} must be an object")
                continue
            move_key = move.get("resource_key")
            if not isinstance(move_key, str) or not move_key.strip():
                fail(errors, f"{path}.resource_key is required")
            elif move_key in move_keys:
                fail(errors, f"duplicate move allowlist entry: {move_key}")
            else:
                move_keys.add(move_key)
            if not isinstance(move.get("from_parent_ocid"), str) or not OCID_RE.match(move["from_parent_ocid"]):
                fail(errors, f"{path}.from_parent_ocid must be an OCI OCID")
            if not isinstance(move.get("to_parent_ocid"), str) or not OCID_RE.match(move["to_parent_ocid"]):
                fail(errors, f"{path}.to_parent_ocid must be an OCI OCID")

    walk_for_secrets(document, "$", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    args = parser.parse_args()
    try:
        document = json.loads(args.inventory.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"inventory read failed: {exc}", file=sys.stderr)
        return 2
    errors = validate_inventory(document)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"validated OCI inventory: {args.inventory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
