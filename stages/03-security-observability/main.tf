resource "oci_cloud_guard_security_zone" "this" {
  for_each = { for key, zone in var.security_zones : key => zone if var.security_zone_enabled && contains(["create", "existing-managed"], zone.mode) }

  compartment_id          = var.security_compartment_ocid
  display_name            = each.value.display_name
  security_zone_recipe_id = each.value.security_zone_recipe_id

  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_kms_vault" "this" {
  for_each = { for key, vault in var.vaults : key => vault if contains(["create", "existing-managed"], vault.mode) }

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

check "security_zone_prerequisites" {
  assert {
    condition     = !anytrue([for zone in values(var.security_zones) : contains(["create", "existing-managed"], zone.mode)]) || (var.security_zone_enabled && var.cloud_guard_enabled && var.security_zone_acknowledged)
    error_message = "Security Zones are opt-in and require cloud_guard_enabled plus security_zone_acknowledged."
  }
}

check "security_resource_modes" {
  assert {
    condition = alltrue(concat(
      [for item in values(var.security_zones) : contains(["create", "existing-managed", "observe-only", "external-saas"], item.mode)],
      [for item in values(var.vaults) : contains(["create", "existing-managed", "observe-only", "external-saas"], item.mode)],
      [for item in values(var.buckets) : contains(["create", "existing-managed", "observe-only", "external-saas"], item.mode)]
    ))
    error_message = "Security resources cannot use an unrecognized or move mode."
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
