output "gateway_id" {
  description = "Full resource name of the Agent Gateway."
  value       = google_network_services_agent_gateway.currency_agent.id
}

output "model_armor_template_id" {
  description = "Full resource name of the Model Armor template."
  value       = google_model_armor_template.currency_agent.id
}
