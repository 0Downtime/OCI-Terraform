locals {
  managed_compartments = {
    for key, value in var.foundation_compartments : key => value
    if contains(["create", "existing-managed"], value.mode) || (value.mode == "move-allowlisted" && var.allowlisted_moves_enabled)
  }
}

data "oci_identity_compartment" "existing" {
  for_each = {
    for key, value in local.managed_compartments : key => value
    if value.mode != "create"
  }
  id = each.value.existing_ocid
}

resource "oci_identity_compartment" "this" {
  for_each = local.managed_compartments

  compartment_id = each.value.parent_ocid
  description    = each.value.description
  name           = each.value.name
  enable_delete  = false

  lifecycle {
    prevent_destroy = true

    precondition {
      condition = each.value.mode == "create" || (
        (try(data.oci_identity_compartment.existing[each.key].compartment_id, "") == each.value.parent_ocid || each.value.allow_reparent) &&
        (each.value.mode != "move-allowlisted" || contains(var.approved_move_keys, each.key))
      )
      error_message = "Compartment ${each.key} has an unexpected parent. Add an explicit move allowlist entry before changing its parent."
    }
  }
}

data "oci_objectstorage_namespace" "this" {
  compartment_id = var.tenancy_ocid
}

data "oci_objectstorage_bucket" "existing_state" {
  count = var.state_bucket_mode == "existing-managed" ? 1 : 0

  namespace = data.oci_objectstorage_namespace.this.namespace
  name      = var.state_bucket_name
}

resource "oci_objectstorage_bucket" "terraform_state" {
  count = contains(["create", "existing-managed"], var.state_bucket_mode) ? 1 : 0

  compartment_id = var.state_bucket_compartment_ocid
  name           = var.state_bucket_name
  namespace      = data.oci_objectstorage_namespace.this.namespace
  access_type    = "NoPublicAccess"
  versioning     = "Enabled"
  storage_tier   = "Standard"
  kms_key_id     = var.state_bucket_kms_key_id != "" ? var.state_bucket_kms_key_id : null

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = var.state_bucket_mode != "existing-managed" || try(data.oci_objectstorage_bucket.existing_state[0].bucket_id, "") == var.state_bucket_existing_ocid
      error_message = "The existing state bucket resolved by namespace and name does not match state_bucket_existing_ocid."
    }
  }
}

check "state_bucket_inputs" {
  assert {
    condition = var.state_bucket_mode == "disabled" || (
      var.state_bucket_compartment_ocid != "" && var.tenancy_ocid != ""
    )
    error_message = "state bucket compartment and tenancy OCIDs are required when state_bucket_mode is enabled."
  }
  assert {
    condition     = contains(["disabled", "create", "existing-managed", "observe-only"], var.state_bucket_mode)
    error_message = "state_bucket_mode must be disabled, create, existing-managed, or observe-only."
  }
  assert {
    condition     = var.state_bucket_mode != "existing-managed" || var.state_bucket_existing_ocid != ""
    error_message = "state_bucket_existing_ocid is required for existing-managed state bucket adoption."
  }
}

check "existing_compartments_have_ocids" {
  assert {
    condition     = alltrue([for compartment in values(var.foundation_compartments) : compartment.mode == "create" || compartment.mode == "external-saas" || compartment.existing_ocid != ""])
    error_message = "Every non-create foundation compartment requires an exact existing_ocid."
  }
  assert {
    condition     = !contains(["create", "existing-managed"], var.state_bucket_mode) || var.state_bucket_name != ""
    error_message = "state_bucket_name is required when state_bucket_mode is create or existing-managed."
  }
}

check "management_modes_are_explicit" {
  assert {
    condition     = alltrue([for compartment in values(var.foundation_compartments) : contains(["create", "existing-managed", "observe-only", "external-saas", "move-allowlisted"], compartment.mode)])
    error_message = "Foundation compartment mode is not an allowed management mode."
  }
  assert {
    condition     = alltrue([for key, compartment in var.foundation_compartments : compartment.mode != "move-allowlisted" || (var.allowlisted_moves_enabled && contains(var.approved_move_keys, key))])
    error_message = "Move-allowlisted compartments require the separate allowlisted_moves_enabled gate and an approved key."
  }
}
