output "security_zone_ocids" { value = { for key, zone in oci_cloud_guard_security_zone.this : key => zone.id } }
output "vault_ocids" { value = { for key, vault in oci_kms_vault.this : key => vault.id } }
