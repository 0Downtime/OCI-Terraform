resource "oci_core_vcn" "this" {
  for_each = { for key, vcn in var.vcns : key => vcn if vcn.mode != "observe-only" }

  compartment_id = var.network_compartment_ocid
  display_name   = each.value.display_name
  cidr_blocks    = each.value.cidr_blocks
  dns_label      = each.value.dns_label != "" ? each.value.dns_label : null

  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_subnet" "this" {
  for_each = { for key, subnet in var.subnets : key => subnet if subnet.mode != "observe-only" }

  compartment_id             = var.network_compartment_ocid
  vcn_id                     = oci_core_vcn.this[each.value.vcn_key].id
  display_name               = each.value.display_name
  cidr_block                 = each.value.cidr_block
  prohibit_public_ip_on_vnic = each.value.prohibit_public_ip_on_vnic

  lifecycle {
    prevent_destroy = true
  }
}

check "network_resource_modes" {
  assert {
    condition     = alltrue([for vcn in values(var.vcns) : contains(["existing-managed", "observe-only", "create"], vcn.mode)])
    error_message = "VCN modes must be existing-managed, observe-only, or create."
  }
}

check "existing_network_objects_have_ocids" {
  assert {
    condition = alltrue(concat(
      [for item in values(var.vcns) : item.mode == "create" || item.existing_ocid != ""],
      [for item in values(var.subnets) : item.mode == "create" || item.existing_ocid != ""]
    ))
    error_message = "Every non-create network object requires an exact existing_ocid."
  }
}
