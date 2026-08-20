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

variable "identity_domain_ocid" {
  type = string
}

variable "groups" {
  type = map(object({
    name          = string
    description   = string
    mode          = string
    existing_ocid = optional(string, "")
  }))
  default = {}
}

variable "policies" {
  type = map(object({
    name          = string
    description   = string
    statements    = list(string)
    mode          = string
    existing_ocid = optional(string, "")
  }))
  default = {}
}

variable "tag_namespaces" {
  type = map(object({
    name          = string
    description   = string
    mode          = string
    existing_ocid = optional(string, "")
  }))
  default = {}
}
