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

variable "network_compartment_ocid" {
  type = string
}

variable "vcns" {
  type = map(object({
    display_name  = string
    cidr_blocks   = list(string)
    dns_label     = optional(string, "")
    mode          = string
    existing_ocid = optional(string, "")
  }))
  default = {}
}

variable "subnets" {
  type = map(object({
    display_name               = string
    vcn_key                    = string
    vcn_ocid                   = optional(string, "")
    cidr_block                 = string
    prohibit_public_ip_on_vnic = bool
    mode                       = string
    existing_ocid              = optional(string, "")
  }))
  default = {}
}
