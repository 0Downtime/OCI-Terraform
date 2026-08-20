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
stages/00-bootstrap/                 Local-state bootstrap and state bucket
stages/01-governance-iam/            Groups, policies, tags, and identity references
stages/02-network/                    VCN, gateways, subnets, route tables, and NSGs
stages/03-security-observability/    Security, logging, Vault, events, and notifications
stages/04-workloads/                 OCI Fusion/OIC boundary resources and app compartments
inventory/                            Sanitized schema and local ignored inventory inputs
scripts/                              Inventory validation and import-manifest tooling
tests/                                Offline safety tests
```

## Deployment sequence

1. Obtain a read-only inventory from the target tenancy.
2. Copy `inventory/oci-inventory.example.json` to the ignored `inventory/oci-inventory.local.json` and populate exact OCIDs.
3. Run `python3 scripts/validate_inventory.py inventory/oci-inventory.local.json`.
4. Generate a reviewed import manifest with `python3 scripts/generate_import_manifest.py`.
5. Initialize and validate each stage with backend initialization disabled.
6. Import only the reviewed resources, refresh, and review the saved plan.
7. Apply only after the plan contains no unexpected replacements, destroys, or compartment moves.

The initial repository contains no target OCIDs and no live OCI credentials. No OCI apply is performed by repository validation.

## Terraform versions

- Terraform: `>= 1.12.0, < 2.0.0`
- OCI provider: `= 8.28.0`

The provider lock file is generated after provider initialization in each stage and should be committed once validated.
