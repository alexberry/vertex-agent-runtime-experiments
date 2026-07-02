# Binds the already-deployed currency-exchange agent (agent-runtime-adk) to
# this gateway. No Terraform resource exposes this: the `agent_gateway_config`
# field on the Reasoning Engine is only reachable via the Python SDK's
# agent_engines.update()/create() -- confirmed absent from the full
# google_vertex_ai_reasoning_engine schema in both the stable and google-beta
# hashicorp/google providers (v7.39.0, checked via the Terraform MCP server).
# Runs bind_gateway.py with whatever `python3` is on PATH, so `terraform
# apply` must be run from the activated `agent-gateway-armor` pyenv
# virtualenv (see ../README.md Setup).
resource "null_resource" "bind_gateway" {
  triggers = {
    gateway_id = google_network_services_agent_gateway.currency_agent.id
  }

  provisioner "local-exec" {
    command     = "./bind_gateway.py"
    working_dir = "${path.module}/.."
  }

  # Runs before this null_resource is removed from state, which (per the
  # depends_on below) happens before Terraform destroys the gateway/authz
  # resources it depends on -- so the agent is unbound while the gateway it
  # points at still exists. Without this, `terraform destroy` deletes the
  # gateway but leaves the reasoning engine's agent_gateway_config pointing
  # at a resource that no longer exists (confirmed live: the SDK's truthy
  # check on agent_gateway_config means the field is never auto-cleared by
  # deleting the gateway it references).
  provisioner "local-exec" {
    when        = destroy
    command     = "./unbind_gateway.py"
    working_dir = "${path.module}/.."
  }

  depends_on = [
    google_network_services_agent_gateway.currency_agent,
    google_network_security_authz_policy.content_authz,
  ]
}
