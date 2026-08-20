output "identity_domain_ocid" { value = data.oci_identity_domain.this.id }
output "group_ocids" { value = { for key, group in oci_identity_group.this : key => group.id } }
output "policy_ocids" { value = { for key, policy in oci_identity_policy.this : key => policy.id } }
output "tag_namespace_ocids" { value = { for key, namespace in oci_identity_tag_namespace.this : key => namespace.id } }
