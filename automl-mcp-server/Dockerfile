FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY pyproject.toml .

# Install the package
RUN pip install -e .

# Environment variables
ENV AUTOML_SERVICE_URL=http://automl-service:8001
ENV MCP_MODE=sse
ENV MCP_PORT=8002
ENV MCP_HOST=0.0.0.0
ENV LOG_LEVEL=INFO

EXPOSE 8002

# Run MCP server in SSE mode
CMD ["python", "-m", "src.infrastructure.mcp.server", "--transport", "sse", "--port", "8002"]
