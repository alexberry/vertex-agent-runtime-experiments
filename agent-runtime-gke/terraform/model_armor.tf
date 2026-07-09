# europe-west2 does not support malicious_uri_filter_settings
# (400 CAPABILITY_NOT_SUPPORTED -- confirmed in agent-gateway-armor experiment).
# PI/jailbreak filter covers prompt-injection attacks, which is the primary
# threat for an agent exposed over HTTP.
resource "google_model_armor_template" "currency_agent" {
  project     = var.project
  location    = var.region
  template_id = "currency-agent-gke"

  filter_config {
    pi_and_jailbreak_filter_settings {
      filter_enforcement = "ENABLED"
      confidence_level   = "LOW_AND_ABOVE"
    }
  }

  template_metadata {
    log_sanitize_operations = true
    log_template_operations = true
  }

  depends_on = [google_project_service.model_armor]
}

output "model_armor_template_resource" {
  value = "projects/${var.project}/locations/${var.region}/templates/${google_model_armor_template.currency_agent.template_id}"
}
