variable "region" {
  type = string
}

variable "tenancy_ocid" {
  type      = string
  sensitive = true
}

variable "user_ocid" {
  type      = string
  default   = ""
  sensitive = true
}

variable "fingerprint" {
  type      = string
  default   = ""
  sensitive = true
}

variable "private_key_path" {
  type    = string
  default = ""
}

variable "config_file_profile" {
  type    = string
  default = "DEFAULT"
}

variable "auth" {
  type    = string
  default = "ConfigFile"
}

variable "integration_compartment_ocid" {
  type = string
}

variable "fusion_compartment_ocid" {
  type = string
}

variable "integration_instances" {
  type = map(object({
    display_name                   = string
    integration_instance_type      = string
    is_byol                        = bool
    message_packs                  = number
    shape                          = string
    network_endpoint_type          = string
    allowlisted_http_ips           = optional(list(string), [])
    is_integration_vcn_allowlisted = optional(bool, false)
    mode                           = string
    existing_ocid                  = optional(string, "")
    domain_id                      = optional(string, "")
  }))
  default = {}
}

variable "fusion_environments" {
  type = map(object({
    display_name                 = string
    fusion_environment_family_id = string
    fusion_environment_type      = string
    mode                         = string
    existing_ocid                = optional(string, "")
    kms_key_id                   = optional(string, "")
    admin_email_address          = optional(string, "")
    admin_first_name             = optional(string, "")
    admin_last_name              = optional(string, "")
    admin_username               = optional(string, "")
  }))
  default = {}
}

variable "external_workload_metadata" {
  description = "Documentation-only classification for CCS and Hyperion/EPM; no provider resource is inferred."
  type        = map(string)
  default     = {}
}
