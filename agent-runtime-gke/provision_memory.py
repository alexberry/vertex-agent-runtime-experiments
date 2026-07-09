#!/usr/bin/env python3
"""Creates the Vertex AI Agent Engine context resource backing Sessions + Memory Bank.

Idempotent: if agent_engine_context.txt already exists and the resource is
still live, prints its name and exits without creating a duplicate.

Run once before deploying the agent container. Writes the resource name to
agent_engine_context.txt (gitignored). Copy the resource name into
k8s/configmap.yaml before running kubectl apply.

Usage:
    GOOGLE_CLOUD_PROJECT=system-alexb-art-ed9d \
    GOOGLE_CLOUD_LOCATION=europe-west2 \
    python provision_memory.py
"""
import os
import pathlib

import requests
import vertexai

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
REGION = os.environ["GOOGLE_CLOUD_LOCATION"]

output_file = pathlib.Path(__file__).parent / "agent_engine_context.txt"

vertexai.init(project=PROJECT, location=REGION)
client = vertexai.Client()


def _resource_exists(name: str) -> bool:
    """Returns True if the reasoning engine resource is still live."""
    import subprocess
    token = subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True
    ).strip()
    resp = requests.get(
        f"https://{REGION}-aiplatform.googleapis.com/v1beta1/{name}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    return resp.status_code == 200


if output_file.exists():
    existing = output_file.read_text().strip()
    if _resource_exists(existing):
        print(f"Already exists: {existing}")
        print("Nothing to do. Delete agent_engine_context.txt to force recreation.")
        raise SystemExit(0)
    print(f"Resource {existing} no longer exists -- creating a new one.")

agent_engine = client.agent_engines.create(
    config={
        "display_name": "agent-runtime-gke-memory-context",
        "context_spec": {
            "memory_bank_config": {
                "generation_config": {
                    "model": f"projects/{PROJECT}/locations/{REGION}/publishers/google/models/gemini-2.0-flash-001",
                }
            }
        },
    }
)

resource_name = agent_engine.api_resource.name
print(f"Created: {resource_name}")

output_file.write_text(resource_name)
print(f"Written to {output_file}")
print()
print("Next: copy the resource name into k8s/configmap.yaml, then kubectl apply.")
