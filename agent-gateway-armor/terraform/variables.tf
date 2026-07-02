variable "project" {
  description = "GCP project ID. Same project as agent-runtime-adk."
  type        = string
  default     = "system-alexb-art-ed9d"
}

variable "region" {
  description = "GCP region. Must match agent-runtime-adk's deployment region -- Model Armor does not support cross-region calls."
  type        = string
  default     = "europe-west2"
}

variable "gateway_name" {
  description = "Name of the Agent Gateway resource."
  type        = string
  default     = "currency-agent-gateway"
}

variable "model_armor_template_id" {
  description = "ID of the Model Armor template enforced on gateway traffic."
  type        = string
  default     = "currency-agent-pi-jailbreak-template"
}
