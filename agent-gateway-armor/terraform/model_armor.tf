# The demoable policy for this experiment: block prompt-injection / jailbreak
# attempts on traffic to the currency-exchange agent. RAI and SDP filters are
# left commented for reference -- enable if extending the demo.
#
# malicious_uri_filter_settings is deliberately omitted: europe-west2 (this
# project's region, fixed by the agent's deployment region) doesn't support
# the "Malicious URI filter" capability -- confirmed via a live `terraform
# apply` (400 CAPABILITY_NOT_SUPPORTED). Check
# https://cloud.google.com/security/products/model-armor for current
# per-region capability support before re-adding it.
resource "google_model_armor_template" "currency_agent" {
  project     = var.project
  location    = var.region
  template_id = var.model_armor_template_id

  filter_config {
    pi_and_jailbreak_filter_settings {
      filter_enforcement = "ENABLED"
      confidence_level   = "LOW_AND_ABOVE"
    }

    # rai_settings {
    #   rai_filters {
    #     filter_type      = "HATE_SPEECH"
    #     confidence_level = "MEDIUM_AND_ABOVE"
    #   }
    # }
  }

  template_metadata {
    log_sanitize_operations = true
    log_template_operations = true
  }

  depends_on = [google_project_service.model_armor]
}
