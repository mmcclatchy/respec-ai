FROM python:3.13-slim

WORKDIR /app

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy server package definition (not CLI package)
COPY pyproject.server.toml pyproject.toml
COPY uv.lock ./
COPY src/ ./src/

# Install MCP server dependencies
RUN uv sync --frozen

# Container runs in daemon mode, waiting for docker exec commands
# Keeps container alive and maintains DB connections (for future DatabaseStateManager)
CMD ["tail", "-f", "/dev/null"]
