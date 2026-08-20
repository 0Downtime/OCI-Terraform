# OCI inventory intake

Use a read-only OCI CLI or console export to populate a local ignored file named `oci-inventory.local.json`.

The tracked example is a schema and naming guide only. Exact OCIDs may remain in the local file for import mapping, but do not include:

- OCI API keys, private keys, PEM files, OCI config files, or session tokens.
- Secret values, passwords, OIC credentials, connection secrets, or SaaS administrator credentials.
- OIC flows, mappings, integrations, or application payload exports.

The inventory must classify each item as one of:

`existing-managed`, `observe-only`, `create`, `external-saas`, or `move-allowlisted`.

Existing and move-allowlisted items require exact OCIDs. A compartment parent change also requires a matching `move_allowlist` entry with both the current and desired parent OCIDs.
