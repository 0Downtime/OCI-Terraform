output "foundation_compartment_ids" {
  description = "Managed foundation compartment OCIDs."
  value       = { for key, compartment in oci_identity_compartment.this : key => compartment.id }
}

output "terraform_state_bucket_name" {
  description = "State bucket name after bootstrap."
  value       = try(oci_objectstorage_bucket.terraform_state[0].name, null)
}

output "terraform_state_bucket_namespace" {
  description = "Object Storage namespace used by the OCI backend."
  value       = data.oci_objectstorage_namespace.this.namespace
}
