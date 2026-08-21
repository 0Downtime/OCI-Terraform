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

variable "state_bucket_mode" {
  type        = string
  description = "disabled, create, existing-managed, or observe-only. Existing adoption still requires a reviewed import using the exact OCID."
  default     = "disabled"
}

variable "state_bucket_existing_ocid" {
  type        = string
  description = "Exact existing state bucket OCID for adoption guardrails; never discovered by name."
  default     = ""
}

variable "allowlisted_moves_enabled" {
  type        = bool
  description = "Separate opt-in for compartment moves. Keep false during initial convergence."
  default     = false
}

variable "approved_move_keys" {
  type        = set(string)
  description = "Exact inventory keys approved for a separately reviewed move operation."
  default     = []
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
