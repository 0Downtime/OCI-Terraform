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
