resource "oci_core_vcn" "this" {
  for_each = { for key, vcn in var.vcns : key => vcn if contains(["create", "existing-managed"], vcn.mode) }

  compartment_id = var.network_compartment_ocid
  display_name   = each.value.display_name
  cidr_blocks    = each.value.cidr_blocks
  dns_label      = each.value.dns_label != "" ? each.value.dns_label : null

  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_subnet" "this" {
  for_each = { for key, subnet in var.subnets : key => subnet if contains(["create", "existing-managed"], subnet.mode) }

  compartment_id             = var.network_compartment_ocid
  vcn_id                     = each.value.vcn_ocid != "" ? each.value.vcn_ocid : oci_core_vcn.this[each.value.vcn_key].id
  display_name               = each.value.display_name
  cidr_block                 = each.value.cidr_block
  prohibit_public_ip_on_vnic = each.value.prohibit_public_ip_on_vnic

  lifecycle {
    prevent_destroy = true
  }
}

check "network_resource_modes" {
  assert {
    condition = alltrue(concat(
      [for item in values(var.vcns) : contains(["existing-managed", "observe-only", "create", "external-saas"], item.mode)],
      [for item in values(var.subnets) : contains(["existing-managed", "observe-only", "create", "external-saas"], item.mode)]
    ))
    error_message = "Network modes must be existing-managed, observe-only, create, or external-saas. Move mode requires a separate migration workflow."
  }
}

check "existing_network_objects_have_ocids" {
  assert {
    condition = alltrue(concat(
      [for item in values(var.vcns) : item.mode == "create" || item.mode == "external-saas" || item.existing_ocid != ""],
      [for item in values(var.subnets) : item.mode == "create" || item.mode == "external-saas" || item.existing_ocid != ""]
    ))
    error_message = "Every non-create network object requires an exact existing_ocid."
  }
}

check "subnet_vcn_references" {
  assert {
    condition     = alltrue([for item in values(var.subnets) : contains(keys(var.vcns), item.vcn_key)])
    error_message = "Every subnet must reference a VCN key present in this stage input."
  }
  assert {
    condition = alltrue([
      for item in values(var.subnets) :
      !contains(["create", "existing-managed"], item.mode) ||
      contains(["create", "existing-managed"], try(var.vcns[item.vcn_key].mode, "")) ||
      item.vcn_ocid != ""
    ])
    error_message = "A managed subnet that references an unmanaged VCN requires the exact vcn_ocid."
  }
}
