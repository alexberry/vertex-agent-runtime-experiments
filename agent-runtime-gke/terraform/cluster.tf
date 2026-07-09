resource "google_compute_network" "agent_runtime" {
  name                    = var.cluster_name
  auto_create_subnetworks = false

  depends_on = [google_project_service.compute]
}

resource "google_compute_subnetwork" "agent_runtime" {
  name          = var.cluster_name
  region        = var.region
  network       = google_compute_network.agent_runtime.id
  ip_cidr_range = "10.0.0.0/20"
}

# Required for gke-l7-regional-external-managed Gateway class.
# Regional Application Load Balancers proxy traffic through Google-managed
# Envoy instances in this subnet -- it must exist before the Gateway is
# programmed. /23 is the minimum recommended size.
resource "google_compute_subnetwork" "proxy_only" {
  name          = "${var.cluster_name}-proxy"
  region        = var.region
  network       = google_compute_network.agent_runtime.id
  ip_cidr_range = "10.0.16.0/23"
  purpose       = "REGIONAL_MANAGED_PROXY"
  role          = "ACTIVE"
}

resource "google_container_cluster" "agent_runtime" {
  name       = var.cluster_name
  location   = var.region
  network    = google_compute_network.agent_runtime.name
  subnetwork = google_compute_subnetwork.agent_runtime.name

  enable_autopilot    = true
  deletion_protection = false

  depends_on = [google_project_service.container]
}

resource "google_artifact_registry_repository" "agent_images" {
  location      = var.region
  repository_id = var.registry_name
  format        = "DOCKER"

  depends_on = [google_project_service.artifact_registry]
}
