FROM python:3.11-slim

LABEL org.opencontainers.image.title="llm-provider-agent"
LABEL org.opencontainers.image.description="GPU contributor handshake agent for LLM Gateway"
LABEL org.opencontainers.image.source="https://github.com/jasincanada/llm-provider"

WORKDIR /app
COPY inference-node-agent.py /app/inference-node-agent.py

ENV GATEWAY_URL="" \
    HANDSHAKE=1 \
    OLLAMA_URL=http://ollama:11434 \
    HEARTBEAT_S=30

CMD ["python", "/app/inference-node-agent.py"]