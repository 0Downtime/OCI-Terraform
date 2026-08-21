# OCI Terraform Brownfield Foundation

Terraform foundation for a single OCI tenancy and region, modeled from the target architecture diagram and designed for guarded brownfield adoption.

## Operating rules

- Inventory first; no creation or move is inferred from a name alone.
- Existing resources require an exact OCID in a local ignored inventory file.
- Initial convergence is non-destructive. Compartments are retained by default and network replacements are rejected unless explicitly approved.
- Compartment reparenting requires an explicit move allowlist and a separately reviewed plan.
- OCI API keys, PEM files, OCI config files, secret values, SaaS credentials, OIC flows, connections, and mappings never belong in this repository.
- Fusion and OIC resources are managed only at the OCI service-instance boundary. SaaS/application payloads remain in their native promotion workflows.

## Repository layout

```text
stages/00-bootstrap/                 Compartments and optional state bucket
stages/01-governance-iam/            Classic IAM/domain groups, policies, tag namespaces
stages/02-network/                   VCNs and subnets only
stages/03-security-observability/   Security Zones (opt-in) and Vaults only
stages/04-workloads/                 OCI Fusion environments and OIC instances only
audit/schema/                        Versioned normalized audit JSON Schema
audit/examples/                      Sanitized synthetic export fixture
inventory/                           Inventory examples and ignored exact-OCID inputs
scripts/                             Offline audit, validation, export planning, and imports
tests/                               Offline safety and audit tests
```

## Deployment sequence

1. Obtain a read-only inventory from the target tenancy.
2. Copy `inventory/oci-inventory.example.json` to the ignored `inventory/oci-inventory.local.json` and populate exact OCIDs.
3. Run `python3 scripts/validate_inventory.py inventory/oci-inventory.local.json`.
4. Generate a read-only command plan with `python3 scripts/plan_oci_exports.py --region <region> --output audit/generated/export-plan.json`; execute commands manually outside this repository and provide sanitized JSON exports.
5. Normalize exports without OCI access: `python3 scripts/oci_audit.py normalize export.json --exact-output audit/snapshots/<id>/exact.local.json --redacted-output audit/snapshots/<id>/snapshot.json --summary-output audit/snapshots/<id>/summary.md`.
6. Generate a stage-specific, reviewed import manifest only after validation: `python3 scripts/generate_import_manifest.py --stage 02-network --output audit/generated/02-network-imports.json --hcl-output stages/02-network/imports.generated.tf`. The ignored HCL file must live inside that stage so Terraform can load it.
7. Initialize and validate each stage with backend initialization disabled.
8. Import only the reviewed resources, refresh, and review the saved plan.
9. Apply only after the plan contains no unexpected replacements, destroys, or compartment moves.

The initial repository contains no target OCIDs and no live OCI credentials. No OCI apply is performed by repository validation.

## Terraform versions

- Terraform: `>= 1.12.0, < 2.0.0`
- OCI provider: `= 8.28.0`

The provider lock file is generated after provider initialization in each stage and should be committed once validated.

## Audit contract

The audit subsystem is independent of Terraform state. `oci_audit.py` produces deterministic `oci-audit.v1` snapshots with metadata, normalized resources, relationships, findings, and a collection manifest. Exact OCIDs are emitted only to ignored local paths; the redacted snapshot retains stable SHA-256 hashes for cross-snapshot comparison. `python3 scripts/oci_audit.py compare before.json after.json` reports additions, removals, and changes.

Validate any re-ingested snapshot without third-party Python dependencies using `python3 scripts/oci_audit.py validate audit/snapshots/<id>/snapshot.json`.

An existing Terraform state bucket remains import-first. Configure `state_bucket_mode = "existing-managed"`, its exact bucket OCID, namespace-derived bucket name, and compartment; then import it at `oci_objectstorage_bucket.terraform_state[0]` using the provider ID `n/{namespaceName}/b/{bucketName}` before planning bootstrap.

The collector boundary is intentionally an export intake and command planner. It does not execute OCI CLI/SDK calls, read OCI profiles, or store credentials. Fusion/OIC application artifacts and unresolved CCS/Hyperion/EPM classification remain residual inventory decisions.
