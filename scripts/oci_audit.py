#!/usr/bin/env python3
"""Offline OCI audit normalization, redaction, rendering, and comparison.

The tool accepts OCI CLI/SDK export JSON supplied by the operator.  It never
loads OCI credentials and never makes network calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SECRET_KEY_RE = re.compile(r"(?:password|passwd|private[_-]?key|pem|api[_-]?key|secret|token|credential|authorization|bearer|client[_-]?secret)", re.I)
OCID_RE = re.compile(r"^ocid1\.[a-z0-9_-]+\.oc[0-9]+\.[a-z0-9_.-]+$")
OCID_VALUE_RE = re.compile(r"ocid1\.[a-z0-9_-]+\.oc[0-9]+\.[a-z0-9_.-]+", re.I)
AUDIT_SCHEMA_VERSION = "oci-audit.v1"
SNAPSHOT_KEYS = {"schema_version", "snapshot_id", "metadata", "resources", "relationships", "findings", "collection_manifest"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _contains_ocid(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_ocid(key) or _contains_ocid(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_ocid(child) for child in value)
    return isinstance(value, str) and OCID_VALUE_RE.search(value) is not None


def validate_snapshot(snapshot: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(snapshot, dict):
        return ["snapshot must be a JSON object"]
    missing = SNAPSHOT_KEYS - set(snapshot)
    extra = set(snapshot) - SNAPSHOT_KEYS
    if missing:
        errors.append(f"snapshot is missing required keys: {sorted(missing)}")
    if extra:
        errors.append(f"snapshot has unsupported keys: {sorted(extra)}")
    if snapshot.get("schema_version") != AUDIT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {AUDIT_SCHEMA_VERSION}")
    if not isinstance(snapshot.get("snapshot_id"), str) or len(snapshot.get("snapshot_id", "")) < 8:
        errors.append("snapshot_id must be a non-empty stable identifier")
    metadata = snapshot.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("metadata must be an object")
        metadata = {}
    for field in ("generated_at", "source", "collector_version", "redaction_profile"):
        if not isinstance(metadata.get(field), str) or not metadata[field]:
            errors.append(f"metadata.{field} is required")
    if metadata.get("redaction_profile") not in {"exact-local", "ai-safe-sha256"}:
        errors.append("metadata.redaction_profile is invalid")
    resources = snapshot.get("resources")
    if not isinstance(resources, list):
        errors.append("resources must be a list")
        resources = []
    required_resource_keys = {"resource_uid", "oci_type", "service", "display_name", "management", "attributes", "evidence"}
    seen_uids: set[str] = set()
    for index, resource in enumerate(resources):
        if not isinstance(resource, dict):
            errors.append(f"resources[{index}] must be an object")
            continue
        absent = required_resource_keys - set(resource)
        if absent:
            errors.append(f"resources[{index}] is missing required keys: {sorted(absent)}")
        uid = resource.get("resource_uid")
        if not isinstance(uid, str) or not uid:
            errors.append(f"resources[{index}].resource_uid is required")
        elif uid in seen_uids:
            errors.append(f"duplicate resource_uid: {uid}")
        else:
            seen_uids.add(uid)
        if not isinstance(resource.get("management"), dict):
            errors.append(f"resources[{index}].management must be an object")
        if not isinstance(resource.get("attributes"), dict):
            errors.append(f"resources[{index}].attributes must be an object")
        if not isinstance(resource.get("evidence"), dict):
            errors.append(f"resources[{index}].evidence must be an object")
    for field in ("relationships", "findings"):
        if not isinstance(snapshot.get(field), list):
            errors.append(f"{field} must be a list")
    manifest = snapshot.get("collection_manifest")
    if not isinstance(manifest, dict):
        errors.append("collection_manifest must be an object")
    else:
        for field in ("input_files", "planned_commands", "residual_gaps"):
            if not isinstance(manifest.get(field), list):
                errors.append(f"collection_manifest.{field} must be a list")
    if metadata.get("redaction_profile") == "ai-safe-sha256" and _contains_ocid(snapshot):
        errors.append("ai-safe-sha256 snapshot contains an unredacted OCID")
    return sorted(set(errors))


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resource_iter(raw: dict[str, Any]) -> Iterable[dict[str, Any]]:
    if isinstance(raw.get("resources"), list):
        yield from (item for item in raw["resources"] if isinstance(item, dict))
        return
    for label in ("compartments", "groups", "policies", "tag_namespaces", "budgets", "events"):
        for item in raw.get(label, []):
            if isinstance(item, dict):
                yield {**item, "category": label}
    for category in ("network", "security", "workloads"):
        for label, items in raw.get(category, {}).items():
            for item in items:
                if isinstance(item, dict):
                    yield {**item, "category": label}


def _redact_value(value: Any, *, redact_ocids: bool = False) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, child in sorted(value.items()):
            if SECRET_KEY_RE.search(str(key)):
                result[key] = "[REDACTED]"
            else:
                result[key] = _redact_value(child, redact_ocids=redact_ocids)
        return result
    if isinstance(value, list):
        return [_redact_value(child, redact_ocids=redact_ocids) for child in value]
    if isinstance(value, str):
        if "BEGIN " in value or re.search(r"bearer\s+\S+", value, re.I):
            return "[REDACTED]"
        if redact_ocids:
            return OCID_VALUE_RE.sub(lambda match: stable_hash(match.group(0)), value)
    return value


def normalize(raw: dict[str, Any], *, source: str = "oci-export", redacted: bool = False) -> dict[str, Any]:
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    generated_at = str(metadata.get("generated_at") or raw.get("generated_at") or now())
    tenancy = metadata.get("tenancy") or raw.get("tenancy") or {}
    tenancy_ocid = tenancy.get("ocid") if isinstance(tenancy, dict) else None
    region = metadata.get("region") or (tenancy.get("target_region") if isinstance(tenancy, dict) else None)
    resources: list[dict[str, Any]] = []
    relationships = raw.get("relationships", []) if isinstance(raw.get("relationships"), list) else []
    for source_resource in _resource_iter(raw):
        item = source_resource
        ocid = item.get("ocid") if isinstance(item.get("ocid"), str) else None
        resource_type = str(item.get("oci_type") or item.get("resource_type") or item.get("type") or item.get("category") or "unknown")
        display_name = str(item.get("display_name") or item.get("name") or item.get("key") or "")
        if redacted:
            display_name = _redact_value(display_name, redact_ocids=True)
        uid_basis = f"{resource_type}|{ocid or item.get('key') or display_name}"
        record = {
            "resource_uid": stable_hash(uid_basis),
            "oci_type": resource_type,
            "service": str(item.get("service") or resource_type.split("_")[1] if resource_type.startswith("oci_") and len(resource_type.split("_")) > 1 else item.get("service") or "unknown"),
            "display_name": display_name,
            "region": item.get("region") or region,
            "compartment_ocid_hash": stable_hash(item["compartment_ocid"]) if isinstance(item.get("compartment_ocid"), str) else None,
            "lifecycle_state": item.get("lifecycle_state"),
            "management": {
                "observed_mode": item.get("mode") or "unclassified",
                "proposed_mode": item.get("proposed_mode") or item.get("mode") or "unclassified",
                "confidence": item.get("confidence") or "unknown",
            },
            "attributes": _redact_value(item.get("attributes") or {k: v for k, v in item.items() if k not in {"ocid", "compartment_ocid", "resource_uid", "oci_type", "resource_type", "type", "service", "display_name", "name", "key", "mode", "proposed_mode", "confidence", "lifecycle_state", "region"}}, redact_ocids=redacted),
            "evidence": _redact_value(item.get("evidence") or {"source": source}, redact_ocids=redacted),
        }
        if not redacted and isinstance(item.get("compartment_ocid"), str):
            record["compartment_ocid"] = item["compartment_ocid"]
        if ocid and OCID_RE.match(ocid):
            record["ocid_hash"] = stable_hash(ocid)
            if not redacted:
                record["ocid"] = ocid
        resources.append(record)
    normalized_relationships = []
    for relationship in relationships:
        if not isinstance(relationship, dict):
            continue
        normalized_relationships.append(_redact_value(relationship, redact_ocids=redacted))
    findings = raw.get("findings", []) if isinstance(raw.get("findings"), list) else []
    snapshot = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "snapshot_id": str(metadata.get("snapshot_id") or stable_hash(generated_at + canonical(sorted(resource["resource_uid"] for resource in resources)))[:23]),
        "metadata": {
            "generated_at": generated_at,
            "source": source,
            "collector_version": str(metadata.get("collector_version") or "offline-intake-1"),
            "region": region,
            "tenancy_ocid_hash": stable_hash(tenancy_ocid) if isinstance(tenancy_ocid, str) else metadata.get("tenancy_ocid_hash"),
            "redaction_profile": "exact-local" if not redacted else "ai-safe-sha256",
        },
        "resources": sorted(resources, key=lambda x: (x["oci_type"], x["resource_uid"])),
        "relationships": sorted(normalized_relationships, key=canonical),
        "findings": sorted((_redact_value(x, redact_ocids=redacted) for x in findings if isinstance(x, dict)), key=canonical),
        "collection_manifest": _redact_value(raw.get("collection_manifest") or {"input_files": [], "planned_commands": [], "residual_gaps": ["No live OCI collection was performed."]}, redact_ocids=redacted),
    }
    errors = validate_snapshot(snapshot)
    if errors:
        raise ValueError("normalized snapshot failed validation: " + "; ".join(errors))
    return snapshot


def write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def summary(snapshot: dict[str, Any]) -> str:
    counts: dict[str, int] = {}
    modes: dict[str, int] = {}
    for resource in snapshot.get("resources", []):
        counts[resource["oci_type"]] = counts.get(resource["oci_type"], 0) + 1
        mode = resource.get("management", {}).get("proposed_mode", "unclassified")
        modes[mode] = modes.get(mode, 0) + 1
    lines = [
        "# OCI Audit Summary", "", f"- Schema: `{snapshot.get('schema_version')}`", f"- Snapshot: `{snapshot.get('snapshot_id')}`",
        f"- Generated: `{snapshot.get('metadata', {}).get('generated_at')}`", f"- Region: `{snapshot.get('metadata', {}).get('region') or 'unknown'}`", "",
        "## Management classification", "", "| Mode | Count |", "| --- | ---: |",
    ]
    lines.extend(f"| `{mode}` | {count} |" for mode, count in sorted(modes.items()))
    lines.extend(["", "## Resource counts", "", "| OCI type | Count |", "| --- | ---: |"])
    lines.extend(f"| `{kind}` | {count} |" for kind, count in sorted(counts.items()))
    lines.extend(["", "## Findings", "", f"{len(snapshot.get('findings', []))} finding(s) recorded.", ""])
    for finding in snapshot.get("findings", []):
        lines.append(f"- **{finding.get('severity', 'unknown')}** `{finding.get('rule_id', 'unclassified')}`: {finding.get('message', 'No message')}")
    gaps = snapshot.get("collection_manifest", {}).get("residual_gaps", [])
    lines.extend(["", "## Residual gaps", ""])
    lines.extend(f"- {gap}" for gap in gaps)
    return "\n".join(lines) + "\n"


def compare(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_by_uid = {x["resource_uid"]: x for x in left.get("resources", [])}
    right_by_uid = {x["resource_uid"]: x for x in right.get("resources", [])}
    added = sorted(set(right_by_uid) - set(left_by_uid))
    removed = sorted(set(left_by_uid) - set(right_by_uid))
    changed = []
    for uid in sorted(set(left_by_uid) & set(right_by_uid)):
        if canonical(left_by_uid[uid]) != canonical(right_by_uid[uid]):
            changed.append({"resource_uid": uid, "before": left_by_uid[uid], "after": right_by_uid[uid]})
    return {"schema_version": "oci-audit-diff.v1", "from_snapshot": left.get("snapshot_id"), "to_snapshot": right.get("snapshot_id"), "added": added, "removed": removed, "changed": changed, "finding_delta": len(right.get("findings", [])) - len(left.get("findings", []))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    norm = sub.add_parser("normalize")
    norm.add_argument("input", type=Path)
    norm.add_argument("--exact-output", type=Path)
    norm.add_argument("--redacted-output", type=Path)
    norm.add_argument("--summary-output", type=Path)
    norm.add_argument("--source", default="oci-export")
    diff = sub.add_parser("compare")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    diff.add_argument("--output", type=Path)
    check = sub.add_parser("validate")
    check.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "normalize":
            raw = json.loads(args.input.read_text(encoding="utf-8"))
            exact = normalize(raw, source=args.source, redacted=False)
            safe = normalize(raw, source=args.source, redacted=True)
            if args.exact_output:
                write_json(args.exact_output, exact)
            if args.redacted_output:
                write_json(args.redacted_output, safe)
            if args.summary_output:
                args.summary_output.parent.mkdir(parents=True, exist_ok=True)
                args.summary_output.write_text(summary(safe), encoding="utf-8")
        elif args.command == "compare":
            before = json.loads(args.before.read_text())
            after = json.loads(args.after.read_text())
            errors = validate_snapshot(before) + validate_snapshot(after)
            if errors:
                raise ValueError("snapshot validation failed: " + "; ".join(sorted(set(errors))))
            result = compare(before, after)
            if args.output:
                write_json(args.output, result)
            else:
                print(json.dumps(result, sort_keys=True, indent=2))
        else:
            errors = validate_snapshot(json.loads(args.input.read_text(encoding="utf-8")))
            if errors:
                raise ValueError("snapshot validation failed: " + "; ".join(errors))
            print(f"validated OCI audit snapshot: {args.input}")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"audit operation failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
