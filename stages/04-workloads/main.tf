resource "oci_integration_integration_instance" "this" {
  for_each = {
    for key, instance in var.integration_instances : key => instance
    if instance.mode != "observe-only"
  }

  compartment_id            = var.integration_compartment_ocid
  display_name              = each.value.display_name
  integration_instance_type = each.value.integration_instance_type
  is_byol                   = each.value.is_byol
  message_packs             = each.value.message_packs
  shape                     = each.value.shape
  domain_id                 = each.value.domain_id != "" ? each.value.domain_id : null

  network_endpoint_details {
    network_endpoint_type          = each.value.network_endpoint_type
    allowlisted_http_ips           = each.value.allowlisted_http_ips
    is_integration_vcn_allowlisted = each.value.is_integration_vcn_allowlisted
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_fusion_apps_fusion_environment" "this" {
  for_each = {
    for key, environment in var.fusion_environments : key => environment
    if environment.mode != "observe-only"
  }

  compartment_id               = var.fusion_compartment_ocid
  display_name                 = each.value.display_name
  fusion_environment_family_id = each.value.fusion_environment_family_id
  fusion_environment_type      = each.value.fusion_environment_type
  kms_key_id                   = each.value.kms_key_id != "" ? each.value.kms_key_id : null

  create_fusion_environment_admin_user_details {
    email_address = each.value.admin_email_address
    first_name    = each.value.admin_first_name
    last_name     = each.value.admin_last_name
    username      = each.value.admin_username
  }

  lifecycle {
    prevent_destroy = true
  }
}

check "external_workloads_are_documented" {
  assert {
    condition     = alltrue([for key, value in var.external_workload_metadata : trimspace(value) != ""])
    error_message = "Every external workload classification entry must contain a non-empty explanation."
  }
}

check "existing_workloads_have_ocids" {
  assert {
    condition = alltrue(concat(
      [for item in values(var.integration_instances) : item.mode == "create" || item.existing_ocid != ""],
      [for item in values(var.fusion_environments) : item.mode == "create" || item.existing_ocid != ""]
    ))
    error_message = "Every non-create workload resource requires an exact existing_ocid."
  }
}
