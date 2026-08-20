resource "oci_cloud_guard_security_zone" "this" {
  for_each = { for key, zone in var.security_zones : key => zone if zone.mode != "observe-only" }

  compartment_id          = var.security_compartment_ocid
  display_name            = each.value.display_name
  security_zone_recipe_id = each.value.security_zone_recipe_id

  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_kms_vault" "this" {
  for_each = { for key, vault in var.vaults : key => vault if vault.mode != "observe-only" }

  compartment_id = var.security_compartment_ocid
  display_name   = each.value.display_name
  vault_type     = each.value.vault_type

  lifecycle {
    prevent_destroy = true
  }
}

check "security_is_non_destructive" {
  assert {
    condition = alltrue(flatten([
      [for item in values(var.security_zones) : item.mode != "create" || item.existing_ocid == ""],
      [for item in values(var.vaults) : item.mode != "create" || item.existing_ocid == ""],
      [for item in values(var.buckets) : item.mode != "create" || item.existing_ocid == ""]
    ]))
    error_message = "Create-mode security resources must not also carry an existing OCID."
  }
}

check "existing_security_objects_have_ocids" {
  assert {
    condition = alltrue(concat(
      [for item in values(var.security_zones) : item.mode == "create" || item.existing_ocid != ""],
      [for item in values(var.vaults) : item.mode == "create" || item.existing_ocid != ""],
      [for item in values(var.buckets) : item.mode == "create" || item.existing_ocid != ""]
    ))
    error_message = "Every non-create security object requires an exact existing_ocid."
  }
}
