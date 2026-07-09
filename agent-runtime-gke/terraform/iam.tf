# Classic Workload Identity: create a GSA, bind IAM roles to it, then allow
# the default KSA to impersonate it. After terraform apply, annotate the KSA:
#   kubectl annotate serviceaccount default --namespace default \
#     iam.gke.io/gcp-service-account=$(terraform output -raw agent_gsa_email)
# Without this annotation the GKE metadata server does not exchange the KSA
# OIDC token for the GSA token and Vertex AI calls return 403.

locals {
  # Platform-managed service agent used by GKE's load balancer traffic
  # extensions (GCPTrafficExtension) to make callouts to external services
  # such as Model Armor. Created automatically when the first
  # GCPTrafficExtension is applied; the IAM binding may fail on a brand-new
  # project if the SA hasn't been created yet -- run `terraform apply` a
  # second time after deploying k8s/model-armor-extension.yaml.
  lb_traffic_extension_agent = "service-${data.google_project.current.number}@gcp-sa-dep.iam.gserviceaccount.com"
}

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

# Load balancer service agent needs Model Armor permissions so the
# GCPTrafficExtension can call out to the Model Armor API at the LB layer.
resource "google_project_iam_member" "lb_model_armor_callout_user" {
  project    = var.project
  role       = "roles/modelarmor.calloutUser"
  member     = "serviceAccount:${local.lb_traffic_extension_agent}"
  depends_on = [google_project_service.model_armor]
}

resource "google_project_iam_member" "lb_model_armor_user" {
  project    = var.project
  role       = "roles/modelarmor.user"
  member     = "serviceAccount:${local.lb_traffic_extension_agent}"
  depends_on = [google_project_service.model_armor]
}

resource "google_project_iam_member" "lb_service_usage_consumer" {
  project = var.project
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = "serviceAccount:${local.lb_traffic_extension_agent}"
}
