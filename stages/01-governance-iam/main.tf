data "oci_identity_domain" "this" {
  domain_id = var.identity_domain_ocid
}

resource "oci_identity_group" "this" {
  for_each = { for key, group in var.groups : key => group if group.mode != "observe-only" }

  compartment_id = var.tenancy_ocid
  name           = each.value.name
  description    = each.value.description

  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_policy" "this" {
  for_each = { for key, policy in var.policies : key => policy if policy.mode != "observe-only" }

  compartment_id = var.tenancy_ocid
  name           = each.value.name
  description    = each.value.description
  statements     = each.value.statements

  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_tag_namespace" "this" {
  for_each = { for key, namespace in var.tag_namespaces : key => namespace if namespace.mode != "observe-only" }

  compartment_id = var.tenancy_ocid
  name           = each.value.name
  description    = each.value.description
  is_retired     = false

  lifecycle {
    prevent_destroy = true
  }
}

check "identity_domain_is_present" {
  assert {
    condition     = data.oci_identity_domain.this.id == var.identity_domain_ocid
    error_message = "The configured identity domain OCID could not be read or does not match the target tenancy."
  }
}

check "existing_governance_objects_have_ocids" {
  assert {
    condition = alltrue(concat(
      [for item in values(var.groups) : item.mode == "create" || item.existing_ocid != ""],
      [for item in values(var.policies) : item.mode == "create" || item.existing_ocid != ""],
      [for item in values(var.tag_namespaces) : item.mode == "create" || item.existing_ocid != ""]
    ))
    error_message = "Every non-create governance object requires an exact existing_ocid."
  }
}
