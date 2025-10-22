# Dockerfile optimized for Railway deployment
# Python 3.11 slim base for smaller image size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for Git operations
# - git: Core Git functionality
# - openssh-client: SSH key-based authentication for Git
# - ca-certificates: SSL/TLS certificate validation
RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /app

# Install Python dependencies with remote extras for HTTP server
# Using pip install -e .[remote] to include FastAPI, uvicorn, etc.
RUN pip install --no-cache-dir -e ".[remote]"

# Create workspace directory for cloning repositories
# Railway volumes will mount to /data for persistence
RUN mkdir -p /data/git-workspaces && \
    chmod 755 /data/git-workspaces

# Create non-root user for security
RUN useradd -m -u 1000 mcpuser && \
    chown -R mcpuser:mcpuser /app /data/git-workspaces

# Switch to non-root user
USER mcpuser

# Set environment variables for Railway deployment
# These can be overridden by Railway environment variables
ENV TRANSPORT_MODE=http
ENV HTTP_HOST=0.0.0.0
ENV HTTP_PORT=8000
ENV WORKSPACE_DIR=/data/git-workspaces

# Expose port 8000 (Railway will map this to their dynamic PORT)
EXPOSE 8000

# Add health check for Railway monitoring
# Railway uses this to determine if the service is healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Run the MCP server
# Railway will inject the PORT environment variable
CMD ["python", "-m", "git_commit_mcp"]
