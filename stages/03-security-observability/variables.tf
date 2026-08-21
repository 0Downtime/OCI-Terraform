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

variable "security_compartment_ocid" {
  type = string
}

variable "security_zones" {
  type = map(object({
    display_name            = string
    security_zone_recipe_id = string
    mode                    = string
    existing_ocid           = optional(string, "")
  }))
  default = {}
}

variable "security_zone_enabled" {
  type        = bool
  description = "Explicit opt-in. Keep false during initial brownfield convergence."
  default     = false
}

variable "cloud_guard_enabled" {
  type        = bool
  description = "Operator acknowledgement that Cloud Guard is enabled in the target tenancy."
  default     = false
}

variable "security_zone_acknowledged" {
  type        = bool
  description = "Operator acknowledgement that Security Zone inheritance and deny rules were reviewed."
  default     = false
}

variable "vaults" {
  type = map(object({
    display_name  = string
    vault_type    = string
    mode          = string
    existing_ocid = optional(string, "")
  }))
  default = {}
}

variable "buckets" {
  type = map(object({
    name          = string
    mode          = string
    existing_ocid = optional(string, "")
  }))
  default = {}
}
