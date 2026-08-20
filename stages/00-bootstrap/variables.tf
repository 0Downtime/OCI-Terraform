variable "region" {
  type        = string
  description = "OCI target region."
}

variable "tenancy_ocid" {
  type        = string
  description = "OCI tenancy OCID, supplied outside source control."
  sensitive   = true
}

variable "user_ocid" {
  type        = string
  description = "OCI API user OCID when API-key authentication is used."
  default     = ""
  sensitive   = true
}

variable "fingerprint" {
  type        = string
  description = "OCI API-key fingerprint when API-key authentication is used."
  default     = ""
  sensitive   = true
}

variable "private_key_path" {
  type        = string
  description = "Path to an existing local OCI private key; never stored in this repository."
  default     = ""
}

variable "config_file_profile" {
  type        = string
  description = "Existing ~/.oci/config profile name."
  default     = "DEFAULT"
}

variable "auth" {
  type        = string
  description = "OCI provider authentication mode."
  default     = "ConfigFile"
}

variable "foundation_compartments" {
  description = "Foundational compartments. Existing entries require an exact OCID and a reviewed import."
  type = map(object({
    name           = string
    description    = string
    parent_ocid    = string
    mode           = string
    existing_ocid  = optional(string, "")
    allow_reparent = optional(bool, false)
  }))
  default = {}
}

variable "state_bucket_name" {
  type        = string
  description = "OCI Object Storage bucket name for later stage state."
  default     = ""
}

variable "state_bucket_compartment_ocid" {
  type        = string
  description = "Compartment for the state bucket, normally cmp-security."
  default     = ""
}

variable "state_bucket_kms_key_id" {
  type        = string
  description = "Optional existing KMS key OCID for state-bucket encryption."
  default     = ""
}
