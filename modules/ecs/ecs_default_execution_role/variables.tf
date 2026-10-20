variable "tags" {
  type        = map(string)
  description = "A map of tags to assign to the resource. Must include CE_Application_ID, CE_Application_Name, and CE_Environment."

  validation {
    condition     = can(regex("^APM\\d{7}$", lookup(var.tags, "CE_Application_ID", "")))
    error_message = "The tags must include CE_Application_ID in the format APM_______ (7 digits)."
  }
  validation {
    condition     = length(lookup(var.tags, "CE_Application_Name", "")) > 0
    error_message = "The tags must include a non-empty CE_Application_Name."
  }
  validation {
    condition     = contains(["DEV", "TEST", "PROD"], lookup(var.tags, "CE_Environment", ""))
    error_message = "The tags must include CE_Environment with a value of DEV, TEST, or PROD."
  }
}
