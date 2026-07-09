# Classic Workload Identity: create a GSA, bind IAM roles to it, then allow
# the default KSA to impersonate it. The pod's SA is annotated (see README)
# so the GKE metadata server exchanges the KSA OIDC token for the GSA token.

resource "google_service_account" "agent" {
  account_id   = "currency-agent"
  display_name = "Currency Agent (GKE Workload Identity)"
  depends_on   = [google_project_service.iam_credentials]
}

resource "google_project_iam_member" "agent_aiplatform_user" {
  project = var.project
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent.email}"
}

resource "google_artifact_registry_repository_iam_member" "agent_registry_reader" {
  location   = var.region
  repository = google_artifact_registry_repository.agent_images.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.agent.email}"
}

# Allow the default KSA in the default namespace to impersonate the GSA.
# The cluster's WI pool ID is always <project-id>.svc.id.goog.
resource "google_service_account_iam_member" "ksa_wi_user" {
  service_account_id = google_service_account.agent.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project}.svc.id.goog[default/default]"
  depends_on         = [google_container_cluster.agent_runtime]
}

output "agent_gsa_email" {
  value = google_service_account.agent.email
}
