FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir uv
COPY requirements.txt .
RUN uv venv /opt/venv && \
    uv pip install --no-cache --python /opt/venv -r requirements.txt

FROM python:3.12-slim
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY agent.py .
EXPOSE 8080
# SESSION_SERVICE_URI and MEMORY_SERVICE_URI are injected by the k8s Deployment
# as agentengine://<resource_name>. Passing explicit service URIs already
# disables local storage -- --no_use_local_storage must not be combined with them.
CMD adk api_server \
    --host 0.0.0.0 \
    --port 8080 \
    --session_service_uri "${SESSION_SERVICE_URI}" \
    --memory_service_uri "${MEMORY_SERVICE_URI}" \
    /app
