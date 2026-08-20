locals {
  existing_compartments = {
    for key, value in var.foundation_compartments : key => value
    if value.mode != "create" && value.existing_ocid != ""
  }
}

data "oci_identity_compartment" "existing" {
  for_each = local.existing_compartments
  id       = each.value.existing_ocid
}

resource "oci_identity_compartment" "this" {
  for_each = var.foundation_compartments

  compartment_id = each.value.parent_ocid
  description    = each.value.description
  name           = each.value.name
  enable_delete  = false

  lifecycle {
    prevent_destroy = true

    precondition {
      condition = each.value.mode == "create" || (
        contains(keys(local.existing_compartments), each.key) &&
        (data.oci_identity_compartment.existing[each.key].compartment_id == each.value.parent_ocid || each.value.allow_reparent)
      )
      error_message = "Compartment ${each.key} has an unexpected parent. Add an explicit move allowlist entry before changing its parent."
    }
  }
}

data "oci_objectstorage_namespace" "this" {
  compartment_id = var.tenancy_ocid
}

resource "oci_objectstorage_bucket" "terraform_state" {
  count = var.state_bucket_name == "" ? 0 : 1

  compartment_id = var.state_bucket_compartment_ocid
  name           = var.state_bucket_name
  namespace      = data.oci_objectstorage_namespace.this.namespace
  access_type    = "NoPublicAccess"
  versioning     = "Enabled"
  storage_tier   = "Standard"
  kms_key_id     = var.state_bucket_kms_key_id != "" ? var.state_bucket_kms_key_id : null

  lifecycle {
    prevent_destroy = true
  }
}

check "state_bucket_inputs" {
  assert {
    condition = var.state_bucket_name == "" || (
      var.state_bucket_compartment_ocid != "" && var.tenancy_ocid != ""
    )
    error_message = "state_bucket_compartment_ocid and tenancy_ocid are required when state_bucket_name is set."
  }
}

check "existing_compartments_have_ocids" {
  assert {
    condition     = alltrue([for compartment in values(var.foundation_compartments) : compartment.mode == "create" || compartment.existing_ocid != ""])
    error_message = "Every non-create foundation compartment requires an exact existing_ocid."
  }
}
