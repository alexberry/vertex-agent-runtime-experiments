variable "project" {
  description = "GCP project ID. Same project as all other experiments."
  type        = string
  default     = "system-alexb-art-ed9d"
}

variable "region" {
  description = "GCP region. Same as all other experiments."
  type        = string
  default     = "europe-west2"
}

variable "cluster_name" {
  description = "Name of the GKE Autopilot cluster."
  type        = string
  default     = "agent-runtime-gke"
}

variable "registry_name" {
  description = "Name of the Artifact Registry repository for agent container images."
  type        = string
  default     = "agent-runtime-gke"
}
