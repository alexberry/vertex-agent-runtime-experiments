# Agent Gateway (Preview) in front of the already-deployed currency-exchange
# agent (agent-runtime-adk). Agents deployed to Agent Runtime are
# auto-registered in this project/region's Agent Registry, so no separate
# registration step is needed before referencing it here.
resource "google_network_services_agent_gateway" "currency_agent" {
  project     = var.project
  location    = var.region
  name        = var.gateway_name
  description = "Client-to-Agent gateway for the currency-exchange agent, with Model Armor prompt-injection/jailbreak screening."

  registries = [
    "//agentregistry.googleapis.com/projects/${var.project}/locations/${var.region}",
  ]

  google_managed {
    governed_access_path = "CLIENT_TO_AGENT"
  }

  depends_on = [google_project_service.network_services]
}

# Wires google_model_armor_template.currency_agent into the gateway's content
# inspection path. Confirmed via the hashicorp/google provider docs (v7.39.0)
# for google_network_services_authz_extension / google_network_security_authz_policy,
# plus Google's "Delegate authorization to Agent Gateway" guide for the
# model_armor_settings metadata format:
#
#   AuthzExtension.service = "modelarmor.{region}.rep.googleapis.com" routes
#   traffic to the regional Model Armor REP endpoint; the specific template(s)
#   to apply are passed via a `model_armor_settings` JSON blob in `metadata`
#   (request_template_id / response_template_id), not as a first-class field
#   on either resource. AuthzPolicy then binds the extension to the gateway
#   with policy_profile = CONTENT_AUTHZ (the only profile that streams the
#   request/response body to the extension for sanitization).
resource "google_network_services_authz_extension" "model_armor" {
  name     = "${var.gateway_name}-model-armor"
  project  = var.project
  location = var.region

  description = "Routes gateway traffic to Model Armor for prompt-injection/jailbreak screening."
  service     = "modelarmor.${var.region}.rep.googleapis.com"
  timeout     = "1s"
  fail_open   = false

  metadata = {
    model_armor_settings = jsonencode([
      {
        request_template_id  = "projects/${var.project}/locations/${var.region}/templates/${var.model_armor_template_id}"
        response_template_id = "projects/${var.project}/locations/${var.region}/templates/${var.model_armor_template_id}"
      }
    ])
  }

  depends_on = [
    google_project_service.network_services,
    google_model_armor_template.currency_agent,
  ]
}

resource "google_network_security_authz_policy" "content_authz" {
  name     = "${var.gateway_name}-content-authz"
  project  = var.project
  location = var.region

  description    = "Applies the Model Armor template to all traffic through the currency-exchange agent's gateway."
  policy_profile = "CONTENT_AUTHZ"
  action         = "CUSTOM"

  target {
    # load_balancing_scheme must NOT be set when targeting an Agent Gateway.
    resources = [google_network_services_agent_gateway.currency_agent.id]
  }

  custom_provider {
    authz_extension {
      resources = [google_network_services_authz_extension.model_armor.id]
    }
  }

  depends_on = [google_project_service.network_security]
}
