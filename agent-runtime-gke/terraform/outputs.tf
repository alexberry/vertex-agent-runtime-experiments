output "cluster_name" {
  description = "Name of the GKE Autopilot cluster."
  value       = google_container_cluster.agent_runtime.name
}

output "cluster_endpoint" {
  description = "Control plane endpoint for kubectl."
  value       = google_container_cluster.agent_runtime.endpoint
  sensitive   = true
}

output "registry_url" {
  description = "Artifact Registry URL for pushing agent images."
  value       = "${var.region}-docker.pkg.dev/${var.project}/${var.registry_name}"
}
