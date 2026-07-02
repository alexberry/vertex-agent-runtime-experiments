locals {
  # Platform-managed service agent that Agent Runtime uses -- same one
  # referenced for Secret Manager access in agent-runtime-adk's deploy docs.
  reasoning_engine_service_agent = "service-${data.google_project.current.number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "reasoning_engine_model_armor_callout" {
  project = var.project
  role    = "roles/modelarmor.calloutUser"
  member  = "serviceAccount:${local.reasoning_engine_service_agent}"
}

resource "google_project_iam_member" "reasoning_engine_model_armor_user" {
  project = var.project
  role    = "roles/modelarmor.user"
  member  = "serviceAccount:${local.reasoning_engine_service_agent}"
}
