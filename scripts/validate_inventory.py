#!/usr/bin/env python3
"""Validate local OCI inventory JSON before audit or import generation."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

MODES = {"existing-managed", "observe-only", "create", "external-saas", "move-allowlisted"}
MANAGED_MODES = {"existing-managed", "create"}
OCID_RE = re.compile(r"^ocid1\.([a-z0-9_-]+)\.(oc[0-9]+)\.[a-z0-9_.-]+$")
SECRET_KEY_RE = re.compile(r"(?:password|passwd|private[_-]?key|pem|api[_-]?key|secret|token|credential|authorization|bearer|client[_-]?secret)", re.I)
SECRET_CONTENT_RE = re.compile(r"(?:BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|authorization:\s*bearer\s+\S+|ocid1\.user\.[^\s,]+:[^\s,]+)", re.I)

EXPECTED_OCID_TYPES: dict[str, set[str]] = {
    "tenancy": {"tenancy"}, "compartments": {"compartment"}, "groups": {"group"},
    "policies": {"policy"}, "tag_namespaces": {"tagnamespace"}, "budgets": {"budget"},
    "events": {"rule"}, "vcns": {"vcn"}, "subnets": {"subnet"}, "route_tables": {"routetable"},
    "security_lists": {"securitylist"}, "network_security_groups": {"networksecuritygroup"},
    "internet_gateways": {"internetgateway"}, "nat_gateways": {"natgateway"},
    "service_gateways": {"servicegateway"}, "drgs": {"drg"}, "load_balancers": {"loadbalancer"},
    "bastions": {"bastion"}, "vaults": {"vault"}, "keys": {"key"}, "buckets": {"bucket"},
    "log_groups": {"loggroup", "loganalyticsloggroup"}, "service_connectors": {"serviceconnector"},
    "cloud_guard": {"cloudguardtarget", "cloudguardconfiguration"}, "security_zones": {"securityzone"},
    "vulnerability_scanning": {"hostscanrecipe", "hostscan_target", "hostscanresult"},
    "alarms": {"alarm"}, "topics": {"onstopic", "notificationtopic"},
    "notifications": {"onssubscription", "subscription"},
    "fusion_environment_families": {"fusionenvironmentfamily"}, "fusion_environments": {"fusionenvironment"},
    "integration_instances": {"integrationinstance"}, "ccs": set(), "hyperion_epm": set(),
}
RESOURCE_LISTS = ("compartments", "groups", "policies", "tag_namespaces", "budgets", "events")
NETWORK_LISTS = ("vcns", "subnets", "route_tables", "security_lists", "network_security_groups", "internet_gateways", "nat_gateways", "service_gateways", "drgs", "load_balancers", "bastions")
SECURITY_LISTS = ("vaults", "keys", "buckets", "log_groups", "service_connectors", "cloud_guard", "security_zones", "vulnerability_scanning", "alarms", "topics", "notifications")
WORKLOAD_LISTS = ("fusion_environment_families", "fusion_environments", "integration_instances", "ccs", "hyperion_epm")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def ocid_parts(value: str) -> tuple[str, str] | None:
    match = OCID_RE.match(value)
    return (match.group(1), match.group(2)) if match else None


def walk_for_secrets(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                fail(errors, f"non-string object key is not allowed: {path}")
                continue
            if SECRET_KEY_RE.search(key):
                fail(errors, f"secret-bearing field is not allowed: {path}.{key}")
            walk_for_secrets(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_for_secrets(child, f"{path}[{index}]", errors)
    elif isinstance(value, str) and SECRET_CONTENT_RE.search(value):
        fail(errors, f"secret-bearing content is not allowed: {path}")


def _identity(item: dict[str, Any]) -> str | None:
    for field in ("key", "name", "display_name", "resource_key"):
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _validate_ocid(item: dict[str, Any], path: str, label: str, mode: str, errors: list[str]) -> str | None:
    needs_ocid = mode in {"existing-managed", "observe-only", "move-allowlisted"}
    value = item.get("ocid")
    if not needs_ocid and value in (None, ""):
        return None
    if not isinstance(value, str) or not OCID_RE.match(value):
        fail(errors, f"{path}.ocid is required and must be an OCI OCID for mode={mode}")
        return None
    expected = EXPECTED_OCID_TYPES.get(label, set())
    actual = ocid_parts(value)[0] if ocid_parts(value) else ""
    if expected and actual not in expected:
        fail(errors, f"{path}.ocid has type {actual!r}; expected one of {sorted(expected)} for {label}")
    return value


def validate_resource_list(items: Any, label: str, errors: list[str], identities: dict[str, str], ocids: dict[str, str], move_keys: set[str]) -> None:
    if not isinstance(items, list):
        fail(errors, f"{label} must be a list")
        return
    local_keys: set[str] = set()
    for index, item in enumerate(items):
        path = f"{label}[{index}]"
        if not isinstance(item, dict):
            fail(errors, f"{path} must be an object")
            continue
        key = _identity(item)
        if key is None:
            fail(errors, f"{path} requires a non-empty key, name, display_name, or resource_key")
            continue
        if key in local_keys:
            fail(errors, f"duplicate resource identity in {label}: {key}")
        local_keys.add(key)
        identity = f"{label}:{key}"
        if identity in identities:
            fail(errors, f"duplicate resource identity globally: {identity}")
        identities[identity] = path
        mode = item.get("mode")
        if mode not in MODES:
            fail(errors, f"{path}.mode must be one of {sorted(MODES)}")
            continue
        if label == "groups" and item.get("group_type") not in {"classic", "identity-domain"}:
            fail(errors, f"{path}.group_type must explicitly be classic or identity-domain")
        ocid = _validate_ocid(item, path, label.split(".")[-1], mode, errors)
        if ocid:
            if ocid in ocids:
                fail(errors, f"duplicate OCID globally: {ocid} ({ocids[ocid]} and {path})")
            ocids[ocid] = path
        if mode == "move-allowlisted":
            move_keys.add(identity)
        if mode == "external-saas" and ocid:
            fail(errors, f"{path}.ocid must be omitted for external-saas classification")
        if label == "groups" and item.get("group_type") == "identity-domain" and mode in {"existing-managed", "move-allowlisted"}:
            import_id = item.get("import_id")
            if not isinstance(import_id, str) or not re.match(r"^idcsEndpoint/.+/groups/[^/]+$", import_id):
                fail(errors, f"{path}.import_id must use idcsEndpoint/{{idcsEndpoint}}/groups/{{groupId}} for an existing identity-domain group")


def _node_at(document: dict[str, Any], path: str) -> Any:
    node: Any = document
    for component in path.split("."):
        if "[" in component:
            key, index = component[:-1].split("[")
            node = node[key][int(index)]
        else:
            node = node[component]
    return node


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
        if isinstance(tenancy.get("ocid"), str):
            _validate_ocid(tenancy, "tenancy", "tenancy", "existing-managed", errors)
    identities: dict[str, str] = {}
    ocids: dict[str, str] = {}
    move_resource_keys: set[str] = set()
    for label in RESOURCE_LISTS:
        validate_resource_list(document.get(label), label, errors, identities, ocids, move_resource_keys)
    for group, labels in (("network", NETWORK_LISTS), ("security", SECURITY_LISTS), ("workloads", WORKLOAD_LISTS)):
        value = document.get(group)
        if not isinstance(value, dict):
            fail(errors, f"{group} must be an object")
            continue
        for label in labels:
            validate_resource_list(value.get(label), f"{group}.{label}", errors, identities, ocids, move_resource_keys)
    moves = document.get("move_allowlist")
    move_records: dict[str, dict[str, Any]] = {}
    if not isinstance(moves, list):
        fail(errors, "move_allowlist must be a list")
    else:
        for index, move in enumerate(moves):
            path = f"move_allowlist[{index}]"
            if not isinstance(move, dict):
                fail(errors, f"{path} must be an object")
                continue
            key = move.get("resource_key")
            if not isinstance(key, str) or not key.strip():
                fail(errors, f"{path}.resource_key is required")
                continue
            if key in move_records:
                fail(errors, f"duplicate move allowlist entry: {key}")
            move_records[key] = move
            for field in ("from_parent_ocid", "to_parent_ocid"):
                value = move.get(field)
                if not isinstance(value, str) or not OCID_RE.match(value):
                    fail(errors, f"{path}.{field} must be an OCI OCID")
                elif ocid_parts(value)[0] != "compartment":
                    fail(errors, f"{path}.{field} must be a compartment OCID")
    for identity in sorted(move_resource_keys):
        short_key = identity.split(":", 1)[1]
        if short_key not in move_records and identity not in move_records:
            fail(errors, f"move-allowlisted resource requires an exact move_allowlist record: {identity}")
    for key in move_records:
        if not any(identity == key or identity.endswith(f":{key}") for identity in move_resource_keys):
            fail(errors, f"move_allowlist references a resource that is not move-allowlisted: {key}")
    compartment_keys = {identity.split(":", 1)[1] for identity in identities if identity.startswith("compartments:")}
    vcn_keys = {identity.split(":", 1)[1] for identity in identities if identity.startswith("network.vcns:")}
    known_ocids = set(ocids)
    for _, path in identities.items():
        node = _node_at(document, path)
        if not isinstance(node, dict):
            continue
        reference_sets = {
            "parent_key": {"root", "tenancy"} | compartment_keys,
            "compartment_key": compartment_keys,
            "vcn_key": vcn_keys,
        }
        for field, allowed_keys in reference_sets.items():
            ref = node.get(field)
            if ref and ref not in allowed_keys:
                fail(errors, f"{path}.{field} references an unresolved inventory key: {ref}")
        parent_ocid = node.get("parent_ocid")
        if parent_ocid and parent_ocid not in known_ocids and parent_ocid != tenancy.get("ocid"):
            fail(errors, f"{path}.parent_ocid is not present in the inventory: {parent_ocid}")
    security = document.get("security")
    if isinstance(security, dict):
        zones = security.get("security_zones", [])
        if isinstance(zones, list) and any(isinstance(x, dict) and x.get("mode") in MANAGED_MODES for x in zones):
            for flag in ("security_zone_enabled", "cloud_guard_enabled", "security_zone_acknowledged"):
                if document.get(flag) is not True:
                    fail(errors, f"{flag} must be true before managing Security Zones")
    walk_for_secrets(document, "$", errors)
    return sorted(set(errors))


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
