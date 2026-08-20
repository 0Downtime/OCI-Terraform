output "vcn_ocids" { value = { for key, vcn in oci_core_vcn.this : key => vcn.id } }
output "subnet_ocids" { value = { for key, subnet in oci_core_subnet.this : key => subnet.id } }
