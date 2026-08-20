# Brownfield adoption runbook

This repository is intentionally inventory-first. Do not point a stage at a live tenancy until the target region, compartment OCIDs, resource modes, and move allowlist have been reviewed.

## Read-only inventory categories

Collect JSON from the target tenancy with a read-only OCI CLI profile. At minimum, capture:

- Tenancy, home/target region, identity domains, compartments, groups, policies, tags, budgets, and events.
- VCNs, subnets, route tables, security lists, NSGs, gateways, DRGs, load balancers, and Bastions.
- Vault and key metadata, bucket metadata, log groups, Service Connector Hub, Cloud Guard, Security Zones, vulnerability scanning, alarms, topics, and subscriptions.
- Fusion environment families/environments and Oracle Integration instances.
- CCS and Hyperion/EPM identifiers and product classification only.

Do not export secret values, API keys, PEM files, OCI config files, passwords, session tokens, OIC connections, OIC flows, or application payloads.

The exact OCIDs used for import may stay in `inventory/oci-inventory.local.json`, which is ignored by Git. Use a redacted copy for review or chat.

## Validate and generate imports

```bash
python3 scripts/validate_inventory.py inventory/oci-inventory.local.json
python3 scripts/generate_import_manifest.py
```

Review `inventory/generated/import-manifest.txt` line by line. The generator only emits imports for `existing-managed` and `move-allowlisted` records.

## Stage validation

```bash
terraform fmt -check -recursive

for stage in 00-bootstrap 01-governance-iam 02-network 03-security-observability 04-workloads; do
  terraform -chdir="stages/$stage" init -backend=false -input=false
  terraform -chdir="stages/$stage" validate
done
```

After bootstrap creates or adopts the state bucket, initialize stages 01–04 with their ignored `backend.hcl` files. Never put backend credentials in that file; use the existing OCI config profile or supported environment authentication.

## Change gates

The first live plan must be reviewed for:

- Any destroy or replacement.
- Any CIDR, DNS label, subnet, gateway, NSG, or route-table replacement.
- Any compartment parent change not listed in the move allowlist.
- Any SaaS/PaaS application payload or credential entering Terraform state.
- Any resource classified as `observe-only` or `external-saas` appearing as a managed resource.
