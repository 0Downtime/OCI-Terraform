data "oci_identity_domain" "this" {
  domain_id = var.identity_domain_ocid
}

resource "oci_identity_group" "this" {
  for_each = { for key, group in var.groups : key => group if group.group_type == "classic" && contains(["create", "existing-managed"], group.mode) }

  compartment_id = var.tenancy_ocid
  name           = each.value.name
  description    = each.value.description

  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_domains_group" "this" {
  for_each = { for key, group in var.groups : key => group if group.group_type == "identity-domain" && contains(["create", "existing-managed"], group.mode) }

  display_name  = each.value.name
  idcs_endpoint = data.oci_identity_domain.this.url
  schemas       = ["urn:ietf:params:scim:schemas:core:2.0:Group"]

  lifecycle {
    prevent_destroy = true

    postcondition {
      condition     = each.value.mode == "create" || self.ocid == each.value.existing_ocid
      error_message = "The imported Identity Domain group OCID does not match existing_ocid."
    }
  }
}

resource "oci_identity_policy" "this" {
  for_each = { for key, policy in var.policies : key => policy if contains(["create", "existing-managed"], policy.mode) }

  compartment_id = var.tenancy_ocid
  name           = each.value.name
  description    = each.value.description
  statements     = each.value.statements

  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_tag_namespace" "this" {
  for_each = { for key, namespace in var.tag_namespaces : key => namespace if contains(["create", "existing-managed"], namespace.mode) }

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
      [for item in values(var.groups) : item.mode == "create" || item.mode == "external-saas" || item.existing_ocid != ""],
      [for item in values(var.policies) : item.mode == "create" || item.mode == "external-saas" || item.existing_ocid != ""],
      [for item in values(var.tag_namespaces) : item.mode == "create" || item.mode == "external-saas" || item.existing_ocid != ""]
    ))
    error_message = "Every non-create governance object requires an exact existing_ocid."
  }
}

check "group_classification_is_explicit" {
  assert {
    condition     = alltrue([for item in values(var.groups) : contains(["classic", "identity-domain"], item.group_type)])
    error_message = "Every group must explicitly identify classic tenancy IAM or identity-domain classification."
  }
  assert {
    condition     = alltrue([for item in values(var.groups) : item.mode == "create" || item.mode == "external-saas" || item.existing_ocid != ""])
    error_message = "Every non-create, non-external group requires an exact existing OCID."
  }
  assert {
    condition = alltrue(concat(
      [for item in values(var.groups) : contains(["create", "existing-managed", "observe-only", "external-saas"], item.mode)],
      [for item in values(var.policies) : contains(["create", "existing-managed", "observe-only", "external-saas"], item.mode)],
      [for item in values(var.tag_namespaces) : contains(["create", "existing-managed", "observe-only", "external-saas"], item.mode)]
    ))
    error_message = "Governance resources cannot use an unrecognized or move mode."
  }
}
